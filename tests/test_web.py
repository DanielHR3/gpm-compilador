from pathlib import Path

import pytest

from tests.conftest import WIKI, legible as _legible
from fastapi.testclient import TestClient

from gpmc.web.app import crear_app


EXPEDIENTE = WIKI / "anita" / "Alta de Avisos de Testamento"


@pytest.fixture
def cliente(tmp_path):
    return TestClient(crear_app(almacen=tmp_path))


def _insumos():
    if not _legible(EXPEDIENTE / "Diccionario de Datos.md"):
        pytest.skip("expediente de referencia no disponible")
    return {
        "as_is": (EXPEDIENTE / "Análisis AS-IS.md").read_bytes(),
        "to_be": (EXPEDIENTE / "Propuesta TO-BE.md").read_bytes(),
        "diccionario": (EXPEDIENTE / "Diccionario de Datos.md").read_bytes(),
    }


def test_la_portada_pide_los_tres_insumos(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    for campo in ("as_is", "to_be", "diccionario"):
        assert f'name="{campo}"' in r.text


def test_subir_los_insumos_crea_una_sesion_y_extrae(cliente):
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    }, follow_redirects=False)
    assert r.status_code in (302, 303), r.text
    assert "/revisar/" in r.headers["location"]


def test_el_paso_de_revision_muestra_huecos_y_pantallas(cliente):
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    })
    assert r.status_code == 200
    assert "hueco" in r.text.lower()
    assert "Alta de Avisos de Testamento" in r.text
    assert "Pantalla" in r.text or "pantallas" in r.text.lower()


def test_descargar_el_gpm_de_una_sesion(cliente):
    import json
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    }, follow_redirects=False)
    sid = r.headers["location"].rsplit("/", 1)[-1]

    g = cliente.get(f"/descargar/{sid}/gpm")
    assert g.status_code == 200
    assert g.headers["content-type"].startswith("application/")
    datos = json.loads(g.content)
    assert datos["nombre"] == "Alta de Avisos de Testamento"
    assert datos["Sections"] == []


def test_descargar_el_simulador_de_una_sesion(cliente):
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    }, follow_redirects=False)
    sid = r.headers["location"].rsplit("/", 1)[-1]

    s = cliente.get(f"/simulador/{sid}")
    assert s.status_code == 200
    assert "simulaci" in s.text.lower()
    assert "http://" not in s.text and "https://" not in s.text


def test_una_sesion_inexistente_devuelve_404(cliente):
    assert cliente.get("/revisar/noexiste").status_code == 404
    assert cliente.get("/descargar/noexiste/gpm").status_code == 404


def test_rechaza_una_carga_sin_diccionario(cliente):
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", b"# vacio", "text/markdown"),
        "to_be": ("tb.md", b"# vacio", "text/markdown"),
        "diccionario": ("dd.md", b"", "text/markdown"),
    })
    assert r.status_code == 200
    assert "Diccionario" in r.text


def test_el_identificador_de_sesion_no_permite_salir_del_almacen(cliente):
    for malo in ("../../etc", "..%2f..", "a/b"):
        r = cliente.get(f"/descargar/{malo}/gpm")
        assert r.status_code in (400, 404), f"{malo} devolvio {r.status_code}"
