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

from gpmc.nucleo.huecos import Hueco

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
# Mermaid admite la etiqueta de la arista antes de la flecha
# (`A -- texto --> B`, `A -- |texto| --> B`) o despues (`A -->|texto| B`).
# Los expedientes del equipo usan la primera; la plantilla del Diccionario
# prescribe la segunda para las compuertas. Se aceptan las dos.
#
# `et2` (forma sin pipes) usa un lookahead negativo en vez de una clase de
# caracteres excluidos: antes excluia literalmente '>' (entre otros), asi que
# una etiqueta con un '<br/>' -real en expedientes del equipo, ver
# test_una_etiqueta_de_arista_con_br_no_se_confunde_con_un_nodo- rompia el
# match completo; el codigo caia a `_ARISTA_SIMPLE` (sin manejo de etiquetas)
# y esa recortaba un fragmento de la etiqueta como si fuera un nodo real,
# generando un MMD-02 fantasma. El lookahead solo se detiene ante la flecha
# completa `-->` o un `|` suelto (para no chocar con la forma con pipes).
_ARISTA = re.compile(
    r"(?P<de>\w+)\s*"
    r"(?:"
    r"--\s*(?:\|(?P<et1>[^|]*)\||(?P<et2>(?:(?!-->|\|).)+?))?\s*-->"
    r"|"
    r"-->\s*\|(?P<et3>[^|]*)\|"
    r")"
    r"\s*(?P<a>\w+)"
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
    clase_nodo: str          # "tarea" | "compuerta" | "inicio_fin" | "nota"
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
    huecos: list[Hueco] = field(default_factory=list)


def _limpiar(texto: str) -> tuple[str, Optional[str]]:
    """Devuelve el texto de la tarea y, si lo trae, quien la ejecuta.

    El diagrama TO-BE nombra al ejecutor delante de la tarea: «🔍 Usuario:
    Consultar informacion». Antes esta funcion reconocia ese prefijo y lo
    BORRABA, y mas abajo el extractor emitia un MMD-03 preguntando justo el dato
    que acababa de tirar: en Publicacion en el Periodico Oficial, 33 de 42
    huecos eran eso. Ahora se devuelve para poder usarlo.
    """
    t = re.sub(r"<br\s*/?>", " ", texto or "")
    t = t.replace('"', "").replace("&nbsp;", " ")
    t = re.sub(r"\*\([^)]*\)\*?", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Los emojis de adorno van delante del prefijo y lo esconden del patron.
    t = re.sub(r"^(?:[^\w¿¡(\[]|_)+", "", t).strip()
    m = _PREFIJO_ACTOR.match(t)
    if not m:
        return t, None
    prefijo = m.group(0).rstrip().rstrip(":").strip()
    return t[m.end():].strip(), prefijo or None


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
            crudo = m["tarea"]
            # Los expedientes anotan el diagrama con la forma [/texto/] y el
            # carril 'nota'. Se aceptan ambas senales: la clase la declara
            # SINONIMOS, la forma cubre las notas que no declaran clase. La forma
            # de barras GANA sobre un carril real contradictorio ([/x/]:::ciudadano
            # sale nota): ante la duda, un nodo con forma de nota no se ejecuta como
            # tarea. Ver test_la_forma_de_barras_gana_sobre_un_carril_real.
            recortado = (crudo or "").strip()
            es_nota = (
                normalizar_actor(m["clase"] or "") == "_nota"
                or (recortado.startswith("/") and recortado.endswith("/"))
            )
            clase_nodo = "nota" if es_nota else "tarea"

        nid = m["id"]
        if nid in vistos:
            if m["clase"] and not vistos[nid].actor:
                vistos[nid].actor = normalizar_actor(m["clase"])
            continue

        # A la nota no se le quita el prefijo de actor: "Nota importante:" no
        # nombra a quien ejecuta, y _limpiar se lo comeria.
        if clase_nodo == "nota":
            texto, prefijo = (crudo or "").strip().strip("/").strip(), None
        else:
            texto, prefijo = _limpiar(crudo)

        # El carril declarado (:::clase) manda; el prefijo de la etiqueta es el
        # respaldo. Si el analista se tomo la molestia de escribir la clase, esa
        # es su intencion explicita.
        if m["clase"]:
            actor = normalizar_actor(m["clase"])
        elif prefijo:
            actor = normalizar_actor(prefijo)
        else:
            actor = None

        nodo = Nodo(
            id=nid,
            texto=texto,
            clase_nodo=clase_nodo,
            actor=actor,
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
        crudo_et = m["et1"] or m["et2"] or m["et3"] or ""
        # Solo el '<br/>' -> espacio: a diferencia de _limpiar (texto de
        # nodo), una etiqueta de arista no lleva prefijo de actor que quitar.
        et = re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", crudo_et)).strip() or None
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
                r.huecos.append(Hueco(
                    "falta_dato", "MMD-02", "flujo",
                    f"la arista {a.de}->{a.a} referencia un nodo no declarado: {extremo}",
                ))

    # Una compuerta no la "ejecuta" nadie: es una decision del flujo. Pedir su
    # actor ensuciaba la lista con huecos imposibles de contestar.
    SIN_ACTOR = ("inicio_fin", "nota", "compuerta")
    for n in r.nodos:
        if n.actor is None and n.clase_nodo not in SIN_ACTOR:
            r.huecos.append(Hueco(
                "falta_dato", "MMD-03", n.id,
                f"la tarea «{n.texto}» no declara carril (:::clase); no se "
                "puede saber qué actor la ejecuta",
            ))
        if n.clase_nodo == "compuerta" and not n.campos:
            r.huecos.append(Hueco(
                "falta_dato", "MMD-04", n.id,
                f"la compuerta ({n.texto[:50]}) no nombra ningún campo @@; "
                "la condición debe capturarse a mano",
            ))

    r.aristas = [a for a in r.aristas if a.de in ids and a.a in ids]
    return r
