# tests/test_api_documentos.py
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from gpmc.agentes.proveedor import NingunProveedor, ProveedorFalso
from gpmc.web.app import crear_app

_EJEMPLO = Path(__file__).resolve().parents[1] / "ejemplos" / "expedientes" / "constancia-de-residencia"
_ASIS = ("---\ndependencia: Presidencia Municipal\n---\n\n"
         "# Análisis AS-IS — Constancia de Residencia\n\n"
         "- **Requisitos:** identificación oficial vigente, comprobante de domicilio\n")
_FRASE = "La identificación oficial se elimina"
_CON_LICENCIA = {"GPMC_IA_PROVEEDOR": "openai", "GPMC_IA_LLAVE": "k"}
_BUENA = json.dumps({"documentos": [
    dict(nombre="Identificación oficial", cita_as_is="identificación oficial vigente",
         destino="elimina", campo=None, cita_to_be=_FRASE, motivo="Se valida con la CURP.",
         confianza="alta"),
    dict(nombre="Comprobante de domicilio", cita_as_is="comprobante de domicilio",
         destino="conserva", campo="doc_comprobante", cita_to_be=None, motivo="", confianza="alta"),
]})


def _texto(prefijo):
    return next(_EJEMPLO.glob(f"{prefijo}*")).read_text(encoding="utf-8")


def _cli(tmp_path, respuestas=(), entorno=_CON_LICENCIA, proveedor=None):
    p = proveedor if proveedor is not None else ProveedorFalso(list(respuestas))
    return TestClient(crear_app(almacen=tmp_path, proveedor=p, entorno=entorno))


def _sesion(c, con_as_is=True):
    to_be = _texto("3.") + f"\n\n- **{_FRASE}**: se valida con la CURP.\n"
    archivos = {"diccionario": ("dd.md", _texto("5.").encode("utf-8"), "text/markdown"),
                "to_be": ("tb.md", to_be.encode("utf-8"), "text/markdown")}
    if con_as_is:
        archivos["as_is"] = ("as.md", _ASIS.encode("utf-8"), "text/markdown")
    r = c.post("/api/v1/expedientes", files=archivos)
    assert r.status_code == 201, r.text
    return r.json()["sid"]


def _doc(estado, nombre):
    return next(d for d in estado["documentos"] if d["nombre"] == nombre)


def test_sin_analizar_la_pagina_trae_el_inventario_del_lector(tmp_path):
    c = _cli(tmp_path)
    d = c.get(f"/api/v1/expedientes/{_sesion(c)}/documentos").json()
    assert (d["disponible"], d["estado"], d["origen"]) == (True, "sin_analizar", "lector")
    assert [(x["nombre"], x["destino"]) for x in d["documentos"]] == [
        ("identificación oficial vigente", "sin_destino"),
        ("comprobante de domicilio", "conserva")]
    assert d["resumen"]["titular"] == "Faltan 2 documentos por revisar."
    assert d["resumen"]["agregados"] == ["Comprobante corregido"]
    assert (d["puede_analizar"], d["pruebas"]) == (True, False)


def test_sin_as_is_lo_dice(tmp_path):
    c = _cli(tmp_path)
    d = c.get(f"/api/v1/expedientes/{_sesion(c, con_as_is=False)}/documentos").json()
    assert d["disponible"] is False and "AS-IS" in d["motivo"] and d["documentos"] == []


def test_sesion_inexistente_da_404_en_todo(tmp_path):
    c = _cli(tmp_path)
    base = "/api/v1/expedientes/0123456789abcdef/documentos"
    assert c.get(base).status_code == 404
    assert c.get(base + "/descarga").status_code == 404
    assert c.post(base + "/analizar").status_code == 404
    assert c.post(base + "/aceptar-verificados").status_code == 404
    assert c.post(base + "/abc/decision", json={"destino": "elimina"}).status_code == 404


def test_analizar_corre_en_segundo_plano_y_deja_las_propuestas(tmp_path):
    c = _cli(tmp_path, [_BUENA])
    sid = _sesion(c)
    r = c.post(f"/api/v1/expedientes/{sid}/documentos/analizar")
    assert r.status_code == 202 and r.json()["estado"] == "analizando"
    d = c.get(f"/api/v1/expedientes/{sid}/documentos").json()
    assert (d["estado"], d["origen"]) == ("lista", "agente")
    assert _doc(d, "Identificación oficial")["destino"] == "elimina"
    assert _doc(d, "Identificación oficial")["cita_to_be"] == _FRASE
    assert [p["mensaje"] for p in d["pasos"]][0].startswith("Leyendo")
    assert d["resumen"]["decididos"] == 0


