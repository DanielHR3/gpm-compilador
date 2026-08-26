"""Extrae el flujo BPMN del diagrama Mermaid de una Propuesta TO-BE.

Base empirica: los 24 expedientes del wiki de reingenieria. Los 29 bloques
mermaid son flowchart/graph, con 614 tareas A[...], 100 compuertas A{...},
92 inicio/fin A([...]) y 630 nodos etiquetados con :::clase.

El extractor NO adivina. Lo que no puede derivar lo devuelve como hueco para
que una persona lo resuelva.
"""

from typing import Optional
import re
from dataclasses import dataclass, field

# Los 24 expedientes usan 38 nombres de carril para unos pocos roles reales.
SINONIMOS = {
    "usuaria": "ciudadano",
    "usuario": "ciudadano",
    "ciudadano": "ciudadano",
    "ciudadana": "ciudadano",
    "solicitante": "ciudadano",
    "sistema": "sistema",
    "gpm": "sistema",
    "externo": "externo",
    "oferente": "externo",
    "nota": "_nota",
}

_CLASSDEF = re.compile(r"^\s*classDef\s+(\w+)", re.M)
_NODO = re.compile(
    r"\b(?P<id>\w+)"
    r"(?:\(\[(?P<inicio>[^\]]*)\]\)"      # A([texto])
    r"|\{(?P<compuerta>[^}]*)\}"          # A{texto}
    r"|\[(?P<tarea>[^\]]*)\])"            # A[texto]
    r"(?::::(?P<clase>\w+))?"
)
_ARISTA = re.compile(
    r"(?P<de>\w+)\s*--\s*(?:\|(?P<et1>[^|]*)\||(?P<et2>[^->|]+?))?\s*-->\s*(?P<a>\w+)"
)
_ARISTA_SIMPLE = re.compile(r"(?P<de>\w+)\s*-->\s*(?P<a>\w+)")
_CAMPO = re.compile(r"@@(\w+)")
_PREFIJO_ACTOR = re.compile(r"^\s*[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ\s/.\-]{2,40}:\s*")


def normalizar_actor(clase: str) -> str:
    """Mapea un nombre de carril a su rol canonico. Uno propio se conserva."""
    return SINONIMOS.get((clase or "").lower(), (clase or "").lower())


@dataclass
class Nodo:
    id: str
    texto: str
    clase_nodo: str          # "tarea" | "compuerta" | "inicio_fin"
    actor: Optional[str]
    campos: list[str] = field(default_factory=list)


@dataclass
class Arista:
    de: str
    a: str
    etiqueta: Optional[str] = None


@dataclass
class Resultado:
    nodos: list[Nodo] = field(default_factory=list)
    aristas: list[Arista] = field(default_factory=list)
    carriles: list[str] = field(default_factory=list)
    huecos: list[str] = field(default_factory=list)


def _limpiar(texto: str) -> str:
    t = re.sub(r"<br\s*/?>", " ", texto or "")
    t = t.replace('"', "").replace("&nbsp;", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return _PREFIJO_ACTOR.sub("", t).strip()


def extraer(bloque: str) -> Resultado:
    r = Resultado()
    r.carriles = [normalizar_actor(c) for c in _CLASSDEF.findall(bloque)]

    vistos: dict[str, Nodo] = {}
    for m in _NODO.finditer(bloque):
        if m["inicio"] is not None:
            clase_nodo, crudo = "inicio_fin", m["inicio"]
        elif m["compuerta"] is not None:
            clase_nodo, crudo = "compuerta", m["compuerta"]
        else:
            clase_nodo, crudo = "tarea", m["tarea"]

        nid = m["id"]
        if nid in vistos:
            if m["clase"] and not vistos[nid].actor:
                vistos[nid].actor = normalizar_actor(m["clase"])
            continue

        nodo = Nodo(
            id=nid,
            texto=_limpiar(crudo),
            clase_nodo=clase_nodo,
            actor=normalizar_actor(m["clase"]) if m["clase"] else None,
            campos=_CAMPO.findall(crudo or ""),
        )
        vistos[nid] = nodo
        r.nodos.append(nodo)

    # Para leer aristas, primero se reduce cada definicion de nodo a su solo id.
    # Sin esto, en `Start([texto]):::ciudadano --> C1` el origen se leeria como
    # 'ciudadano', que es la clase, no el nodo.
    plano = _NODO.sub(lambda m: m["id"], bloque)
    plano = re.sub(r":::\w+", "", plano)

    ocupadas = set()
    for m in _ARISTA.finditer(plano):
        et = (m["et1"] or m["et2"] or "").strip() or None
        r.aristas.append(Arista(de=m["de"], a=m["a"], etiqueta=et))
        ocupadas.add(m.span())
    for m in _ARISTA_SIMPLE.finditer(plano):
        if any(ini <= m.start() and m.end() <= fin for ini, fin in ocupadas):
            continue
        r.aristas.append(Arista(de=m["de"], a=m["a"]))

    # Huecos: lo que no se pudo derivar, dicho en voz alta.
    ids = set(vistos)
    for a in r.aristas:
        for extremo in (a.de, a.a):
            if extremo not in ids:
                r.huecos.append(f"la arista {a.de}->{a.a} referencia un nodo no declarado: {extremo}")

    for n in r.nodos:
        if n.actor is None and n.clase_nodo != "inicio_fin":
            r.huecos.append(
                f"el nodo '{n.id}' no declara carril (:::clase); no se puede saber que actor lo ejecuta"
            )
        if n.clase_nodo == "compuerta" and not n.campos:
            r.huecos.append(
                f"la compuerta '{n.id}' ({n.texto[:50]}) no nombra ningun campo @@; "
                "la condicion debe capturarse a mano"
            )

    r.aristas = [a for a in r.aristas if a.de in ids and a.a in ids]
    return r
