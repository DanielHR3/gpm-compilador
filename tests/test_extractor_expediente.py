from pathlib import Path

import pytest

from tests.conftest import WIKI, legible as _legible

from gpmc.extractores.expediente import extraer_expediente



EXPEDIENTES = [
    "anita/Alta de Avisos de Testamento",
    "elesvan/Constancia de No Infracción Vehicular Ambiental",
    "elesvan/Vinculación con Organismos Internacionales",
]


@pytest.mark.parametrize("nombre", EXPEDIENTES)
def test_produce_un_manifiesto_valido_de_un_expediente_real(nombre):
    carpeta = WIKI / nombre
    if not _legible(carpeta / "Diccionario de Datos.md"):
        pytest.skip(f"no disponible: {nombre}")
    r = extraer_expediente(carpeta)
    assert r.manifiesto is not None, f"no se produjo manifiesto. huecos: {r.huecos[:5]}"
    m = r.manifiesto
    assert m.tramite.nombre
    assert m.actores, "sin actores"
    assert m.pantallas, "sin pantallas"
    assert any(t.inicial for t in m.flujo.tareas)
    assert any(t.terminal for t in m.flujo.tareas)


@pytest.mark.parametrize("nombre", EXPEDIENTES)
def test_el_manifiesto_extraido_compila_a_gpm(nombre):
    from gpmc.compilador.a_gpm import compilar
    from gpmc.nucleo.formato import serializar

    carpeta = WIKI / nombre
    if not _legible(carpeta / "Diccionario de Datos.md"):
        pytest.skip(f"no disponible: {nombre}")
    r = extraer_expediente(carpeta)
    if r.manifiesto is None:
        pytest.skip("sin manifiesto")
    g = compilar(r.manifiesto)
    texto = serializar(g)
    assert texto.startswith('{"id":')
    assert len(g["Formularios"]) == len(r.manifiesto.pantallas)


def test_siempre_reporta_huecos_de_un_expediente_real():
    """Un extractor que no reporta ningun hueco sobre material real esta
    inventando. Los 24 expedientes promedian ~10 huecos por diagrama."""
    carpeta = WIKI / EXPEDIENTES[0]
    if not _legible(carpeta / "Diccionario de Datos.md"):
        pytest.skip("no disponible")
    r = extraer_expediente(carpeta)
    assert r.huecos, "sospechoso: cero huecos sobre material real"


def test_falla_con_gracia_si_falta_un_insumo(tmp_path):
    (tmp_path / "Propuesta TO-BE.md").write_text("# vacio", encoding="utf-8")
    r = extraer_expediente(tmp_path)
    assert r.manifiesto is None
    assert any("Diccionario" in h for h in r.huecos)


def test_explica_el_bloqueo_de_permisos_de_macos(tmp_path, monkeypatch):
    """Un PermissionError crudo no le dice nada a un analista de proceso."""
    from gpmc.extractores.expediente import SinPermiso
    import gpmc.extractores.expediente as mod

    (tmp_path / "Diccionario de Datos.md").write_text("x", encoding="utf-8")
    original = Path.read_text

    def falla(self, *a, **k):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(Path, "read_text", falla)
    with pytest.raises(SinPermiso) as exc:
        mod.extraer_expediente(tmp_path)
    mensaje = str(exc.value)
    assert "Privacidad" in mensaje
    assert "Documentos" in mensaje
    monkeypatch.setattr(Path, "read_text", original)
