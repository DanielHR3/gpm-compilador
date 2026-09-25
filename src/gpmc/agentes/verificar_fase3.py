"""Tres cruces deterministas entre el AS-IS y los borradores generados.

Es la misma filosofia que `medir-ia`: no hay un segundo modelo juzgando. Lo que
el extractor ya reporta no se repite aqui; se anaden solo los cruces que el
extractor no puede hacer porque no lee el AS-IS como lista de requisitos.
"""
import re
from typing import Optional

from gpmc.extractores import diccionario as ext_dicc
from gpmc.extractores import mermaid as ext_mmd
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.planeacion.registro import clave

_BLOQUE_MERMAID = re.compile(r"```mermaid(.*?)```", re.S)
# Las formas medidas en la boveda de Simplificacion (2026-09-24): `**Requisitos:**`,
# `**Requisitos documentales:**`, `**Requisitos documentales**:`, `**Requisitos (ficha
# RUTS):**`, `**Requisitos propios:**`... con la lista en la misma linea o en items
# anidados debajo. Un AS-IS puede traer mas de una lista; se suman todas.
# Las palabras con que un AS-IS cuenta que el ciudadano vuelve a entregar tras
# una revision (Reposicion: «¿Solventa la informacion? Si, regresa a entregar
# de nuevo»). Si aparecen y el diagrama compilable no regresa a ninguna tarea,
# falta el ciclo de correccion que el equipo siempre modela (GEN-02).
_CICLO_EN_AS_IS = re.compile(r"solvent|subsan|correg|correcci[oó]n|observacion", re.I)
_RAMA_CORRECCION = re.compile(r"correcci[oó]n|corregir|solventar|subsanar|observacion", re.I)
_LINEA_REQ = re.compile(r"^\s*[-*]?\s*\*\*Requisitos[^*]*\*\*:?\s*(.*)$", re.I)
_ITEM = re.compile(r"^\s+[-*]\s+(.*)$")


def _limpio(item: str) -> str:
    # Hasta la raya o el parentesis: lo que sigue es nota del analista.
    t = re.split(r"\s+[—–-]\s+|\s*\(", item, maxsplit=1)[0]
    return t.strip().rstrip(".").strip()


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


def _casa(requisito: str, etiqueta: str) -> bool:
    a, b = clave(requisito), clave(etiqueta)
    return bool(a) and bool(b) and (a in b or b in a)


def _vuelve_atras(rm) -> bool:
    """True si alguna arista regresa a un nodo ya alcanzado desde el inicio:
    la vuelta «correccion -> revision»."""
    salientes = {}
    for a in rm.aristas:
        salientes.setdefault(a.de, []).append(a.a)
    entrantes = {a.a for a in rm.aristas}
    orden = {}
    pendientes = [n.id for n in rm.nodos if n.id not in entrantes]
    while pendientes:
        n = pendientes.pop(0)
        if n in orden:
            continue
        orden[n] = len(orden)
        pendientes += salientes.get(n, [])
    return any(a.a in orden and a.de in orden and orden[a.a] <= orden[a.de] for a in rm.aristas)


def _gen02(as_is: str, rm) -> list:
    huecos = []
    tipo = {n.id: n.clase_nodo for n in rm.nodos}
    for a in rm.aristas:
        if (tipo.get(a.de) == "compuerta" and a.etiqueta and _RAMA_CORRECCION.search(a.etiqueta)
                and tipo.get(a.a) == "inicio_fin"):
            huecos.append(Hueco(
                "falta_dato", "GEN-02", "flujo",
                f"la rama «{a.etiqueta}» de la compuerta «{a.de}» termina en Fin: una corrección "
                f"vuelve a una pantalla del ciudadano y de ahí a la revisión, no cierra el trámite",
            ))
    m = _CICLO_EN_AS_IS.search(as_is or "")
    if m and not huecos and not _vuelve_atras(rm):
        huecos.append(Hueco(
            "falta_dato", "GEN-02", "flujo",
            f"el AS-IS habla de solventar («{m.group(0)}») y el diagrama compilable no regresa a "
            f"ninguna tarea: falta el ciclo de corrección (revisión → dictamen → corrección del "
            f"ciudadano → vuelta a la revisión)",
        ))
    return huecos


def verificar_cruzado(as_is: str, tobe: str, m: Optional[Manifiesto]) -> list:
    huecos = []
    if m is None:
        return huecos
    campos = [c for p in m.pantallas for c in p.campos]
    archivos = [c for c in campos if c.tipo == "file"]
    for req in requisitos_del_as_is(as_is):
        if any(_casa(req, c.etiqueta) for c in archivos):
            continue
        huecos.append(Hueco(
            "falta_dato", "GEN-01", "requisitos",
            f"El AS-IS pide «{req}» y el Diccionario propuesto no lo captura como "
            f"un campo de tipo Archivo.",
        ))
    bloques = _BLOQUE_MERMAID.findall(tobe or "")
    if not bloques:
        return huecos
    nombres = {c.nombre for c in campos}
    rm = ext_mmd.extraer(bloques[0], campos_declarados=sorted(nombres))
    pantallas = {ext_dicc._babel(p.nombre) for p in m.pantallas}
    for n in rm.nodos:
        if n.clase_nodo == "compuerta":
            for campo in n.campos:
                if campo not in nombres:
                    huecos.append(Hueco(
                        "falta_dato", "MMD-04", n.id,
                        f"la compuerta «{n.texto}» decide con @@{campo}, que no existe "
                        f"en el Diccionario propuesto",
                    ))
        elif n.clase_nodo == "tarea":
            texto = n.texto.split(":", 1)[1] if ":" in n.texto else n.texto
            if ext_dicc._babel(texto) not in pantallas:
                huecos.append(Hueco(
                    "falta_dato", "FLU-02", n.id,
                    f"la tarea «{n.texto}» del TO-BE no casa con ninguna pantalla del "
                    f"Diccionario propuesto",
                ))
    huecos += _gen02(as_is, rm)
    return huecos
