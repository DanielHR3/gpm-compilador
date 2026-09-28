"""Lee el Analisis AS-IS como datos: pasos, requisitos, tiempo, sistemas y fricciones.

Hasta el 2026-09-28 del AS-IS solo se sacaban metadatos y requisitos. La
comparativa de antes y despues necesita el resto. La forma es la medida sobre
los seis expedientes del equipo de Simplificacion: viñetas `- **Nombre:** valor`
bajo «Estado actual», con los pasos anidados o en la misma linea con `→`.

Es tolerante a proposito: lo que no se lee queda vacio y la comparativa lo
reporta como «sin dato». Fallar hacia vacio no produce cifras falsas.
"""
import re
from dataclasses import dataclass, field

from gpmc.planeacion.registro import clave

# Las formas medidas en la boveda de Simplificacion (2026-09-24): `**Requisitos:**`,
# `**Requisitos documentales:**`, `**Requisitos (ficha RUTS):**`... con la lista
# en la misma linea o en items anidados debajo. Un AS-IS puede traer mas de una
# lista de requisitos; se suman todas.
_LINEA_REQ = re.compile(r"^\s*[-*]?\s*\*\*Requisitos[^*]*\*\*:?\s*(.*)$", re.I)
_ITEM = re.compile(r"^\s+[-*]\s+(.*)$")
_VINETA = re.compile(r"^\s*[-*]?\s*\*\*([^*]+?)\*\*:?\s*(.*)$")
_HIJO = re.compile(r"^(\s+)([-*]|\d+[.)])\s+(.*)$")
_FILA_TABLA = re.compile(r"^\s*\|(.+)\|\s*$")
PUNTO = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")
_SECCION_FRICCION = re.compile(r"^##+\s+Fricci[oó]n", re.I)
_NEGRITA_INICIAL = re.compile(r"^\*\*(.+?)\*\*")
_RAYA = re.compile(r"\s+[—–]\s+")
# Tras el dato viene la nota del analista: «13 dias habiles, confirmado con…»
# o una frase nueva: «150 minutos en total. El caso real observado…».
_CORTE = re.compile(r"\s+[—–]\s+|[,;(]|\.\s+(?=[A-ZÁÉÍÓÚÑ])")


@dataclass
class EstadoActual:
    canal: str = ""
    pasos: list = field(default_factory=list)
    requisitos: list = field(default_factory=list)
    tiempo: str = ""
    costo: str = ""
    sistemas: list = field(default_factory=list)
    fricciones: list = field(default_factory=list)


def _limpio(item: str) -> str:
    # Hasta la raya o el parentesis: lo que sigue es nota del analista.
    t = re.split(r"\s+[—–-]\s+|\s*\(", item, maxsplit=1)[0]
    # Quitar una nota entre parentesis deja dos espacios donde estaba.
    return re.sub(r"\s+", " ", t).strip().rstrip(".").strip()


def _enumeracion(texto: str) -> list:
    """«a, b y c» -> [a, b, c]. Lo que va entre parentesis es nota y se quita
    antes de partir: «Identificacion oficial (INE, pasaporte o cartilla)» es
    UN requisito. La «y» solo separa en el ultimo tramo: «pago de derechos y
    aprovechamientos» sin comas es un solo requisito."""
    sin_notas = re.sub(r"\([^()]*\)", "", texto)
    partes = [p for p in sin_notas.split(",")]
    if len(partes) > 1:
        # «a, b, y c»: la coma antes de la «y» deja el ultimo tramo como «y c».
        ultimo = re.sub(r"^\s*y\s+", "", partes[-1])
        partes = partes[:-1] + re.split(r"\s+y\s+", ultimo.strip(), maxsplit=1)
    return partes


def requisitos_del_as_is(as_is: str) -> list:
    """Las listas de requisitos del AS-IS, en la misma linea o anidadas debajo
    (solo el primer nivel: un sub-item es un detalle del requisito). No se
    leen, a proposito, listas sin sangria, separadas por una linea en blanco o
    numeradas: fallar hacia «no hay requisitos» no produce GEN-01 falsos."""
    lineas = (as_is or "").splitlines()
    salida = []
    for i, linea in enumerate(lineas):
        m = _LINEA_REQ.match(linea)
        if not m:
            continue
        resto = m.group(1).strip()
        if resto:
            salida += [r for r in (_limpio(p) for p in _enumeracion(resto)) if r]
            continue
        sangria = None
        for sig in lineas[i + 1:]:
            mi = _ITEM.match(sig)
            if not mi:
                break
            nivel = len(sig) - len(sig.lstrip())
            if sangria is None:
                sangria = nivel
            if nivel > sangria:
                continue
            r = _limpio(mi.group(1))
            if r:
                salida.append(r)
    return salida


