"""Interpretacion unica de las reglas de transicion.

Compilador, validador y simulador usan este modulo. Si cada uno interpretara
las reglas por su cuenta, el simulador mentiria sobre lo que hara la plataforma.

Sobre SINTAXIS_ESTRICTA
-----------------------
la guía de modelado interna sostenia que comparar un campo complejo (select, radio)
con == "siempre falla en produccion", y que la forma correcta es
`@@campo->value === 'valor'`. Eso quedo REFUTADO el 2026-08-31:

- Cuatro exports autenticos publicados usan `@@campo == "valor"` sobre campos de
  tipo `select` (constancia-ambiental, pago-de-bases, test-ciudadano-4-pasos,
  busqueda-testamento). No es cierto que la forma con == no exista con campos
  complejos: la usa produccion.
- Prueba de runtime en el portal del ciudadano: un tramite compilado con esta
  constante en False emitio `@@procede=='si'` sobre un `select`, y en el runtime
  el flujo AVANZO al elegir la rama. La tarea de origen solo tenia salidas
  condicionales (sin transicion por defecto), asi que solo pudo avanzar porque una
  regla con == evaluo verdadero. Ver planeacion/actas/2026-08-30-prueba-en-plataforma.md.

La constante se queda en False: la prueba confirma el valor actual, no exige
cambiarlo.
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
    """Traduce una condicion del manifiesto a la sintaxis de regla del .gpm.

    El operador puede ser '==' o '!=': la desigualdad la usan las condiciones de
    visibilidad ('@@tipo_solicitante != \"usuario\"' en busqueda-de-testamento)."""
    desigual = getattr(cond, "operador", "==") == "!="
    if SINTAXIS_ESTRICTA:
        op = "!==" if desigual else "==="
        return f"@@{cond.campo}->value {op} '{cond.igual}'"
    op = "!=" if desigual else "=="
    return f"@@{cond.campo}{op}'{cond.igual}'"


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
