"""Los entregables se anotan en estado.jsonl al extraer y al descargar el .gpm
que pasó la puerta (spec 2026-11-06-api-de-estado-para-simplifica)."""
from fastapi.testclient import TestClient

from gpmc.web import estado
from gpmc.web.app import crear_app
from tests.test_api import _ASIS_LIMPIO, _DICC_LIMPIO, _TOBE_LIMPIO

_ASIS_RUTS = _ASIS_LIMPIO.replace("---\ndependencia:", '---\nruts_id: "4321"\ndependencia:', 1)


def _subir(c, as_is=_ASIS_RUTS, to_be=_TOBE_LIMPIO, dicc=_DICC_LIMPIO):
    files = {"diccionario": ("dd.md", dicc.encode("utf-8"), "text/markdown")}
    if as_is:
        files["as_is"] = ("asis.md", as_is.encode("utf-8"), "text/markdown")
    if to_be:
        files["to_be"] = ("tobe.md", to_be.encode("utf-8"), "text/markdown")
    r = c.post("/api/v1/expedientes", files=files)
    assert r.status_code == 201, r.text
    return r.json()["sid"]


def _ent(tmp_path, ruts="4321"):
    [exp] = estado.consultar(tmp_path, ruts)
    return exp["entregables"]


def test_el_fixture_trae_ruts_id():
    assert 'ruts_id: "4321"' in _ASIS_RUTS


def test_extraer_anota_as_is_to_be_y_diccionario_de_los_archivos_subidos(tmp_path, monkeypatch):
    monkeypatch.setattr(estado, "hoy", lambda: "2026-11-10")
    _subir(TestClient(crear_app(almacen=tmp_path)))
    e = _ent(tmp_path)
    assert (e["as-is"], e["to-be"], e["diccionario"]) == ("2026-11-10",) * 3
    assert e["gpm"] is None and e["bpmn"] is None


def test_extraer_sin_to_be_no_anota_to_be(tmp_path):
    _subir(TestClient(crear_app(almacen=tmp_path)), to_be=None)
    e = _ent(tmp_path)
    assert e["as-is"] and e["diccionario"] and e["to-be"] is None


def test_extraer_sin_ruts_id_no_crea_estado_jsonl(tmp_path):
    _subir(TestClient(crear_app(almacen=tmp_path)), as_is=_ASIS_LIMPIO)
    assert not (tmp_path / estado.ARCHIVO).exists()


def test_reextraer_no_cambia_la_fecha_del_as_is(tmp_path, monkeypatch):
    c = TestClient(crear_app(almacen=tmp_path))
    monkeypatch.setattr(estado, "hoy", lambda: "2026-11-10")
    _subir(c)
    monkeypatch.setattr(estado, "hoy", lambda: "2026-11-11")
    _subir(c)
    assert _ent(tmp_path)["as-is"] == "2026-11-10"


def test_descargar_gpm_con_200_anota_gpm(tmp_path, monkeypatch):
    monkeypatch.setattr(estado, "hoy", lambda: "2026-11-12")
    c = TestClient(crear_app(almacen=tmp_path))
    sid = _subir(c)
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 200, r.text
    assert _ent(tmp_path)["gpm"] == "2026-11-12"


def test_descargar_gpm_por_la_ruta_vieja_tambien_anota(tmp_path):
    c = TestClient(crear_app(almacen=tmp_path))
    sid = _subir(c)
    assert c.get(f"/descargar/{sid}/gpm").status_code == 200
    assert _ent(tmp_path)["gpm"]


def test_descargar_gpm_bloqueado_409_no_anota_gpm(tmp_path):
    c = TestClient(crear_app(almacen=tmp_path))
    sid = _subir(c, to_be=None)  # sin TO-BE: INS-01 bloquea la puerta
    assert c.get(f"/api/v1/expedientes/{sid}/gpm").status_code == 409
    assert c.get(f"/descargar/{sid}/gpm").status_code == 409
    assert _ent(tmp_path)["gpm"] is None


def test_descargar_gpm_de_pruebas_no_anota_gpm(tmp_path):
    c = TestClient(crear_app(almacen=tmp_path))
    sid = _subir(c)
    assert c.get(f"/api/v1/expedientes/{sid}/gpm?modo=pruebas").status_code == 200
    assert c.get(f"/descargar/{sid}/gpm-pruebas").status_code == 200
    assert _ent(tmp_path)["gpm"] is None