def casa(requisito: str, etiqueta: str) -> bool:
    a, b = clave(requisito), clave(etiqueta)
    return bool(a) and bool(b) and (a in b or b in a)


def titulo_de(item: str) -> str:
    """El titulo en negrita con que el equipo abre un punto; sin negrita, el
    punto entero. Se quita el punto final, que es de la frase y no del titulo."""
    t = (item or "").strip()
    m = _NEGRITA_INICIAL.match(t)
    if m:
        t = m.group(1)
    return t.strip().rstrip(".:").strip()


def _sin_parentesis(texto: str) -> str:
    previo = None
    while previo != texto:
        previo, texto = texto, re.sub(r"\([^()]*\)", "", texto)
    return texto


def _vineta(lineas: list, prefijos: tuple) -> tuple:
    """(resto, hijos, indice) de la PRIMERA viñeta cuyo nombre empieza por
    `prefijos`. La primera y no todas: Prorroga trae dos mediciones de pasos de
    dos fuentes y sumarlas daria una cifra que nadie escribio."""
    for i, linea in enumerate(lineas):
        m = _VINETA.match(linea)
        if not m or not clave(m.group(1)).startswith(prefijos):
            continue
        hijos, sangria = [], None
        for sig in lineas[i + 1:]:
            mh = _HIJO.match(sig)
            if not mh:
                break
            nivel = len(mh.group(1))
            if sangria is None:
                sangria = nivel
            if nivel > sangria:
                continue
            hijos.append((mh.group(2) not in "-*", mh.group(3).strip()))
        # En una lista numerada, una viñeta suelta es un total o una nota
        # («Tiempo interno documentado: 25 minutos»), no un paso mas.
        if any(numerado for numerado, _ in hijos):
            hijos = [h for h in hijos if h[0]]
        return m.group(2).strip(), [t for _, t in hijos], i
    return "", [], -1


def _sin_punto(texto: str) -> str:
    return texto.strip().rstrip(".").strip()


def _pasos_de_tabla(lineas: list, desde: int) -> list:
    """Los pasos cuando vienen en una tabla bajo la viñeta (Prorroga,
    Reposicion). Solo la primera tabla, y solo si tiene una columna que se
    llame «Paso» o «Etapa»: sin ese encabezado no se adivina cual es."""
    columna, salida = None, []
    for linea in lineas[desde:]:
        if linea.strip() and not linea[:1].isspace():
            break
        m = _FILA_TABLA.match(linea)
        if not m:
            if columna is not None:
                break
            continue
        celdas = [c.strip() for c in m.group(1).split("|")]
        if columna is None:
            columna = next((k for k, c in enumerate(celdas)
                            if clave(c) in ("paso", "etapa")), None)
            if columna is None:
                return []
            continue
        if set(celdas[0]) <= set("-: "):
            continue
        if columna < len(celdas) and celdas[columna]:
            salida.append(celdas[columna])
    return salida


def _pasos(lineas: list) -> list:
    resto, hijos, i = _vineta(lineas, ("pasos", "etapas"))
    if hijos:
        return [p for p in (_sin_punto(h) for h in hijos) if p]
    if "→" not in resto:
        return _pasos_de_tabla(lineas, i + 1) if i >= 0 else []
    tramos = resto.split("→")
    # «7 etapas — Recepcion → …»: lo de antes de la raya es la cuenta, no un paso.
    tramos[0] = _RAYA.split(tramos[0])[-1]
    return [p for p in (_sin_punto(t) for t in tramos) if p]


def _dato(lineas: list, prefijos: tuple) -> str:
    resto, _, _ = _vineta(lineas, prefijos)
    return _sin_punto(_CORTE.split(resto, maxsplit=1)[0]) if resto else ""


def _sistemas(lineas: list) -> list:
    resto, _, _ = _vineta(lineas, ("sistemas",))
    return [s for s in (_sin_punto(p) for p in _sin_parentesis(resto).split(",")) if s]


def _fricciones(lineas: list) -> list:
    salida, dentro = [], False
    for linea in lineas:
        if linea.startswith("#"):
            dentro = bool(_SECCION_FRICCION.match(linea))
            continue
        if not dentro or linea[:1].isspace():
            continue
        m = PUNTO.match(linea)
        if m:
            salida.append(titulo_de(m.group(1)))
    return [f for f in salida if f]


def extraer(texto: str) -> EstadoActual:
    lineas = (texto or "").splitlines()
    resto_canal, _, _ = _vineta(lineas, ("canal",))
    resto_costo, _, _ = _vineta(lineas, ("costo",))
    return EstadoActual(
        canal=_sin_punto(resto_canal),
        pasos=_pasos(lineas),
        requisitos=requisitos_del_as_is(texto),
        tiempo=_dato(lineas, ("tiempo",)),
        costo=_sin_punto(resto_costo),
        sistemas=_sistemas(lineas),
        fricciones=_fricciones(lineas),
    )
