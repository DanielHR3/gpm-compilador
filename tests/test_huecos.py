# tests/test_huecos.py
from gpmc.nucleo.huecos import Hueco, NIVELES, ORDEN_NIVEL


def test_niveles_son_los_tres_esperados():
    assert NIVELES == ("bloqueante", "falta_dato", "por_confirmar")


def test_str_incluye_codigo_ubicacion_y_mensaje():
    h = Hueco("falta_dato", "META-01", "metadatos", "no se encontró el tiempo de respuesta")
    assert str(h) == "[META-01] metadatos: no se encontró el tiempo de respuesta"


def test_str_omite_ubicacion_vacia():
    h = Hueco("bloqueante", "INS-01", "", "no se encontró la Propuesta TO-BE")
    assert str(h) == "[INS-01] no se encontró la Propuesta TO-BE"


def test_propuesta_por_defecto_es_none():
    h = Hueco("por_confirmar", "DIC-01", "p1", "'CURP' sin nombre técnico")
    assert h.propuesta is None


def test_orden_nivel_prioriza_bloqueante():
    huecos = [
        Hueco("por_confirmar", "DIC-01", "p1", "x"),
        Hueco("bloqueante", "INS-01", "", "y"),
        Hueco("falta_dato", "META-01", "", "z"),
    ]
    huecos.sort(key=lambda h: ORDEN_NIVEL[h.nivel])
    assert [h.nivel for h in huecos] == ["bloqueante", "falta_dato", "por_confirmar"]
