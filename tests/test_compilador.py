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


# Manifiesto minimo e inline: no depende de ejemplos/ ni de material real.
_CON_SELECT = """
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: curp, etiqueta: CURP, tipo: text}
  - {nombre: sexo, etiqueta: Sexo, tipo: select, catalogo: [{etiqueta: Hombre, valor: h}]}
flujo:
  tareas:
  - {id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]}
  - {id: tf, nombre: Fin, terminal: true}
  conexiones: [{de: t1, a: tf}]
"""


def _campos_de_prueba():
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    g = compilar(Manifiesto(**yaml.safe_load(_CON_SELECT)))
    return {c["nombre"]: c for c in g["Formularios"][0]["Campos"]}


def test_un_select_declara_su_tipo_de_catalogo():
    sexo = _campos_de_prueba()["sexo"]
    assert sexo["catalogo_id"] == "1"
    assert json.loads(sexo["extra"])["catalog_type"] == "manual"


def test_un_campo_que_no_es_select_no_declara_catalogo():
    curp = _campos_de_prueba()["curp"]
    assert curp["catalogo_id"] is None
    assert "catalog_type" not in json.loads(curp["extra"])


def test_el_select_conserva_el_ancho_y_sus_opciones():
    sexo = _campos_de_prueba()["sexo"]
    assert json.loads(sexo["extra"])["tamano"] == "col-xs-12 col-md-6"
    assert json.loads(sexo["datos"]) == [{"etiqueta": "Hombre", "valor": "h"}]


def _manifiesto_con_nombre(nombre: str):
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    datos = yaml.safe_load(_CON_SELECT)
    datos["tramite"] = {"nombre": nombre, "dependencia": "D"}
    return Manifiesto(**datos)


def test_dos_nombres_de_tramite_distintos_dan_proceso_id_distinto():
    ga = compilar(_manifiesto_con_nombre("Alfa"))
    gb = compilar(_manifiesto_con_nombre("Beta"))
    assert ga["id"] != gb["id"]


def test_el_proceso_id_explicito_gana_sobre_la_derivacion():
    g = compilar(_manifiesto_con_nombre("Alfa"), proceso_id="7777")
    assert g["id"] == "7777"


def test_la_derivacion_del_proceso_id_es_determinista():
    # El mismo nombre siempre da el mismo id (la ruta sin proceso_id explicito).
    assert compilar(_manifiesto_con_nombre("Gamma"))["id"] == compilar(
        _manifiesto_con_nombre("Gamma")
    )["id"]
