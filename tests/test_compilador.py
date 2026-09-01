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


def test_el_ejemplo_ejercita_la_serializacion_de_un_select_remoto():
    """El ejemplo trae un select con catálogo remoto (estado_sol/mgee) y su cascada
    (municipio_sol). Sin un select en ejemplos/, la serialización de ese camino
    —catalogo_id, catalog_url, key_object— nunca se ejercitaba desde un manifiesto
    real."""
    g = compilar(cargar(EJEMPLO))
    campos = {c["nombre"]: c for f in g["Formularios"] for c in f["Campos"]}
    estado = campos["estado_sol"]
    assert estado["catalogo_id"] == "1"
    extra = json.loads(estado["extra"])
    assert extra["catalog_type"] == "url"
    assert extra["catalog_url"].endswith("/mgee")
    assert extra["key_object"] and " " not in extra["key_object"]
    # La cascada declara su padre en el mismo campo, no en la raíz.
    muni = json.loads(campos["municipio_sol"]["extra"])
    assert muni["populated_by"] == ["estado_sol"]


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


# Catalogo remoto: la forma sale de acceso-informacion-publica.gpm (estado_sol
# y municipio_sol). No depende de material real: el manifiesto va inline.
_CON_REMOTO = """
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: estado_sol, etiqueta: Estado, tipo: select, endpoint: mgee}
  - {nombre: municipio_sol, etiqueta: Municipio, tipo: select, endpoint: mgem,
     dependencia_tipo: campo, dependencia_campo: estado_sol}
  - {nombre: sexo, etiqueta: Sexo, tipo: select, catalogo: [{etiqueta: H, valor: h}]}
  - {nombre: raro, etiqueta: Raro, tipo: select, endpoint: consultarfc}
flujo:
  tareas:
  - {id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]}
  - {id: tf, nombre: Fin, terminal: true}
  conexiones: [{de: t1, a: tf}]
"""


def _campos_remotos():
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    g = compilar(Manifiesto(**yaml.safe_load(_CON_REMOTO)))
    return {c["nombre"]: c for c in g["Formularios"][0]["Campos"]}


def test_un_catalogo_remoto_usa_la_url_del_registro():
    e = json.loads(_campos_remotos()["estado_sol"]["extra"])
    assert e["catalog_type"] == "url"
    assert e["catalog_url"] == "https://gaia.inegi.org.mx/wscatgeo/v2/mgee"
    assert e["object_response"] == "datos"
    assert e["key_object"] == "nomgeo,cvegeo"  # sin espacio: la plataforma no lo recorta (acta 2026-08-30)
    assert "value_object" not in e          # esa clave no existe en ningun export
    # Conjunto completo, como en la prueba de cascada: una clave nueva colada
    # solo en la rama sin cascada no pasaria inadvertida. 'accion_id' del export
    # lo asigna la plataforma, no lo emitimos.
    assert set(e) == {"tamano", "catalog_type", "catalog_url",
                      "object_response", "key_object"}


def test_un_catalogo_remoto_conserva_catalogo_id():
    # La Fase 0 fijo que todo select lleva catalogo_id "1". Un catalogo remoto
    # sigue siendo un select.
    assert _campos_remotos()["estado_sol"]["catalogo_id"] == "1"


def test_una_cascada_interpola_el_padre_y_lo_declara():
    e = json.loads(_campos_remotos()["municipio_sol"]["extra"])
    assert e["catalog_url"] == (
        "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@estado_sol"
    )
    assert e["dependent_populated"] == "1"
    assert e["populated_by"] == ["estado_sol"]
    assert e["key_object"] == "nomgeo,cvegeo"  # sin espacio: la plataforma no lo recorta (acta 2026-08-30)
    assert e["object_response"] == "datos"


def test_un_endpoint_desconocido_cae_a_catalogo_manual():
    c = _campos_remotos()["raro"]
    e = json.loads(c["extra"])
    assert e["catalog_type"] == "manual"
    # Las cuatro claves van aunque tres queden vacias: sin catalog_url la
    # plataforma revienta al importar (acta 2026-08-30).
    assert e["catalog_url"] == ""
    assert e["object_response"] == ""
    assert e["key_object"] == ""
    assert c["catalogo_id"] == "1"


