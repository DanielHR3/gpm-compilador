"""Los documentos que el tramite entrega, leidos del manifiesto.

Una accion de tipo `documento` es lo unico que el ciudadano se lleva a casa,
pero en el manifiesto vive suelta: el nombre en `acciones` y el enganche en
`acciones_antes` / `acciones_despues` de alguna tarea. Aqui se juntan las dos
mitades para que el simulador pueda ensenarlas.

Sobre la plantilla: la plataforma guarda el cuerpo del documento como texto
plano en un campo extra de la accion, y en los expedientes reales ese texto no
siempre sirve. Hay plantillas que son el volcado de un PDF escaneado —columnas
de datos sueltos, sin una sola frase— y plantillas que son una fila de rayas.
El simulador las ensena igual, pero marcadas: un documento que saldria
ilegible es un hallazgo, no un detalle de presentacion.
"""

import re
from typing import Optional

from gpmc.nucleo.manifiesto import Manifiesto

# Una "palabra" es una racha de cuatro letras o mas. Los volcados de PDF
# escaneado traen folios, placas y fechas, casi ninguna palabra; la prosa de un
# oficio trae decenas. Medido sobre los expedientes autenticos, la separacion
# es limpia: 0 y 1 palabras en los dos casos rotos, 62 a 181 en los cinco
# buenos. El umbral va en medio y lejos de los dos extremos.
_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}")
_MINIMO_PALABRAS = 8

_NOTA_ILEGIBLE = (
    "La plantilla guardada no tiene texto legible: parece el volcado de un PDF "
    "escaneado. El documento se generaria asi en la plataforma."
)
_NOTA_VACIA = (
    "La accion no trae plantilla. La plataforma generaria el documento en blanco."
)


def _estado(plantilla: str) -> tuple[str, Optional[str]]:
    if not plantilla.strip():
        return "sin_plantilla", _NOTA_VACIA
    if len(_PALABRA.findall(plantilla)) < _MINIMO_PALABRAS:
        return "ilegible", _NOTA_ILEGIBLE
    return "legible", None


def _enganche(m: Manifiesto, nombre: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """(tarea, instante, actor) de la tarea que dispara el documento.

    Se devuelve el primer enganche: un mismo documento colgado de dos tareas
    seria otro hallazgo, pero no uno que esta vista tenga que resolver.
    """
    for t in m.flujo.tareas:
        for instante, lista in (("antes", t.acciones_antes), ("despues", t.acciones_despues)):
            if nombre in lista:
                actores = {a.id: a.nombre for a in m.actores}
                return t.nombre, instante, actores.get(t.actor or "")
    return None, None, None


def documentos_de(m: Manifiesto) -> list[dict]:
    """Un dict por accion de tipo `documento`, listo para incrustar en la pagina."""
    salida = []
    for i, a in enumerate(m.acciones):
        if a.tipo != "documento":
            continue
        extra = a.model_dump()
        plantilla = (extra.get("plantilla") or "").strip("\n")
        estado, nota = _estado(plantilla)
        tarea, instante, actor = _enganche(m, a.nombre)
        salida.append({
            # Indice y no nombre: en los expedientes reales dos acciones pueden
            # llamarse igual, y este id termina en un selector del DOM.
            "id": f"doc{i}",
            "nombre": a.nombre,
            "titulo": a.titulo,
            "subtitulo": a.subtitulo,
            "firmador_nombre": a.firmador_nombre,
            "firmador_cargo": a.firmador_cargo,
            "variable": extra.get("variable"),
            "tarea": tarea,
            "instante": instante,
            "actor": actor,
            "plantilla": plantilla,
            "estado": estado,
            "nota": nota,
        })
    return salida
