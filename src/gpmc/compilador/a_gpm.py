"""Traduce un manifiesto al objeto .gpm.

Los identificadores numericos se asignan de forma determinista a partir de un
contador base, para que compilar dos veces el mismo manifiesto produzca el
mismo archivo.
"""

from itertools import count

from gpmc.compilador.acciones import construir_acciones
from gpmc.nucleo import esquema, reglas
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


def compilar(m: Manifiesto, proceso_id: str = "900") -> dict:
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
            esquema.campo(
                id=str(next(ids)),
                nombre=c.nombre,
                tipo=c.tipo,
                etiqueta=c.etiqueta or c.nombre,
                formulario_id=fid,
                posicion=str(i),
                validacion=_validacion_de(c),
                datos=[o.model_dump() for o in c.catalogo] or None,
                extra={"tamano": ANCHOS[c.ancho]},
                readonly=c.solo_lectura,
                ayuda=c.ayuda,
            )
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
