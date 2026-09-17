"""Arma lo que ve el modelo para un lote de huecos DIC-08: ni mas ni menos.

- La prosa sale del propio mensaje del hueco.
- Los candidatos son los campos capturados en la misma pantalla o antes,
  sin el propio campo: una condicion no puede mirar al futuro.
- Van los valores TECNICOS del catalogo, para que la respuesta sea verificable.
- No va el AS-IS, ni el TO-BE, ni "Ejemplo Real" (el manifiesto ya no la
  conserva; `CampoCandidato` no tiene por donde colarla).
"""
import json
import re

from pydantic import BaseModel

from gpmc.nucleo.manifiesto import Manifiesto

RE_PROSA = re.compile(r"no se pudo interpretar: «(.*?)»", re.S)


class CampoCandidato(BaseModel):
    nombre: str
    etiqueta: str
    tipo: str
    valores: list[str] = []
    pantalla: str


class HuecoDic08(BaseModel):
    ubicacion: str
    campo: str
    etiqueta: str
    pantalla: str
    prosa: str
    candidatos: list[str]


class ContextoLote(BaseModel):
    campos: list[CampoCandidato] = []
    huecos: list[HuecoDic08] = []
    omitidos: list[tuple] = []   # (ubicacion, motivo)


def _campos_por_pantalla(m: Manifiesto) -> list:
    """[(indice_pantalla, pantalla_id, Campo)] en orden de captura."""
    out = []
    for i, p in enumerate(m.pantallas):
        for c in p.campos:
            out.append((i, p.id, c))
    return out


def contexto_dic08(m: Manifiesto, huecos: list) -> ContextoLote:
    ctx = ContextoLote()
    todos = _campos_por_pantalla(m)
    indice_de = {p.id: i for i, p in enumerate(m.pantallas)}
    usados = set()
    for h in huecos:
        if h.codigo != "DIC-08" or "::" not in h.ubicacion:
            continue
        pantalla_id, nombre = h.ubicacion.split("::", 1)
        mprosa = RE_PROSA.search(h.mensaje or "")
        if not mprosa or pantalla_id not in indice_de:
            ctx.omitidos.append((h.ubicacion, "sin_prosa"))
            continue
        idx = indice_de[pantalla_id]
        propio = next((c for (i, pid, c) in todos if pid == pantalla_id and c.nombre == nombre), None)
        candidatos = [c.nombre for (i, pid, c) in todos if i <= idx and c.nombre != nombre]
        ctx.huecos.append(HuecoDic08(
            ubicacion=h.ubicacion, campo=nombre,
            etiqueta=(propio.etiqueta if propio and propio.etiqueta else nombre),
            pantalla=pantalla_id, prosa=mprosa.group(1).strip(), candidatos=candidatos))
        usados.update(candidatos)
    ctx.campos = [
        CampoCandidato(nombre=c.nombre, etiqueta=c.etiqueta or c.nombre, tipo=str(c.tipo),
                       valores=[o.valor for o in (c.catalogo or [])], pantalla=pid)
        for (i, pid, c) in todos if c.nombre in usados
    ]
    return ctx


def estimar_tokens(ctx: ContextoLote) -> int:
    """Estimacion burda: 4 caracteres por token sobre el JSON serializado."""
    return len(json.dumps(ctx.model_dump(exclude={"omitidos"}), ensure_ascii=False)) // 4


def _subconjunto(ctx: ContextoLote, huecos: list) -> ContextoLote:
    usados = {n for h in huecos for n in h.candidatos}
    return ContextoLote(campos=[c for c in ctx.campos if c.nombre in usados], huecos=list(huecos))


def partir_lote(ctx: ContextoLote, max_tokens: int) -> list:
    """Parte por la mitad, recursivamente, hasta que cada parte quepa. Un hueco
    que no cabe ni solo se descarta (queda anotado en `omitidos` de la parte)."""
    if not ctx.huecos:
        return []
    if estimar_tokens(ctx) <= max_tokens:
        return [ctx]
    if len(ctx.huecos) == 1:
        solo = _subconjunto(ctx, [])
        solo.omitidos = [(ctx.huecos[0].ubicacion, "tope_tokens")]
        return [solo]
    mitad = len(ctx.huecos) // 2
    return (partir_lote(_subconjunto(ctx, ctx.huecos[:mitad]), max_tokens)
            + partir_lote(_subconjunto(ctx, ctx.huecos[mitad:]), max_tokens))
