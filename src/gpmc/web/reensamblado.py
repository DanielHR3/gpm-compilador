"""Re-corre la ramificación del flujo de una sesión con los overrides de
compuerta que la persona haya fijado a mano (compuertas.json).

Vive separado de `sesiones.py` porque toca extractores (`mermaid`,
`expediente`) además del almacén de sesión, y ese módulo se mantiene ligero
para que `web/api.py` lo importe sin arrastrar todo el pipeline.
"""

import re
from pathlib import Path

from gpmc.extractores import mermaid as ext_mmd
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
        m.flujo = Flujo(tareas=tareas, conexiones=conexiones)
    return m