def test_el_catalogo_manual_sigue_igual_que_en_la_fase_0():
    c = _campos_remotos()["sexo"]
    assert json.loads(c["extra"])["catalog_type"] == "manual"
    assert c["catalogo_id"] == "1"


def test_las_claves_coinciden_con_el_export_autentico():
    # Comparado contra municipio_sol del export real, que es la cascada. Se
    # excluye 'accion_id': lo asigna la plataforma, no lo emitimos nosotros.
    e = json.loads(_campos_remotos()["municipio_sol"]["extra"])
    esperadas = {"tamano", "catalog_type", "catalog_url", "object_response",
                 "key_object", "dependent_populated", "populated_by"}
    assert set(e) == esperadas


def test_una_cascada_sin_padre_no_emite_una_url_colgando():
    # url_para(None) dejaria la URL en '.../mgem/@@'. Sin campo padre no se
    # puede resolver el catalogo, asi que se degrada a lista manual vacia y
    # el hueco API-03 del extractor explica por que.
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    m = Manifiesto(**yaml.safe_load("""
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: municipio_sol, etiqueta: Municipio, tipo: select, endpoint: mgem}
flujo:
  tareas: [{id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]},
           {id: tf, nombre: Fin, terminal: true}]
  conexiones: [{de: t1, a: tf}]
"""))
    c = compilar(m)["Formularios"][0]["Campos"][0]
    e = json.loads(c["extra"])
    assert e["catalog_type"] == "manual"
    assert e["catalog_url"] == ""   # las cuatro claves, aunque vacias (acta 2026-08-30)
    assert c["catalogo_id"] == "1"


def test_los_ids_generados_caben_en_el_rango_de_los_exports_autenticos():
    """Los 12 exports disponibles usan proceso_id de 3 a 5 digitos (842..10004)
    e ids de elemento de 4 (1000..9270). Las pruebas de distincion, override y
    determinismo pasan con CUALQUIER modulo, asi que nada fijaba el rango: un
    id de 9 digitos las satisfacia igual. La regla del proyecto es reproducir
    lo que el export contiene, no lo que parece razonable."""
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    g = compilar(Manifiesto(**yaml.safe_load(_CON_SELECT)))
    assert len(g["id"]) <= 5, f"proceso_id de {len(g['id'])} digitos: ningun export pasa de 5"
    assert 100 <= int(g["id"]) <= 99999
    for t in g["Tareas"]:
        assert len(t["id"]) <= 5, f"id de tarea {t['id']}: los exports usan 4 digitos"
    for f in g["Formularios"]:
        assert len(f["id"]) <= 5, f"id de formulario {f['id']}: los exports usan 4 digitos"


def test_el_catalogo_remoto_coincide_con_el_export_autentico(export_referencia):
    """La respuesta duradera al defecto que se repitio cuatro veces.

    Las demas pruebas assertean literales que alguien tecleo mirando el export
    — si el export cambiara, o si el literal se tecleo mal, nada lo detecta.
    Esta abre el archivo y compara. Se salta cuando GPMC_EXPORTS no apunta a
    material real, como el resto de las pruebas que lo necesitan."""
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto

    suyo = None
    for ruta in export_referencia.parent.glob("*.gpm"):
        d = json.loads(ruta.read_text(encoding="utf-8"))
        for f in d.get("Formularios", []):
            for c in (f.get("campos") or f.get("Campos") or []):
                if c["nombre"] == "municipio_sol":
                    suyo = c
    if suyo is None:
        pytest.skip("ningun export de referencia trae el campo municipio_sol")

    m = Manifiesto(**yaml.safe_load("""
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: municipio_sol, etiqueta: Municipio, tipo: select, endpoint: mgem,
     dependencia_tipo: campo, dependencia_campo: estado_sol}
flujo:
  tareas: [{id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]},
           {id: tf, nombre: Fin, terminal: true}]
  conexiones: [{de: t1, a: tf}]
"""))
    nuestro = compilar(m)["Formularios"][0]["Campos"][0]
    a, b = json.loads(nuestro["extra"]), json.loads(suyo["extra"])

    # accion_id lo asigna la plataforma; tamano es el ancho del campo.
    ajenas = {"accion_id", "tamano"}
    assert set(a) - ajenas == set(b) - ajenas, "el conjunto de claves difiere del export"
    for k in set(a) - ajenas:
        if k == "key_object":
            # Divergencia deliberada y verificada: el export trae "nomgeo, cvegeo"
            # con espacio, pero la plataforma parte por la coma sin recortarlo y
            # la cascada falla (acta 2026-08-30). Emitimos sin espacio. Se
            # compara ignorando espacios, que aun detecta una transposicion.
            assert a[k].replace(" ", "") == b[k].replace(" ", ""), \
                f"key_object difiere del export mas alla del espacio: {a[k]!r} vs {b[k]!r}"
            assert " " not in a[k], "emitimos key_object sin espacio"
        else:
            assert a[k] == b[k], f"'{k}': emitimos {a[k]!r}, el export trae {b[k]!r}"
    assert nuestro["catalogo_id"] == suyo["catalogo_id"]
    assert nuestro["dependiente_campo"] == suyo["dependiente_campo"]


