import json
from pathlib import Path

from gpmc.compilador.a_gpm import compilar
from gpmc.nucleo.formato import serializar
from gpmc.nucleo.manifiesto import cargar

EJEMPLO = Path(__file__).parent.parent / "ejemplos" / "vinculacion-organismos.yaml"


def test_compila_el_ejemplo_a_una_estructura_valida():
    g = compilar(cargar(EJEMPLO))
    assert g["nombre"] == "Vinculación con Organismos Internacionales"
    assert g["homoclave"] == "SEDECO/02"
    assert len(g["Tareas"]) == 3
    assert len(g["Formularios"]) == 2
    assert len(g["Conexiones"]) == 3
    assert g["Sections"] == []


def test_la_ficha_ruts_viaja_en_la_raiz():
    g = compilar(cargar(EJEMPLO))
    assert g["type_of_person"] == "ambas"
    assert g["tiempo_entrega"] == "5 días hábiles"
    assert g["category"] == "ciudadano"


def test_la_tarea_inicial_y_la_terminal_quedan_marcadas():
    g = compilar(cargar(EJEMPLO))
    por_nombre = {t["nombre"]: t for t in g["Tareas"]}
    assert por_nombre["Capturar solicitud"]["inicial"] == "1"
    assert por_nombre["Trámite concluido"]["terminal"] == "1"


def test_el_actor_de_grupo_produce_grupos_usuarios():
    g = compilar(cargar(EJEMPLO))
    revision = next(t for t in g["Tareas"] if t["nombre"] == "Revisar documentación")
    assert revision["GruposUsuarios"] == [{"nombre": "COINHI"}]
    assert revision["acceso_modo"] == "grupos_usuarios"


def test_las_conexiones_condicionales_usan_el_evaluador_compartido():
    g = compilar(cargar(EJEMPLO))
    reglas_emitidas = sorted(c["regla"] for c in g["Conexiones"] if c["regla"])
    assert reglas_emitidas == ["@@documentos_correctos=='no'", "@@documentos_correctos=='si'"]
    assert all(c["tipo"] == "evaluacion" for c in g["Conexiones"] if c["regla"])


def test_el_campo_obligatorio_lleva_required():
    g = compilar(cargar(EJEMPLO))
    curp = next(c for f in g["Formularios"] for c in f["Campos"] if c["nombre"] == "curp")
    assert "required" in curp["validacion"]
    assert "exact_length[18]" in curp["validacion"]


def test_el_campo_de_sipubeh_queda_de_solo_lectura():
    g = compilar(cargar(EJEMPLO))
    nom = next(c for f in g["Formularios"] for c in f["Campos"] if c["nombre"] == "nombre_completo")
    assert nom["readonly"] == "1"


def test_el_catalogo_se_emite_como_string_json():
    g = compilar(cargar(EJEMPLO))
    tp = next(c for f in g["Formularios"] for c in f["Campos"] if c["nombre"] == "tipo_persona")
    assert isinstance(tp["datos"], str)
    assert json.loads(tp["datos"])[0]["valor"] == "persona_fisica"


def test_el_resultado_se_serializa_sin_errores():
    texto = serializar(compilar(cargar(EJEMPLO)))
    assert texto.startswith('{"id":')
    assert json.loads(texto)["nombre"] == "Vinculación con Organismos Internacionales"


def test_los_ids_son_unicos_y_las_referencias_cierran():
    g = compilar(cargar(EJEMPLO))
    ids_tarea = {t["id"] for t in g["Tareas"]}
    assert len(ids_tarea) == len(g["Tareas"])
    for c in g["Conexiones"]:
        assert str(c["tarea_id_origen"]) in ids_tarea
        assert str(c["tarea_id_destino"]) in ids_tarea
    ids_form = {f["id"] for f in g["Formularios"]}
    for t in g["Tareas"]:
        for p in t["Pasos"]:
            assert p["formulario_id"] in ids_form


def test_compilar_dos_veces_produce_lo_mismo():
    m = cargar(EJEMPLO)
    assert serializar(compilar(m)) == serializar(compilar(m))


def test_el_ejemplo_compila_con_su_accion_de_folio():
    g = compilar(cargar(EJEMPLO))
    assert len(g["Acciones"]) == 1
    extra = json.loads(g["Acciones"][0]["extra"])
    assert "lockForUpdate()" in extra["expresion"]
    assert "SEDECO-VOI" in extra["expresion"]

def test_las_acciones_se_mapean_a_eventos_en_la_tarea():
    from gpmc.nucleo.manifiesto import Manifiesto, Tramite, FichaRUTS, Actor, Tarea, Flujo, Accion
    m = Manifiesto(
        version=1,
        tramite=Tramite(nombre="Test", dependencia="DEP", ruts=FichaRUTS(category="ciudadano", type_of_person="ambas")),
        actores=[Actor(id="a", nombre="A", tipo="autoservicio")],
        flujo=Flujo(
            tareas=[
                Tarea(id="t1", nombre="T1", inicial=True, terminal=True, actor="a", acciones_antes=["folio"], acciones_despues=["costo"])
            ]
        ),
        acciones=[
            Accion(nombre="folio", tipo="folio", variable="f"),
            Accion(nombre="costo", tipo="costo", variable="c")
        ]
    )
    g = compilar(m)
    t1 = g["Tareas"][0]
    eventos = t1["Eventos"]
    assert len(eventos) == 2
    ev_antes = next(e for e in eventos if e["instante"] == "antes")
    ev_despues = next(e for e in eventos if e["instante"] == "despues")
    
    id_folio = next(a["id"] for a in g["Acciones"] if a["nombre"] == "folio")
    id_costo = next(a["id"] for a in g["Acciones"] if a["nombre"] == "costo")
    
    assert ev_antes["accion_id"] == str(id_folio)
    assert ev_despues["accion_id"] == str(id_costo)
    assert ev_antes["tarea_id"] == t1["id"]
