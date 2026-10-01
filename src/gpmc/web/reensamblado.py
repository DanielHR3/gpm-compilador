"""Re-corre la ramificación del flujo de una sesión con los overrides de
compuerta que la persona haya fijado a mano (compuertas.json).

Vive separado de `sesiones.py` porque toca extractores (`mermaid`,
`expediente`) además del almacén de sesión, y ese módulo se mantiene ligero
para que `web/api.py` lo importe sin arrastrar todo el pipeline.
"""

import re
from pathlib import Path

from gpmc.extractores import mermaid as ext_mmd
from gpmc.extractores.documentos import atar_a_tareas
from gpmc.extractores.expediente import _flujo_ramificado
from gpmc.nucleo.manifiesto import Flujo, Manifiesto
from gpmc.web import sesiones

_BLOQUE_MERMAID = re.compile(r"```mermaid(.*?)```", re.S)


def rm_de_tobe(carpeta: Path):
    """Re-parsea el bloque ```mermaid``` del TO-BE de `carpeta` y devuelve el
    resultado de `mermaid.extraer` (`rm`), o `None` si no hay TO-BE en la
    carpeta (expediente subido solo con Diccionario) o si el TO-BE no trae
    bloque ```mermaid```.

    Extraído de `reensamblar_flujo` para que otros consumidores (p.ej.
    `web/api.py`, `GET /compuerta/{gate_id}`) re-parseen el mismo Mermaid sin
    duplicar el criterio de localización del insumo.
    """
    ruta_to_be = carpeta / sesiones.INSUMOS["to_be"]
    if not ruta_to_be.exists():
        return None

    texto = ruta_to_be.read_text(encoding="utf-8")
    bloque = _BLOQUE_MERMAID.search(texto)
    if bloque is None:
        return None

    return ext_mmd.extraer(bloque.group(1))


def reensamblar_flujo(carpeta: Path, m: Manifiesto) -> Manifiesto:
    """Re-parsea el Mermaid del TO-BE de `carpeta`, aplica `compuertas_de(carpeta)`
    como overrides de compuerta, y corre `_flujo_ramificado` de nuevo sobre las
    pantallas que ya trae `m` (no se re-extrae el Diccionario).

    Si ramifica, reemplaza `m.flujo` y devuelve `m`. Si no hay TO-BE en la
    carpeta (expediente subido solo con Diccionario), si el TO-BE no trae
    bloque ```mermaid```, o si `_flujo_ramificado` devuelve `None` (los
    overrides no bastan para ramificar de forma segura), devuelve `m` intacto.
    """
    rm = rm_de_tobe(carpeta)
    if rm is None:
        return m

    overrides = sesiones.compuertas_de(carpeta)
    resultado = _flujo_ramificado(rm, m.pantallas, overrides=overrides)
    if resultado is not None:
        tareas, conexiones, _parejas = resultado
        nuevo = Flujo(tareas=tareas, conexiones=conexiones)
        _conservar_acciones(m, nuevo)
        m.flujo = nuevo
    return m


def _conservar_acciones(m: Manifiesto, nuevo: Flujo) -> None:
    """Pasa al flujo rearmado las acciones que colgaban de cada tarea.

    `_flujo_ramificado` arma tareas nuevas a partir del diagrama y no sabe de
    acciones: sin esto, ramificar dejaba cada documento sin evento —un PDF que
    nunca se produce— y borraba la tarea que una persona eligio con `doc04`.
    Una tarea vieja y una nueva son la misma si muestran las mismas pantallas.
    Lo que no encuentra pareja vuelve a colgarse con la regla de la extraccion.
    """
    por_pantallas = {
        tuple(paso.id for paso in t.pantallas): t for t in nuevo.tareas if t.pantallas
    }
    colgadas = set()
    for vieja in m.flujo.tareas:
        pareja = por_pantallas.get(tuple(paso.id for paso in vieja.pantallas))
        if pareja is None:
            continue
        pareja.acciones_antes = list(vieja.acciones_antes)
        pareja.acciones_despues = list(vieja.acciones_despues)
        colgadas.update(vieja.acciones_antes, vieja.acciones_despues)
    sueltas = [a for a in m.acciones if a.nombre not in colgadas]
    # Los avisos que devuelve no se usan: son los de la extraccion, ya dados.
    atar_a_tareas(sueltas, nuevo, m.pantallas)
