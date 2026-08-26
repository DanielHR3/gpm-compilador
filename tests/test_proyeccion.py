from datetime import date

import pytest

from gpmc.planeacion.proyeccion import proyectar
from gpmc.planeacion.registro import Registro


COMPLETO = ["as-is", "to-be", "bpmn", "diccionario", "wireframes"]


def _completar(r, nombre, cuando):
    for e in COMPLETO:
        r.hito(nombre, e, cuando=cuando)


@pytest.fixture
def reg(tmp_path):
    r = Registro(tmp_path / "t.yaml")
    for i, d in enumerate([8, 10, 14, 22, 6, 12]):
        r.iniciar(f"T{i}", analista="anita", cuando=date(2026, 7, 1))
        _completar(r, f"T{i}", date(2026, 7, 1))
        r.cerrar(f"T{i}", cuando=date(2026, 7, 1 + d))
    return r


def test_proyecta_desde_los_cerrados_reales(reg):
    p = proyectar(reg, cantidad=1, analistas=1)
    assert p.mediana_dias == 11
    assert p.muestra == 6


def test_la_proyeccion_de_varios_tramites_considera_el_paralelismo(reg):
    uno = proyectar(reg, cantidad=1, analistas=1)
    diez = proyectar(reg, cantidad=10, analistas=1)
    assert diez.dias_totales > uno.dias_totales
    con_dos = proyectar(reg, cantidad=10, analistas=2)
    assert con_dos.dias_totales < diez.dias_totales


def test_suma_el_ciclo_de_la_dgt_por_separado(reg):
    p = proyectar(reg, cantidad=1, analistas=1)
    assert p.dias_dgt == (14, 16)
    assert "DGT" in p.nota_dgt


def test_no_proyecta_sin_datos_cerrados(tmp_path):
    vacio = Registro(tmp_path / "v.yaml")
    vacio.iniciar("A", analista="a")
    p = proyectar(vacio, cantidad=3, analistas=1)
    assert p.mediana_dias is None
    assert p.dias_totales is None
    assert "sin" in p.advertencias[0].lower()


def test_advierte_que_dias_transcurridos_no_son_esfuerzo(reg):
    p = proyectar(reg, cantidad=5, analistas=1)
    assert any("esfuerzo" in a.lower() for a in p.advertencias), p.advertencias


def test_advierte_cuando_la_muestra_es_pequena(tmp_path):
    r = Registro(tmp_path / "t.yaml")
    r.iniciar("A", analista="a", cuando=date(2026, 7, 1))
    _completar(r, "A", date(2026, 7, 1))
    r.cerrar("A", cuando=date(2026, 7, 11))
    p = proyectar(r, cantidad=1, analistas=1)
    assert any("muestra" in a.lower() for a in p.advertencias), p.advertencias


def test_distingue_lo_sembrado_de_lo_medido_en_vivo(tmp_path):
    r = Registro(tmp_path / "t.yaml")
    r.iniciar("W", analista="a", cuando=date(2026, 7, 1), origen="wiki")
    _completar(r, "W", date(2026, 7, 1))
    r.cerrar("W", cuando=date(2026, 7, 13))
    p = proyectar(r, cantidad=1, analistas=1)
    assert p.muestra_viva == 0
    assert any("frontmatter" in a.lower() or "wiki" in a.lower() for a in p.advertencias)


def test_proyecta_solo_con_expedientes_completos(tmp_path):
    """Un expediente recien abierto con 1 entregable no es un ciclo de 0 dias:
    mezclarlos hunde la mediana y lleva a prometer lo imposible."""
    r = Registro(tmp_path / "t.yaml")
    for i, (d, ents) in enumerate([(12, 5), (14, 6), (10, 5), (0, 1), (0, 2), (1, 2)]):
        n = f"T{i}"
        r.iniciar(n, analista="a", cuando=date(2026, 7, 1))
        for j, e in enumerate(["as-is", "to-be", "bpmn", "diccionario",
                               "wireframes", "control-acciones"][:ents]):
            r.hito(n, e, cuando=date(2026, 7, 1))
        r.cerrar(n, cuando=date(2026, 7, 1 + d))
    p = proyectar(r, cantidad=1, analistas=1)
    assert p.mediana_dias == 12, "debe usar solo los completos (12, 14, 10)"
    assert p.muestra == 3
    assert p.parciales_excluidos == 3
    assert any("parcial" in a.lower() for a in p.advertencias), p.advertencias


def test_si_no_hay_completos_lo_dice_en_vez_de_usar_los_parciales(tmp_path):
    r = Registro(tmp_path / "t.yaml")
    r.iniciar("A", analista="a", cuando=date(2026, 7, 1))
    r.hito("A", "as-is", cuando=date(2026, 7, 1))
    r.cerrar("A", cuando=date(2026, 7, 2))
    p = proyectar(r, cantidad=3, analistas=1)
    assert p.mediana_dias is None
    assert any("completo" in a.lower() for a in p.advertencias), p.advertencias
