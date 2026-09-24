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
_LINEA_REQ = re.compile(r"^\s*[-*]?\s*\*\*Requisitos[^*]*\*\*:?\s*(.*)$", re.I)
_ITEM = re.compile(r"^\s+[-*]\s+(.*)$")


def _limpio(item: str) -> str:
    # Hasta la raya o el parentesis: lo que sigue es nota del analista.
    t = re.split(r"\s+[—–-]\s+|\s*\(", item, maxsplit=1)[0]
    return t.strip().rstrip(".").strip()


def requisitos_del_as_is(as_is: str) -> list:
    lineas = (as_is or "").splitlines()
    salida = []
    for i, linea in enumerate(lineas):
        m = _LINEA_REQ.match(linea)
        if not m:
            continue
        resto = m.group(1).strip()
        if resto:
            partes = re.split(r",|\s+y\s+", resto)
            salida += [r for r in (_limpio(p) for p in partes) if r]
            continue
        for sig in lineas[i + 1:]:
            mi = _ITEM.match(sig)
            if not mi:
                break
            r = _limpio(mi.group(1))
            if r:
                salida.append(r)
    return salida


def _casa(requisito: str, etiqueta: str) -> bool:
    a, b = clave(requisito), clave(etiqueta)
    return bool(a) and bool(b) and (a in b or b in a)


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
    return huecos
