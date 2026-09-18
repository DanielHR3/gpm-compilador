"""El filtro determinista: lo que no pasa aqui no se le ensena al analista.

Aplica ANTES de mostrar las mismas reglas que `POST /resolver` aplica al guardar
(campo existe, valor en catalogo) y una mas: el campo se captura antes o en la
misma pantalla. Para DIC-08 la salida es cerrada, asi que no hace falta un
segundo modelo verificando.
"""
from typing import Optional

from gpmc.extractores.diccionario import _babel
from gpmc.nucleo.manifiesto import Clausula, Condicion, Manifiesto

VEREDICTOS = ("aceptable", "campo_inexistente", "autorreferencia", "campo_futuro",
              "valor_fuera_de_catalogo", "esquema_invalido", "modelo_declino", "sin_respuesta")


def _indice(m: Manifiesto) -> dict:
    """nombre_campo -> (indice_pantalla, Campo)"""
    out = {}
    for i, p in enumerate(m.pantallas):
        for c in p.campos:
            out.setdefault(c.nombre, (i, c))
    return out


def _valor_tecnico(campo, igual: str) -> Optional[str]:
    """El valor tecnico del catalogo que casa con `igual` (por valor o por
    etiqueta, sin acentos ni mayusculas); `igual` tal cual si no hay catalogo;
    None si hay catalogo y no casa."""
    if not campo.catalogo:
        return igual
    b = _babel(igual)
    for o in campo.catalogo:
        if b in (_babel(o.valor), _babel(o.etiqueta)):
            return o.valor
    return None


def verificar(condicion: Condicion, ubicacion: str, m: Manifiesto):
    if "::" not in ubicacion:
        return "esquema_invalido", None
    pantalla_id, propio = ubicacion.split("::", 1)
    idx_propio = next((i for i, p in enumerate(m.pantallas) if p.id == pantalla_id), None)
    if idx_propio is None:
        return "esquema_invalido", None
    indice = _indice(m)

    partes = [(condicion.campo, condicion.igual, condicion.operador)] + [
        (cl.campo, cl.igual, cl.operador) for cl in condicion.y]
    normalizadas = []
    for campo_nombre, igual, op in partes:
        if campo_nombre == propio:
            return "autorreferencia", None
        if campo_nombre not in indice:
            return "campo_inexistente", None
        i, campo = indice[campo_nombre]
        if i > idx_propio:
            return "campo_futuro", None
        v = _valor_tecnico(campo, igual)
        if v is None:
            return "valor_fuera_de_catalogo", None
        normalizadas.append((campo_nombre, v, op))

    (c0, v0, o0), resto = normalizadas[0], normalizadas[1:]
    try:
        cond = Condicion(campo=c0, igual=v0, operador=o0,
                         y=[Clausula(campo=c, igual=v, operador=o) for c, v, o in resto])
    except Exception:
        return "esquema_invalido", None
    return "aceptable", cond
