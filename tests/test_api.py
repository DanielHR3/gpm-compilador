from fastapi.testclient import TestClient
from gpmc.web.app import crear_app
from tests.test_extractor_diccionario import _VIS
from tests.test_extractor_expediente import _DICC_RAMA, _TOBE_RAMA

_DICC = ("### Pantalla 1 — Solicitante — Datos\n\n"
         "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
         "| CURP | Texto | Input | Si | La CURP `@@curp` |\n")


def _cli(tmp_path):
    return TestClient(crear_app(almacen=tmp_path))


def test_post_expedientes_devuelve_json_con_sid_y_huecos(tmp_path):
    r = _cli(tmp_path).post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["sid"]) == 16
    assert body["manifiesto"]["tramite"]["nombre"]
    assert any(h["codigo"] == "INS-01" for h in body["huecos"])
    assert "estimacion" in body and "problemas" in body


def test_get_expediente_recupera_el_estado(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}")
    assert r.status_code == 200
    assert r.json()["sid"] == sid


def test_get_expediente_inexistente_da_404(tmp_path):
    r = _cli(tmp_path).get("/api/v1/expedientes/0123456789abcdef")
    assert r.status_code == 404
    assert "error" in r.json()


def test_post_expedientes_archivo_gigante_da_413(tmp_path):
    r = _cli(tmp_path).post("/api/v1/expedientes", files={
        "diccionario": ("enorme.md", b"x" * (11 * 1024 * 1024), "text/markdown")})
    assert r.status_code == 413
    assert "enorme.md" in r.json()["archivos"]


def test_resolver_aplica_meta01_y_devuelve_el_estado_nuevo(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={
        "resoluciones": [{"tipo": "meta01", "ubicacion": "metadatos", "valor": "5 dias habiles"}]})
    assert r.status_code == 200
    assert not any(h["codigo"] == "META-01" for h in r.json()["huecos"])
    assert "5 dias habiles" in r.json()["manifiesto"]["tramite"]["ruts"]["tiempo_entrega"]


# AS-IS que nombra el trámite (para que la extracción del manifiesto prospere)
# pero no declara tiempo de respuesta → el extractor emite META-01 'metadatos'.
_ASIS_SIN_TIEMPO = ("---\ndependencia: Secretaria X\n---\n\n"
                    "# Analisis AS-IS — Registro de Prueba\n\n"
                    "Texto sin tiempo de respuesta declarado.\n")


def test_resolver_meta01_purga_el_hueco_aunque_la_ubicacion_no_sea_metadatos(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown"),
        "as_is": ("asis.md", _ASIS_SIN_TIEMPO.encode("utf-8"), "text/markdown"),
    }).json()["sid"]
    # el expediente arranca con un hueco META-01
    assert any(h["codigo"] == "META-01"
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])
    # el cliente manda una ubicacion que NO es "metadatos"
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={
        "resoluciones": [{"tipo": "meta01", "ubicacion": "otra-cosa", "valor": "3 dias"}]})
    assert r.status_code == 200
    # aun asi el hueco se tacha, en la respuesta y en huecos.json (al releer)
    assert not any(h["codigo"] == "META-01" for h in r.json()["huecos"])
    assert not any(h["codigo"] == "META-01"
                   for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])


def test_resolver_dic08_pone_la_condicion_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    # NOTA (Task 7b / Ruling 5): el campo base de la condicion debe estar
    # declarado en el manifiesto de _VIS ("tipo_solicitante", no el
    # "tipo_documento" original — ese nombre no lo declara ningun campo de
    # _VIS y con la validacion de Task 7b pasaria a dar 422, que es
    # justamente el caso que cubre test_resolver_dic08_condicion_con_campo_base_no_declarado_da_422).
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "tipo_solicitante", "igual": "persona_moral", "operador": "==",
                      "y": [{"campo": "es_persona_moral", "igual": "si"}]},
    }]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "DIC-08" and h["ubicacion"] == ubic
                   for h in body["huecos"])
    pantalla_id, campo = ubic.split("::", 1)
    p = next(pp for pp in body["manifiesto"]["pantallas"] if pp["id"] == pantalla_id)
    cv = next(cc for cc in p["campos"] if cc["nombre"] == campo)["condicion_visible"]
    assert cv["campo"] == "tipo_solicitante"
    assert cv["y"][0]["campo"] == "es_persona_moral"


def test_resolver_dic08_campo_inexistente_da_422(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": "p1::no_existe",
        "condicion": {"campo": "x", "igual": "y"}}]})
    assert r.status_code == 422 and "error" in r.json()


