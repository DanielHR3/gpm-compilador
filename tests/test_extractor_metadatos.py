from gpmc.extractores import metadatos as ext
from gpmc.nucleo.huecos import Hueco


_AS_IS_MINIMO = """---
dependencia: Secretaría X
---
# Análisis AS-IS — Trámite de prueba
"""


def test_huecos_son_Hueco_y_traen_codigo_meta():
    r = ext.extraer(_AS_IS_MINIMO)
    assert r.huecos
    assert all(isinstance(h, Hueco) for h in r.huecos)
    codigos = {h.codigo for h in r.huecos}
    assert "META-01" in codigos            # falta el tiempo de respuesta
    assert all(c.startswith("META-") for c in codigos)


def test_tiempo_faltante_es_falta_dato():
    r = ext.extraer(_AS_IS_MINIMO)
    meta01 = [h for h in r.huecos if h.codigo == "META-01"][0]
    assert meta01.nivel == "falta_dato"


def test_costo_faltante_es_por_confirmar():
    r = ext.extraer(_AS_IS_MINIMO)
    meta03 = [h for h in r.huecos if h.codigo == "META-03"][0]
    assert meta03.nivel == "por_confirmar"
