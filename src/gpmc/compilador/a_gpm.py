"""Traduce un manifiesto al objeto .gpm.

Los identificadores numericos se asignan de forma determinista a partir de un
contador base, para que compilar dos veces el mismo manifiesto produzca el
mismo archivo.
"""

import hashlib
from itertools import count

from gpmc.compilador.acciones import construir_acciones
from gpmc.nucleo import esquema, reglas
from gpmc.nucleo.integraciones import resolver as _resolver_catalogo
from gpmc.nucleo.manifiesto import Campo, Manifiesto

ANCHOS = {
    "completo": "col-xs-12",
    "medio": "col-xs-12 col-md-6",
    "tercio": "col-xs-12 col-md-4",
}


def _validacion_de(c: Campo) -> str:
    partes = []
    if c.obligatorio:
        partes.append("required")
    if c.longitud_exacta is not None:
        partes.append(f"exact_length[{c.longitud_exacta}]")
    return "|".join(partes)


def _campo_gpm(c: Campo, posicion: int, formulario_id: str, campo_id: int) -> dict:
    """Un Campo del manifiesto -> un campo del Form Builder.

    Un select siempre declara de que tipo es su catalogo y siempre lleva
    catalogo_id "1": asi lo traen los dos exports autenticos, sin una sola
    excepcion. Eso esta verificado. Que sin catalog_type la plataforma reviente al
    importar con "Undefined property: stdClass::$catalog_url" (CampoSelect.php:468)
    ya no es hipotesis: se confirmo importando un .gpm el 2026-08-31 (PLAT-1, ver
    planeacion/actas/2026-08-30-prueba-en-plataforma.md). Por eso un select siempre
    emite las cuatro claves de catalogo aunque tres queden vacias.
    """
    extra = {"tamano": ANCHOS[c.ancho]}
    catalogo_id = None

    opciones = [o.model_dump() for o in c.catalogo]

    # Un select/radio sin opciones, sin endpoint y sin campo padre revienta la
    # vista de la plataforma con "Invalid argument supplied for foreach()"
    # (radio/display.php:4, models/CampoSelect.php:375). Ni datos '[]' lo evita
    # (verificado 2026-09-02, 'Estado Civil' de Testamento). Se degrada a input
    # de texto; el hueco DIC-07 del extractor dice que falta el catalogo. Un
    # endpoint (aunque no se resuelva) se respeta: lo cubre el hueco API-01.
    tipo = c.tipo
    if tipo in ("select", "radio") and not opciones \
            and not c.endpoint and not c.dependencia_campo:
        tipo = "text"

    if tipo == "select":
        # Un select siempre lleva catalogo_id "1", sea manual o remoto: asi lo
        # traen los dos exports autenticos, sin excepcion.
        catalogo_id = "1"
        cat = _resolver_catalogo(c.endpoint) if c.endpoint else None
        # Un catalogo en cascada sin campo padre no se puede resolver: su URL
        # quedaria colgando en '@@'. Se degrada a lista manual vacia — el hueco
        # API-03 del extractor dice por que quedo vacia.
        if cat is not None and cat.requiere_padre and not c.dependencia_campo:
            cat = None
        if cat is None:
            # Las cuatro claves van aunque el catalogo sea manual y tres queden
            # vacias. Verificado el 2026-08-30: la plataforma revienta al
            # importar un select que solo trae catalog_type
            # ("Undefined property: stdClass::$catalog_url", CampoSelect.php:468).
            # El export autentico las omite porque muestra lo que la plataforma
            # PRODUCE, no lo que su importador ACEPTA — la bitacora del 2026-08-10
            # tenia razon. Ver planeacion/actas/2026-08-30-prueba-en-plataforma.md.
            extra["catalog_type"] = "manual"
            extra["catalog_url"] = ""
            extra["object_response"] = ""
            extra["key_object"] = ""
        else:
            # Forma tomada de acceso-informacion-publica.gpm (estado_sol,
            # municipio_sol), con una correccion verificada en la plataforma:
            # 'key_object' es una sola cadena "etiqueta,valor" SIN espacio tras
            # la coma. El export lo trae con espacio, pero la plataforma parte
            # por la coma sin recortar y acaba buscando una clave ' cvegeo' que
            # no existe; con el espacio la cascada devolvio 404 (proceso 1045,
            # 2026-08-30). La dependencia de la cascada viaja aqui dentro, no en
            # la raiz del campo: en el export las claves dependiente_* van vacias
            # incluso en la cascada.
            extra["catalog_type"] = "url"
            extra["catalog_url"] = cat.url_para(c.dependencia_campo)
            extra["object_response"] = cat.nodo
            extra["key_object"] = f"{cat.etiqueta},{cat.valor}"
            if cat.requiere_padre and c.dependencia_campo:
                extra["dependent_populated"] = "1"
                extra["populated_by"] = [c.dependencia_campo]

    datos = opciones or None

    # La condicion de visibilidad viaja como string en dependiente_campo, con la
    # misma sintaxis que una regla de transicion: asi la traen los exports
    # autenticos (busqueda-de-testamento: @@tipo_solicitante == "notario").
    dependiente_campo = reglas.emitir(c.condicion_visible) if c.condicion_visible else ""

    return esquema.campo(
        id=str(campo_id),
        nombre=c.nombre,
        tipo=tipo,
        etiqueta=c.etiqueta or c.nombre,
        formulario_id=formulario_id,
        posicion=str(posicion),
        validacion=_validacion_de(c),
        datos=datos,
        extra=extra,
        readonly=c.solo_lectura,
        ayuda=c.ayuda,
        catalogo_id=catalogo_id,
        dependiente_campo=dependiente_campo,
    )