def test_resolver_dic08_condicion_con_campo_base_no_declarado_da_422(tmp_path):
    # La Condicion referencia un campo que NO esta declarado en el manifiesto
    # (spec 5.1: "422 ... si una Condicion referencia un campo no declarado").
    # No debe fijarse condicion_visible ni tacharse el hueco.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "campo_fantasma", "igual": "x"},
    }]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    assert "campo_fantasma" in r.json()["error"]
    # el hueco DIC-08 sigue vivo: la resolucion invalida no se aplico
    assert any(h["codigo"] == "DIC-08" and h["ubicacion"] == ubic
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])


def test_resolver_dic08_condicion_con_clausula_y_no_declarada_da_422(tmp_path):
    # El campo base SI esta declarado, pero una clausula `y` referencia un
    # campo que no lo esta.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "es_persona_moral", "igual": "si",
                      "y": [{"campo": "campo_fantasma", "igual": "x"}]},
    }]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    assert "campo_fantasma" in r.json()["error"]


# TO-BE con la compuerta G sin @@campo (variante MMD-04 de _TOBE_RAMA, igual
# que test_no_ramifica_si_la_compuerta_no_nombra_campo en
# test_extractor_expediente.py): el Diccionario declara "procede" en la
# Pantalla 2, así que "mmd04campo" con ese campo puede reensamblar el flujo.
_TOBE_MMD04 = _TOBE_RAMA.replace("{¿@@procede == 'si'?}", "{¿Procede?}")
_INSUMOS_CON_MMD04 = {
    "diccionario": ("dd.md", _DICC_RAMA.encode("utf-8"), "text/markdown"),
    "to_be": ("tobe.md", _TOBE_MMD04.encode("utf-8"), "text/markdown"),
}


def test_resolver_mmd04campo_reensambla_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "procede"}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "MMD-04" for h in body["huecos"])
    assert any(cx.get("cuando", {}).get("campo") == "procede"
               for cx in body["manifiesto"]["flujo"]["conexiones"])


def test_resolver_mmd04campo_campo_inexistente_da_422(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "no_existe"}]})
    assert r.status_code == 422


def test_reconocer_marca_el_hueco_y_lo_devuelve(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/reconocer", json={"codigo": "INS-01", "ubicacion": ""})
    assert r.status_code == 200
    assert ["INS-01", ""] in r.json()["reconocidos"]


# ── Descarga del .gpm (puerta del linter) y del manifiesto ──

try:
    from tests.test_cli import _ASIS_LIMPIO, _TOBE_LIMPIO
except Exception:  # pragma: no cover - fallback si el import de paquete falla
    _ASIS_LIMPIO = ("---\ndependencia: Secretaría de Prueba\n---\n"
                    "# Análisis AS-IS — Trámite Limpio\n\n"
                    "**Tiempo de respuesta:** 5 días hábiles\n")
    _TOBE_LIMPIO = ("# Propuesta TO-BE — Trámite Limpio\n\n"
                    "```mermaid\nflowchart TD\n"
                    "    classDef solicitante fill:#eee\n"
                    "    Start([Inicio]):::solicitante --> T1[Solicitante: Datos]:::solicitante\n"
                    "    T1 --> Fin([Fin]):::solicitante\n```\n")

_DICC_LIMPIO = ("### Pantalla 1 — Solicitante — Datos\n\n"
                "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
                "| CURP | Texto | Input | Sí | La CURP `@@curp` |\n")


def test_gpm_bloqueado_da_409_con_lista(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 409
    assert any(b["codigo"] == "INS-01" for b in r.json()["bloqueantes"])


def test_gpm_se_descarga_cuando_no_hay_bloqueantes(tmp_path):
    # Diccionario + TO-BE lineal + AS-IS con dependencia y tiempo -> sin bloqueantes
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC_LIMPIO.encode("utf-8"), "text/markdown"),
        "as_is": ("asis.md", _ASIS_LIMPIO.encode("utf-8"), "text/markdown"),
        "to_be": ("tobe.md", _TOBE_LIMPIO.encode("utf-8"), "text/markdown"),
    }).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 200, r.text
    assert ".gpm" in r.headers["content-disposition"]
    assert len(r.content) > 0


def test_manifiesto_devuelve_el_yaml(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/manifiesto")
    assert r.status_code == 200
    assert "text/yaml" in r.headers["content-type"]
    assert "tramite:" in r.text
