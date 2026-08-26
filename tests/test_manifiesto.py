import pytest
from pydantic import ValidationError

from gpmc.nucleo.manifiesto import Manifiesto, cargar, guardar

MINIMO = {
    "version": 1,
    "tramite": {"nombre": "Prueba", "dependencia": "DGT"},
    "actores": [{"id": "ciudadano", "nombre": "Ciudadano", "tipo": "autoservicio"}],
    "pantallas": [{
        "id": "p1", "nombre": "Datos", "actor": "ciudadano",
        "campos": [{"nombre": "curp", "etiqueta": "CURP", "tipo": "text", "obligatorio": True}],
    }],
    "flujo": {
        "tareas": [
            {"id": "t1", "nombre": "Capturar", "actor": "ciudadano", "inicial": True, "pantallas": ["p1"]},
            {"id": "t2", "nombre": "Fin", "terminal": True},
        ],
        "conexiones": [{"de": "t1", "a": "t2"}],
    },
    "acciones": [],
}


def test_carga_un_manifiesto_minimo():
    m = Manifiesto.model_validate(MINIMO)
    assert m.tramite.nombre == "Prueba"
    assert m.pantallas[0].campos[0].nombre == "curp"
    assert m.flujo.tareas[0].inicial is True


def test_rechaza_pantalla_de_actor_inexistente():
    malo = {**MINIMO, "pantallas": [{**MINIMO["pantallas"][0], "actor": "fantasma"}]}
    with pytest.raises(ValidationError, match="actor"):
        Manifiesto.model_validate(malo)


def test_rechaza_conexion_a_tarea_inexistente():
    malo = {**MINIMO, "flujo": {**MINIMO["flujo"], "conexiones": [{"de": "t1", "a": "t9"}]}}
    with pytest.raises(ValidationError, match="t9"):
        Manifiesto.model_validate(malo)


def test_rechaza_flujo_sin_tarea_inicial():
    tareas = [{**t, "inicial": False} for t in MINIMO["flujo"]["tareas"]]
    malo = {**MINIMO, "flujo": {**MINIMO["flujo"], "tareas": tareas}}
    with pytest.raises(ValidationError, match="inicial"):
        Manifiesto.model_validate(malo)


def test_rechaza_flujo_sin_tarea_terminal():
    tareas = [{**t, "terminal": False} for t in MINIMO["flujo"]["tareas"]]
    malo = {**MINIMO, "flujo": {**MINIMO["flujo"], "tareas": tareas}}
    with pytest.raises(ValidationError, match="terminal"):
        Manifiesto.model_validate(malo)


def test_condicion_referencia_un_campo_declarado():
    con_cond = {
        **MINIMO,
        "flujo": {
            **MINIMO["flujo"],
            "conexiones": [{"de": "t1", "a": "t2", "cuando": {"campo": "curp", "igual": "x"}}],
        },
    }
    m = Manifiesto.model_validate(con_cond)
    assert m.flujo.conexiones[0].cuando.campo == "curp"

    malo = {
        **MINIMO,
        "flujo": {
            **MINIMO["flujo"],
            "conexiones": [{"de": "t1", "a": "t2", "cuando": {"campo": "inexistente", "igual": "x"}}],
        },
    }
    with pytest.raises(ValidationError, match="inexistente"):
        Manifiesto.model_validate(malo)


def test_ida_y_vuelta_por_yaml(tmp_path):
    m = Manifiesto.model_validate(MINIMO)
    destino = tmp_path / "m.yaml"
    guardar(m, destino)
    assert cargar(destino) == m


def test_busca_campo_por_nombre():
    m = Manifiesto.model_validate(MINIMO)
    assert m.campo_por_nombre("curp").etiqueta == "CURP"
    assert m.campo_por_nombre("no_existe") is None


def test_el_ejemplo_del_repo_es_valido():
    from pathlib import Path
    ruta = Path(__file__).parent.parent / "ejemplos" / "vinculacion-organismos.yaml"
    m = cargar(ruta)
    assert m.tramite.homoclave == "SEDECO/02"