def test_el_candado_cerrado_da_409_y_no_llama_al_modelo(tmp_path):
    p = ProveedorFalso([_BUENA])
    c = _cli(tmp_path, entorno={"GPMC_IA_PROVEEDOR": "gemini", "GPMC_IA_LLAVE": "k"}, proveedor=p)
    sid = _sesion(c)
    r = c.post(f"/api/v1/expedientes/{sid}/documentos/analizar")
    assert r.status_code == 409 and r.json()["error"]
    assert p.llamadas == 0
    d = c.get(f"/api/v1/expedientes/{sid}/documentos").json()
    assert d["puede_analizar"] is False and d["motivo_analizar"]


def test_con_modo_de_pruebas_se_abre_y_la_pagina_lo_avisa(tmp_path):
    ent = {"GPMC_IA_PROVEEDOR": "gemini", "GPMC_IA_LLAVE": "k", "GPMC_FASE3_PRUEBAS": "1"}
    c = _cli(tmp_path, [_BUENA], entorno=ent)
    sid = _sesion(c)
    assert c.get(f"/api/v1/expedientes/{sid}/documentos").json()["pruebas"] is True
    assert c.post(f"/api/v1/expedientes/{sid}/documentos/analizar").status_code == 202


def test_sin_proveedor_no_se_puede_analizar_pero_si_decidir(tmp_path):
    c = _cli(tmp_path, proveedor=NingunProveedor())
    sid = _sesion(c)
    assert c.post(f"/api/v1/expedientes/{sid}/documentos/analizar").status_code == 409
    d = c.get(f"/api/v1/expedientes/{sid}/documentos").json()
    doc = _doc(d, "identificación oficial vigente")
    r = c.post(f"/api/v1/expedientes/{sid}/documentos/{doc['id']}/decision",
               json={"destino": "elimina", "motivo": "Se valida con la CURP."})
    assert r.status_code == 200
    decidido = _doc(r.json(), "identificación oficial vigente")
    assert (decidido["destino"], decidido["estado"], decidido["motivo_de"]) == (
        "elimina", "corregido", "persona")


