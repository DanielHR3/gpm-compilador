from fastapi.testclient import TestClient
from gpmc.web.app import crear_app

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


def test_reconocer_marca_el_hueco_y_lo_devuelve(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/reconocer", json={"codigo": "INS-01", "ubicacion": ""})
    assert r.status_code == 200
    assert ["INS-01", ""] in r.json()["reconocidos"]
