"""Interpretacion unica de las reglas de transicion.

Compilador, validador y simulador usan este modulo. Si cada uno interpretara
las reglas por su cuenta, el simulador mentiria sobre lo que hara la plataforma.

Sobre SINTAXIS_ESTRICTA
-----------------------
la guía de modelado interna sostiene que comparar un campo complejo (select, radio)
con == "siempre falla en produccion", y que la forma correcta es
`@@campo->value === 'valor'`. Los dos exports autenticos disponibles usan la
forma con ==, incluido el producido por una implementacion. La cuestion no se puede
resolver leyendo archivos.

Hasta que una prueba empirica en la plataforma lo determine, se emite la forma
que estos exports muestran y la constante queda apagada. Ver la seccion 9.bis
del documento de diseno.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gpmc.nucleo.manifiesto import Condicion

SINTAXIS_ESTRICTA = False

_COMPARACION = re.compile(
    r"@@(?P<campo>\w+)\s*(?:->value\s*)?(?P<op>===|==|!==|!=)\s*'(?P<valor>[^']*)'"
)
_CAMPO = re.compile(r"@@(\w+)")


def emitir(cond: "Condicion") -> str:
    """Traduce una condicion del manifiesto a la sintaxis de regla del .gpm."""
    if SINTAXIS_ESTRICTA:
        return f"@@{cond.campo}->value === '{cond.igual}'"
    return f"@@{cond.campo}=='{cond.igual}'"


def campos_de(regla: str) -> list[str]:
    """Nombres de campo que aparecen en una regla, en orden y sin repetir."""
    vistos = []
    for nombre in _CAMPO.findall(regla or ""):
        if nombre not in vistos:
            vistos.append(nombre)
    return vistos


def evaluar(regla: str, valores: dict[str, str]) -> bool:
    """Evalua una regla contra los valores capturados.

    Acepta las dos sintaxis en circulacion, porque debe poder recorrer .gpm
    existentes escritos de cualquiera de las dos formas.
    """
    if not regla:
        return True

    partes = [p.strip() for p in re.split(r"&&", regla)]
    resultados = []
    for parte in partes:
        m = _COMPARACION.fullmatch(parte)
        if not m:
            raise ValueError(f"regla no reconocida: {parte!r}")
        actual = valores.get(m["campo"])
        esperado = m["valor"]
        negado = m["op"].startswith("!")
        igual = actual == esperado
        resultados.append(not igual if negado else igual)
    return all(resultados)