def test_decidir_valida_destino_y_documento(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    doc = c.get(f"/api/v1/expedientes/{sid}/documentos").json()["documentos"][0]
    url = f"/api/v1/expedientes/{sid}/documentos"
    assert c.post(f"{url}/{doc['id']}/decision", json={"destino": "borrar"}).status_code == 422
    assert c.post(f"{url}/{doc['id']}/decision", json={"destino": "sin_destino"}).status_code == 422
    assert c.post(f"{url}/{doc['id']}/decision",
                  json={"destino": "elimina", "motivo": "x" * 301}).status_code == 422
    assert c.post(f"{url}/noexiste/decision", json={"destino": "elimina"}).status_code == 404


def test_aceptar_verificados_no_acepta_lo_que_quedo_sin_destino(tmp_path):
    # `_BUENA` es JSON con los acentos escapados: la frase se cambia en el dato.
    docs = json.loads(_BUENA)["documentos"]
    docs[0]["cita_to_be"] = "Una frase que el TO-BE no trae"
    c = _cli(tmp_path, [json.dumps({"documentos": docs})])
    sid = _sesion(c)
    c.post(f"/api/v1/expedientes/{sid}/documentos/analizar")
    d = c.post(f"/api/v1/expedientes/{sid}/documentos/aceptar-verificados").json()
    assert _doc(d, "Comprobante de domicilio")["estado"] == "aceptado"
    sin = _doc(d, "Identificación oficial")
    assert (sin["destino"], sin["estado"], sin["veredicto"]) == (
        "sin_destino", "propuesto", "cita_inventada")
    assert d["resumen"]["titular"] == "De 1 documento revisado, 0 ya no se piden. Falta 1 por revisar."


def test_volver_a_analizar_no_pisa_lo_decidido(tmp_path):
    otra = _BUENA.replace('"destino": "elimina"', '"destino": "consulta"')
    c = _cli(tmp_path, [_BUENA, otra])
    sid = _sesion(c)
    url = f"/api/v1/expedientes/{sid}/documentos"
    c.post(f"{url}/analizar")
    doc = _doc(c.get(url).json(), "Identificación oficial")
    c.post(f"{url}/{doc['id']}/decision", json={"destino": "elimina"})
    c.post(f"{url}/analizar")
    despues = _doc(c.get(url).json(), "Identificación oficial")
    assert (despues["destino"], despues["estado"]) == ("elimina", "aceptado")


def test_un_analizando_viejo_se_lee_como_error(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    viejo = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    (tmp_path / sid / "documentos.json").write_text(json.dumps(
        {"estado": "analizando", "iniciado": viejo, "pasos": [], "documentos": []}),
        encoding="utf-8")
    d = c.get(f"/api/v1/expedientes/{sid}/documentos").json()
    assert d["estado"] == "error" and "interrumpió" in d["motivo_estado"]
    # Y trae el inventario del lector para seguir a mano.
    assert len(d["documentos"]) == 2


def test_un_documentos_json_roto_no_tumba_la_pagina(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    (tmp_path / sid / "documentos.json").write_text("{roto", encoding="utf-8")
    assert c.get(f"/api/v1/expedientes/{sid}/documentos").status_code == 200


def test_decidir_no_toca_el_manifiesto_ni_los_huecos(tmp_path):
    c = _cli(tmp_path)
    sid = _sesion(c)
    antes = {n: (tmp_path / sid / n).read_bytes() for n in ("manifiesto.yaml", "huecos.json")}
    doc = c.get(f"/api/v1/expedientes/{sid}/documentos").json()["documentos"][0]
    c.post(f"/api/v1/expedientes/{sid}/documentos/{doc['id']}/decision", json={"destino": "elimina"})
    assert antes == {n: (tmp_path / sid / n).read_bytes() for n in antes}


def test_la_comparativa_toma_los_requisitos_de_lo_revisado(tmp_path):
    c = _cli(tmp_path, [_BUENA])
    sid = _sesion(c)
    url = f"/api/v1/expedientes/{sid}"
    c.post(f"{url}/documentos/analizar")
    c.post(f"{url}/documentos/aceptar-verificados")
    comp = c.get(f"{url}/comparativa").json()
    req = next(m for m in comp["metricas"] if m["clave"] == "requisitos")
    assert (req["antes"]["texto"], req["antes"]["origen"]) == ("2", "revisado")
    # Queda el comprobante que se conserva y el comprobante corregido que se agrega.
    assert req["despues"]["texto"] == "2"
    assert comp["documentos"]["titular"] == "De 2 documentos que pedía el trámite, 1 ya no se pide."
    assert not [h for h in comp["huecos"] if h["codigo"] in ("CMP-04", "CMP-05")]


def test_analizar_y_decidir_quedan_en_la_auditoria(tmp_path):
    from gpmc.web.usuarios import AlmacenEnMemoria
    usuarios = AlmacenEnMemoria()
    usuarios.alta("daniel.hernandezr@hidalgo.gob.mx", "Daniel", "DGT", "Secreta-123")
    c = TestClient(crear_app(almacen=tmp_path, proveedor=ProveedorFalso([_BUENA]),
                             entorno=_CON_LICENCIA, usuarios=usuarios, jwt_secreto="s3cr3to"))
    assert c.get("/api/v1/expedientes/0123456789abcdef/documentos").status_code == 401
    c.post("/api/v1/sesion", json={"correo": "daniel.hernandezr@hidalgo.gob.mx",
                                   "contrasena": "Secreta-123"})
    sid = _sesion(c)
    url = f"/api/v1/expedientes/{sid}/documentos"
    c.post(f"{url}/analizar")
    doc = c.get(url).json()["documentos"][0]
    c.post(f"{url}/{doc['id']}/decision", json={"destino": "elimina"})
    c.post(f"{url}/aceptar-verificados")
    acciones = [f["accion"] for f in usuarios.auditoria() if f["accion"].startswith("documentos.")]
    assert sorted(acciones) == ["documentos.analizar", "documentos.decidir", "documentos.decidir"]


def test_la_descarga_es_una_pagina_escapada(tmp_path):
    hostil = _ASIS.replace("comprobante de domicilio", "<b>acta</b>")
    c = _cli(tmp_path)
    to_be = _texto("3.")
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _texto("5.").encode("utf-8"), "text/markdown"),
        "to_be": ("tb.md", to_be.encode("utf-8"), "text/markdown"),
        "as_is": ("as.md", hostil.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/documentos/descarga")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.startswith("<!doctype html>")
    assert "<b>acta</b>" not in r.text and "&lt;b&gt;acta&lt;/b&gt;" in r.text
