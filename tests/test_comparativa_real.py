# tests/test_comparativa_real.py
"""La comparativa contra los expedientes reales del equipo. Se salta sin
`GPMC_WIKI`; nunca falla por falta de material."""
import pytest

from tests.conftest import WIKI

from gpmc.comparativa.armar import a_dict, comparar
from gpmc.comparativa.documento import a_html
from gpmc.extractores import as_is as ext_as_is
from gpmc.extractores import rediseno as ext_rediseno
from gpmc.extractores.expediente import extraer_expediente


def _texto(carpeta, *pistas):
    for ruta in sorted(carpeta.glob("*.md")):
        nombre = ruta.name.upper().replace("-", " ")
        if any(p in nombre for p in pistas):
            return ruta.read_text(encoding="utf-8", errors="replace")
    return ""


def test_cada_expediente_real_arma_comparativa_sin_excepcion():
    # Sin el fixture `wiki`: comprueba la carpeta con `legible()`, que abre la
    # ruta como archivo y con un directorio siempre da falso.
    if not WIKI.is_dir():
        pytest.skip("GPMC_WIKI no configurada")
    wiki = WIKI
    carpetas = [c for c in sorted(wiki.iterdir()) if c.is_dir() and _texto(c, "AS IS")]
    if not carpetas:
        pytest.skip(f"sin expedientes con AS-IS en {wiki}")
    for carpeta in carpetas:
        r = extraer_expediente(carpeta)
        if r.manifiesto is None:
            continue
        c = comparar(ext_as_is.extraer(_texto(carpeta, "AS IS")),
                     ext_rediseno.extraer(_texto(carpeta, "TO BE")), r.manifiesto)
        assert len(c.metricas) == 7, carpeta.name
        assert c.frase, carpeta.name
        assert {h.nivel for h in c.huecos} <= {"por_confirmar"}, carpeta.name
        assert a_html(c).startswith("<!doctype html>"), carpeta.name
        assert a_dict(c)["tramite"], carpeta.name
