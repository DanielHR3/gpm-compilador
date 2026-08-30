"""Extrae los metadatos del tramite y su ficha RUTS desde el AS-IS y el TO-BE.

Los datos que la ficha RUTS necesita ya estan escritos en prosa dentro del
Analisis AS-IS: homoclave, dependencia, costo, tiempo de respuesta y a quien
va dirigido. No son captura nueva.
"""

from typing import Optional
import re
from dataclasses import dataclass, field

from gpmc.nucleo.manifiesto import FichaRUTS, Tramite
from gpmc.nucleo.huecos import Hueco

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_HOMOCLAVE = re.compile(r"\*\*Homoclave:?\*\*[:\s]*`?([A-Za-z0-9/\-]+)`?", re.I)
_DEPENDENCIA = re.compile(r"^dependencia:\s*(.+?)\s*$", re.M | re.I)
_TRAMITE_LINK = re.compile(r'^tramite:\s*"?\[\[([^\]]+)\]\]"?', re.M | re.I)
_TIEMPO = re.compile(r"\*\*Tiempo de (?:respuesta|entrega):?\*\*[:\s]*([^.\n·]+)", re.I)
_COSTO = re.compile(r"\*\*Costo:?\*\*[:\s]*([^.\n·]+)", re.I)
_DIRIGIDO = re.compile(r"\*\*A qui[eé]n va dirigido:?\*\*[:\s]*([^.\n]+)", re.I)

SIN_COSTO = ("ninguno", "gratuito", "sin costo", "no aplica", "0")


@dataclass
class Resultado:
    tramite: Optional[Tramite] = None
    huecos: list[Hueco] = field(default_factory=list)


def _persona_de(texto: str) -> str:
    t = (texto or "").lower()
    fisica, moral = "física" in t or "fisica" in t, "moral" in t
    if fisica and moral:
        return "ambas"
    if moral:
        return "moral"
    if fisica:
        return "fisica"
    return "ambas"


def extraer(as_is: str, to_be: str = "", nombre_carpeta: str = "") -> Resultado:
    r = Resultado()
    texto = (as_is or "") + "\n" + (to_be or "")

    nombre = ""
    m = _TRAMITE_LINK.search(as_is or "")
    if m:
        # El wikilink de Obsidian trae la ruta completa de la boveda
        # ("1. REINGENIERIA/_recuperados/Alta de Avisos de Testamento"); el
        # nombre del tramite es solo la ultima nota.
        nombre = m.group(1).strip().split("/")[-1].strip()
    if not nombre:
        m = re.search(r"^#\s+An[aá]lisis AS-IS\s*[—\-–]\s*(.+?)\s*$", as_is or "", re.M)
        if m:
            nombre = m.group(1).strip()
    if not nombre:
        # H1 no estandar que nombra la fase y separa el titulo con un guion:
        # "# Arquitectura Actual (AS-IS) - Acceso a la Informacion".
        for fuente in (as_is or "", to_be or ""):
            m = re.search(
                r"^#\s+[^\n]*?(?:\bAS-?IS\b|\bTO-?BE\b)[^\n]*?[—\-–]\s*(.+?)\s*$",
                fuente, re.M | re.I,
            )
            if m:
                nombre = m.group(1).strip()
                break
    if not nombre and nombre_carpeta and not re.fullmatch(r"[0-9a-f]{16}", nombre_carpeta):
        # Ultimo recurso: el nombre de la carpeta del expediente (util en la
        # CLI). El asistente web pasa el id de sesion como nombre de carpeta
        # temporal; ese no es un nombre de tramite y se descarta.
        nombre = nombre_carpeta
    if not nombre:
        r.huecos.append(Hueco("falta_dato", "META-04", "metadatos",
                              "no se pudo determinar el nombre del tramite"))
        return r

    fm = _FRONTMATTER.search(as_is or "")
    dependencia = ""
    if fm:
        md = _DEPENDENCIA.search(fm.group(1))
        if md:
            dependencia = md.group(1).strip().strip('"')
    if not dependencia:
        r.huecos.append(Hueco("falta_dato", "META-02", "metadatos",
                              "no se encontro la dependencia en el frontmatter del AS-IS"))
        dependencia = "[por confirmar]"

    homoclave = ""
    mh = _HOMOCLAVE.search(texto)
    if mh:
        homoclave = mh.group(1).strip()
    else:
        r.huecos.append(Hueco("por_confirmar", "META-05", "metadatos",
                              "no se encontro homoclave; en tramites nuevos es normal, la asigna GPM"))

    tiempo = ""
    mt = _TIEMPO.search(texto)
    if mt:
        tiempo = mt.group(1).strip().rstrip(",;")
    else:
        r.huecos.append(Hueco("falta_dato", "META-01", "metadatos",
                              "no se encontro el tiempo de respuesta declarado"))

    costo = ""
    mc = _COSTO.search(texto)
    if mc:
        crudo = mc.group(1).strip().rstrip(",;")
        costo = "" if any(s in crudo.lower() for s in SIN_COSTO) else crudo
    else:
        r.huecos.append(Hueco("por_confirmar", "META-03", "metadatos",
                              "no se encontro el costo declarado; se asume sin costo"))

    dirigido = ""
    md2 = _DIRIGIDO.search(texto)
    if md2:
        dirigido = md2.group(1)
    else:
        r.huecos.append(Hueco("por_confirmar", "META-06", "metadatos",
                              "no se encontro 'A quien va dirigido'; type_of_person queda en 'ambas'"))

    r.tramite = Tramite(
        nombre=nombre,
        dependencia=dependencia,
        homoclave=homoclave,
        ruts=FichaRUTS(
            category="ciudadano",
            type_of_person=_persona_de(dirigido),
            tiempo_entrega=tiempo,
            costo=costo,
        ),
    )
    return r
