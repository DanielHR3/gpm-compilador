from datetime import date, timedelta

import pytest

from tests.conftest import WIKI, legible as _legible

from gpmc.planeacion.registro import (
    ENTREGABLES, Registro, capacidad, estado, sembrar_desde_wiki,
)


@pytest.fixture
def reg(tmp_path):
    return Registro(tmp_path / "tiempos.yaml")


def test_iniciar_registra_el_nombre_y_la_fecha(reg):
    reg.iniciar("Certificado de Prueba", analista="anita")
    e = reg.buscar("Certificado de Prueba")
    assert e.analista == "anita"
    assert e.inicio == date.today()
    assert e.cierre is None


def test_iniciar_dos_veces_no_reinicia_el_reloj(reg):
    reg.iniciar("X", analista="a", cuando=date(2026, 8, 1))
    reg.iniciar("X", analista="a", cuando=date(2026, 8, 10))
    assert reg.buscar("X").inicio == date(2026, 8, 1)


def test_encuentra_el_tramite_aunque_varie_el_nombre(reg):
    reg.iniciar("Certificado de No Infracción Vehicular", analista="a")
    assert reg.buscar("certificado de no infraccion vehicular") is not None
    assert reg.buscar("  CERTIFICADO DE NO INFRACCIÓN VEHICULAR  ") is not None


def test_registrar_un_hito_guarda_su_fecha(reg):
    reg.iniciar("X", analista="a", cuando=date(2026, 8, 1))
    reg.hito("X", "to-be", cuando=date(2026, 8, 5))
    assert reg.buscar("X").hitos["to-be"] == date(2026, 8, 5)


def test_rechaza_un_entregable_desconocido(reg):
    reg.iniciar("X", analista="a")
    with pytest.raises(ValueError, match="entregable"):
        reg.hito("X", "inventado")


def test_cerrar_calcula_los_dias_transcurridos(reg):
    reg.iniciar("X", analista="a", cuando=date(2026, 8, 1))
    reg.cerrar("X", cuando=date(2026, 8, 13))
    e = reg.buscar("X")
    assert e.cierre == date(2026, 8, 13)
    assert e.dias == 12


def test_un_expediente_abierto_reporta_dias_hasta_hoy(reg):
    reg.iniciar("X", analista="a", cuando=date.today() - timedelta(days=4))
    assert reg.buscar("X").dias == 4


def test_persiste_entre_instancias(tmp_path):
    ruta = tmp_path / "t.yaml"
    Registro(ruta).iniciar("X", analista="anita", cuando=date(2026, 8, 1))
    assert Registro(ruta).buscar("X").analista == "anita"


def test_el_estado_separa_abiertos_de_cerrados(reg):
    reg.iniciar("A", analista="a", cuando=date(2026, 8, 1))
    reg.iniciar("B", analista="a", cuando=date(2026, 8, 2))
    reg.cerrar("B", cuando=date(2026, 8, 9))
    s = estado(reg)
    assert [x.nombre for x in s.abiertos] == ["A"]
    assert [x.nombre for x in s.cerrados] == ["B"]


def test_la_capacidad_cuenta_el_trabajo_en_paralelo(reg):
    for n in "ABC":
        reg.iniciar(n, analista="elesvan", cuando=date(2026, 8, 1))
    reg.iniciar("D", analista="anita", cuando=date(2026, 8, 1))
    c = capacidad(reg)
    assert c["elesvan"].abiertos == 3
    assert c["anita"].abiertos == 1


def test_la_capacidad_reporta_la_mediana_de_los_cerrados(reg):
    for n, d in (("A", 11), ("B", 15)):
        reg.iniciar(n, analista="a", cuando=date(2026, 8, 1))
        for e in ["as-is", "to-be", "bpmn", "diccionario", "wireframes"]:
            reg.hito(n, e, cuando=date(2026, 8, 1))
        reg.cerrar(n, cuando=date(2026, 8, d))
    assert capacidad(reg)["a"].mediana_dias == 12


def test_la_capacidad_no_inventa_mediana_sin_cerrados(reg):
    reg.iniciar("A", analista="a")
    assert capacidad(reg)["a"].mediana_dias is None


def test_sembrar_desde_el_wiki_marca_el_origen(tmp_path, wiki):
    r = Registro(tmp_path / "t.yaml")
    n = sembrar_desde_wiki(r, wiki)
    assert n >= 20, f"solo se sembraron {n}"
    alguno = r.todos()[0]
    assert alguno.origen == "wiki", "lo sembrado debe distinguirse de lo medido en vivo"


def test_los_entregables_son_los_seis_del_expediente():
    assert set(ENTREGABLES) == {
        "as-is", "to-be", "bpmn", "diccionario", "wireframes", "control-acciones",
    }


def test_sembrar_cuenta_los_entregables_reales(tmp_path, wiki):
    r = Registro(tmp_path / "t.yaml")
    sembrar_desde_wiki(r, wiki)
    completos = [e for e in r.todos() if e.completo]
    parciales = [e for e in r.todos() if not e.completo]
    assert completos and parciales, "la muestra real mezcla completos y parciales"
    assert all(len(e.hitos) >= 5 for e in completos)


def test_la_capacidad_usa_la_misma_regla_de_completitud_que_la_proyeccion(reg):
    reg.iniciar("Completo", analista="a", cuando=date(2026, 7, 1))
    for e in ["as-is", "to-be", "bpmn", "diccionario", "wireframes"]:
        reg.hito("Completo", e, cuando=date(2026, 7, 1))
    reg.cerrar("Completo", cuando=date(2026, 7, 13))
    reg.iniciar("Parcial", analista="a", cuando=date(2026, 7, 1))
    reg.hito("Parcial", "as-is", cuando=date(2026, 7, 1))
    reg.cerrar("Parcial", cuando=date(2026, 7, 1))
    c = capacidad(reg)["a"]
    assert c.cerrados == 2
    assert c.completos == 1
    assert c.mediana_dias == 12, "el parcial de 0 dias no debe hundir la mediana"
