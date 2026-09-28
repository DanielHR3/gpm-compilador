# tests/test_api_comparativa.py
import json

from fastapi.testclient import TestClient

from gpmc.web.app import crear_app

_DICC = ("### Pantalla 1 — Solicitante — Datos\n\n"
         "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
         "| CURP | Texto | Input | Si | La CURP `@@curp` |\n")
_ASIS = ("---\ndependencia: Secretaria X\n---\n\n"
         "# Análisis AS-IS — Registro de Prueba\n\n"
         "## Estado actual\n"
         "- **Pasos / ventanillas:** 3 etapas — Recepción → Revisión → Entrega.\n"
         "- **Tiempo estimado:** 13 días hábiles\n"
         "- **Requisitos:** identificación oficial, <b>acta</b>\n")


def _cli(tmp_path):
    return TestClient(crear_app(almacen=tmp_path))


def _sesion(c, con_as_is=True):
    archivos = {"diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}
    if con_as_is:
        archivos["as_is"] = ("as.md", _ASIS.encode("utf-8"), "text/markdown")
    r = c.post("/api/v1/expedientes", files=archivos)
    assert r.status_code == 201, r.text
    return r.json()["sid"]


def _metrica(cuerpo, clave):
    return next(m for m in cuerpo["metricas"] if m["clave"] == clave)


def test_la_comparativa_de_una_sesion_con_as_is(tmp_path):
    c = _cli(tmp_path)
    r = c.get(f"/api/v1/expedientes/{_sesion(c)}/comparativa")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["disponible"] is True
    assert _metrica(d, "pasos")["antes"] == {
        "texto": "3", "numero": 3.0, "unidad": "", "origen": "contado"}
    assert d["pasos_antes"] == ["Recepción", "Revisión", "Entrega"]
    assert {h["nivel"] for h in d["huecos"]} <= {"por_confirmar"}


def test_sin_as_is_responde_200_y_dice_por_que(tmp_path):
    c = _cli(tmp_path)
    d = c.get(f"/api/v1/expedientes/{_sesion(c, con_as_is=False)}/comparativa").json()
    assert d["disponible"] is False
    assert "AS-IS" in d["motivo"] and d["metricas"] == []


def test_sesion_inexistente_da_404_en_los_tres(tmp_path):
    c = _cli(tmp_path)
    base = "/api/v1/expedientes/0123456789abcdef/comparativa"
    assert c.get(base).status_code == 404
    assert c.get(base + "/documento").status_code == 404
    assert c.post(base + "/declarar", json={
        "clave": "visitas", "antes": "2", "despues": "0"}).status_code == 404


def test_declarar_guarda_y_la_lectura_siguiente_lo_trae(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    r = c.post(f"/api/v1/expedientes/{sid}/comparativa/declarar",
               json={"clave": "visitas", "antes": "2", "despues": "0"})
    assert r.status_code == 200, r.text
    assert _metrica(r.json(), "visitas")["porcentaje"] == 100.0
    otra = c.get(f"/api/v1/expedientes/{sid}/comparativa").json()
    assert _metrica(otra, "visitas")["despues"]["origen"] == "declarado"
    guardado = json.loads((tmp_path / sid / "comparativa.json").read_text(encoding="utf-8"))
    assert guardado["declaradas"]["visitas"]["despues"] == "0"
    assert guardado["declaradas"]["visitas"]["cuando"]


def test_declarar_no_toca_el_manifiesto_ni_los_huecos(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    antes = {n: (tmp_path / sid / n).read_bytes() for n in ("manifiesto.yaml", "huecos.json")}
    c.post(f"/api/v1/expedientes/{sid}/comparativa/declarar",
           json={"clave": "visitas", "antes": "2", "despues": "0"})
    assert antes == {n: (tmp_path / sid / n).read_bytes() for n in antes}
    estado = c.get(f"/api/v1/expedientes/{sid}").json()
    assert not any(h["codigo"].startswith("CMP-") for h in estado["huecos"])


def test_declarar_rechaza_clave_desconocida_y_texto_largo(tmp_path):
    c = _cli(tmp_path)
    url = f"/api/v1/expedientes/{_sesion(c)}/comparativa/declarar"
    assert c.post(url, json={"clave": "inventada", "antes": "1", "despues": "0"}).status_code == 422
    assert c.post(url, json={"clave": "visitas", "antes": "x" * 81, "despues": "0"}).status_code == 422


def test_un_comparativa_json_roto_no_tumba_la_lectura(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    (tmp_path / sid / "comparativa.json").write_text("{roto", encoding="utf-8")
    assert c.get(f"/api/v1/expedientes/{sid}/comparativa").status_code == 200


def test_el_documento_se_descarga_y_escapa(tmp_path):
    c = _cli(tmp_path)
    r = c.get(f"/api/v1/expedientes/{_sesion(c)}/comparativa/documento")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "attachment" in r.headers["content-disposition"]
    assert ".html" in r.headers["content-disposition"]
    assert "<b>acta</b>" not in r.text
    assert r.text.startswith("<!doctype html>")


def test_con_usuarios_la_comparativa_exige_sesion_y_declarar_queda_en_la_auditoria(tmp_path):
    """El «quien» de una metrica declarada lo registra la auditoria del servidor."""
    from tests.test_api import _cli_usuarios, _entrar
    c, usuarios = _cli_usuarios(tmp_path)
    assert c.get("/api/v1/expedientes/0123456789abcdef/comparativa").status_code == 401
    _entrar(c)
    sid = _sesion(c)
    c.get(f"/api/v1/expedientes/{sid}/comparativa")              # leer no se audita
    c.post(f"/api/v1/expedientes/{sid}/comparativa/declarar",
           json={"clave": "visitas", "antes": "2", "despues": "0"})
    fila = [f for f in usuarios.auditoria() if f["accion"] == "comparativa.declarar"]
    assert len(fila) == 1 and fila[0]["sid"] == sid
    assert not [f for f in usuarios.auditoria() if f["accion"].startswith("comparativa.leer")]