def compilar(m: Manifiesto, proceso_id: str = "") -> dict:
    if not proceso_id:
        num = int(hashlib.sha256(m.tramite.nombre.encode("utf-8")).hexdigest(), 16)
        # El modulo lo fija el rango de los exports autenticos, no lo que
        # parezca razonable: los 12 disponibles usan proceso_id de 842 a 10004
        # e ids de elemento de 1000 a 9270. 90 000 cubetas dan cinco digitos,
        # como el mayor observado (10002), y bastan de sobra para el catalogo
        # estatal. Derivarlo del nombre importa porque acciones.py emite
        # ->where('proceso_id', N) para el contador de folios: con un id fijo
        # todos los tramites compartirian la misma fila.
        proceso_id = str((num % 90_000) + 10_000)
        ids = count((num % 8_000) + 1_000)
    else:
        ids = count(1000)
    actores = {a.id: a for a in m.actores}

    usos_pantalla = {}
    for t in m.flujo.tareas:
        for p in t.pantallas:
            usos_pantalla[p.id] = usos_pantalla.get(p.id, 0) + 1

    acciones_gpm, documentos_gpm, mapa_ids_accion = construir_acciones(m.acciones, proceso_id, ids)

    formularios = []
    id_de_pantalla: dict[str, str] = {}
    for pantalla in m.pantallas:
        fid = str(next(ids))
        id_de_pantalla[pantalla.id] = fid
        campos = [
            _campo_gpm(c, i, fid, next(ids))
            for i, c in enumerate(pantalla.campos, start=1)
        ]
        formularios.append(
            esquema.formulario(
                id=fid, 
                nombre=pantalla.nombre, 
                proceso_id=proceso_id, 
                campos=campos,
                is_reusable=usos_pantalla.get(pantalla.id, 0) > 1,
            )
        )

    tareas = []
    id_de_tarea: dict[str, str] = {}
    for i, t in enumerate(m.flujo.tareas, start=1):
        tid = str(next(ids))
        id_de_tarea[t.id] = tid
        actor = actores.get(t.actor) if t.actor else None
        grupos = actor.grupos_usuarios if actor and actor.tipo == "grupo" else []
        pasos = [
            esquema.paso(
                id=str(next(ids)),
                orden=orden,
                formulario_id=id_de_pantalla[p.id],
                tarea_id=tid,
                modo=p.modo,
            )
            for orden, p in enumerate(t.pantallas, start=1)
        ]
        
        eventos = []
        for a_nombre in t.acciones_antes:
            eventos.append({
                "id": str(next(ids)), "regla": "", "instante": "antes", 
                "tarea_id": tid, "accion_id": mapa_ids_accion[a_nombre], 
                "paso_id": None, "metadata": None
            })
        for a_nombre in t.acciones_despues:
            eventos.append({
                "id": str(next(ids)), "regla": "", "instante": "despues", 
                "tarea_id": tid, "accion_id": mapa_ids_accion[a_nombre], 
                "paso_id": None, "metadata": None
            })

        tareas.append(
            esquema.tarea(
                id=tid,
                identificador=f"box_{i}",
                nombre=t.nombre,
                proceso_id=proceso_id,
                inicial=t.inicial,
                terminal=t.terminal,
                actor_grupos=grupos,
                pasos=pasos,
                eventos=eventos,
                posx=200 + (i - 1) * 220,
                posy=120,
            )
        )

    conexiones = [
        esquema.conexion(
            id=next(ids),
            origen=id_de_tarea[cx.de],
            destino=id_de_tarea[cx.a],
            regla=reglas.emitir(cx.cuando) if cx.cuando else None,
        )
        for cx in m.flujo.conexiones
    ]

    ficha = esquema.RUTS(
        category=m.tramite.ruts.category,
        type_of_person=m.tramite.ruts.type_of_person,
        tiempo_entrega=m.tramite.ruts.tiempo_entrega,
        costo=m.tramite.ruts.costo,
        description=m.tramite.ruts.description,
        publico=m.tramite.ruts.publico,
    )

    return esquema.proceso(
        id=proceso_id,
        nombre=m.tramite.nombre,
        homoclave=m.tramite.homoclave,
        ruts=ficha,
        tareas=tareas,
        formularios=formularios,
        acciones=acciones_gpm,
        conexiones=conexiones,
        documentos=documentos_gpm,
    )