# --- Correcciones tras la prueba de importacion en la plataforma (2026-08-30) ---
# Ver planeacion/actas/2026-08-30-prueba-en-plataforma.md

def test_un_select_manual_emite_las_cuatro_claves_de_catalogo():
    """La plataforma revento con 'Undefined property: stdClass::$catalog_url'
    (CampoSelect.php:468) al importar un select manual que solo traia
    catalog_type. La bitacora interna del 2026-08-10 ya lo decia: las cuatro
    claves son requeridas aunque vayan vacias. El export autentico las omite
    porque muestra lo que la plataforma PRODUCE, no lo que su importador ACEPTA."""
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    m = Manifiesto(**yaml.safe_load("""
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: sexo, etiqueta: Sexo, tipo: select, catalogo: [{etiqueta: H, valor: h}]}
flujo:
  tareas: [{id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]},
           {id: tf, nombre: Fin, terminal: true}]
  conexiones: [{de: t1, a: tf}]
"""))
    e = json.loads(compilar(m)["Formularios"][0]["Campos"][0]["extra"])
    assert e["catalog_type"] == "manual"
    for clave in ("catalog_url", "object_response", "key_object"):
        assert clave in e, f"falta '{clave}' — la plataforma revienta sin ella"
        assert e[clave] == "", f"'{clave}' debe ir vacia en un catalogo manual"


def test_key_object_no_lleva_espacio_tras_la_coma():
    """La plataforma parte key_object por la coma SIN recortar espacios: con
    'nomgeo, cvegeo' acabo buscando una clave ' cvegeo' (con espacio) que no
    existe, y la cascada devolvio 404. Observado en el municipio del proceso
    1045. Se emite sin espacio."""
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    m = Manifiesto(**yaml.safe_load("""
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: estado_sol, etiqueta: Estado, tipo: select, endpoint: mgee}
flujo:
  tareas: [{id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]},
           {id: tf, nombre: Fin, terminal: true}]
  conexiones: [{de: t1, a: tf}]
"""))
    e = json.loads(compilar(m)["Formularios"][0]["Campos"][0]["extra"])
    assert e["key_object"] == "nomgeo,cvegeo", "sin espacio tras la coma"
    assert " " not in e["key_object"]


def test_ningun_nombre_de_formulario_o_tarea_desborda_la_columna():
    """Verificado en la plataforma (2026-08-31): un nombre demasiado largo en
    'formulario.nombre' tumba el import con 'Data too long'. El compilador capa
    los nombres para que ningun nombre pueda romper una importacion."""
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    largo = "N" * 200
    m = Manifiesto(**yaml.safe_load(f"""
tramite: {{nombre: T, dependencia: D}}
actores: [{{id: u, nombre: U}}]
pantallas:
- id: p1
  nombre: "{largo}"
  actor: u
  campos: [{{nombre: c, etiqueta: C}}]
flujo:
  tareas:
  - {{id: t1, nombre: "{largo}", actor: u, inicial: true, pantallas: [{{id: p1}}]}}
  - {{id: tf, nombre: Fin, terminal: true}}
  conexiones: [{{de: t1, a: tf}}]
"""))
    g = compilar(m)
    for f in g["Formularios"]:
        assert len(f["nombre"]) <= 60, f"nombre de formulario de {len(f['nombre'])} chars"
    for t in g["Tareas"]:
        assert len(t["nombre"]) <= 60
