"""Generador de propuestas para DIC-08: un lote, una llamada, todo verificado.

Devuelve TODAS las propuestas —aceptables y rechazadas— porque el registro de
demostrabilidad necesita las dos. Quien las muestra decide (la API filtra a
`aceptable` sin decision).
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ValidationError

from gpmc.agentes.bitacora import Interaccion, registrar
from gpmc.agentes.contexto import ContextoLote, contexto_dic08, partir_lote
from gpmc.agentes.prompt import (ESQUEMA_DIC08, INSTRUCCION_DIC08, VERSION_PROMPT,
                                 hash_instruccion, serializar_datos)
from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida
from gpmc.agentes.verificar import verificar
from gpmc.nucleo.manifiesto import Condicion, Manifiesto


class Cita(BaseModel):
    fuente: Literal["Diccionario de Datos"] = "Diccionario de Datos"
    pantalla: str
    pantalla_nombre: str
    campo: str
    texto: str


class Propuesta(BaseModel):
    id: str
    ubicacion: str
    condicion: Optional[Condicion] = None
    motivo_modelo: Optional[str] = None
    confianza: Literal["alta", "media", "baja"] = "baja"
    cita: Cita
    veredicto: str
    decision: Optional[Literal["aceptada", "corregida", "descartada"]] = None
    condicion_final: Optional[Condicion] = None
    creada: str
    decidida: Optional[str] = None


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cita(m: Manifiesto, h) -> Cita:
    p = next((p for p in m.pantallas if p.id == h.pantalla), None)
    return Cita(pantalla=h.pantalla, pantalla_nombre=(p.nombre if p else h.pantalla),
                campo=h.campo, texto=h.prosa)


def _llamar(proveedor, datos: str):
    """Una llamada con un reintento SOLO ante ErrorDeRed. RespuestaInvalida no
    se reintenta: el modelo ya contesto, y contesto mal."""
    try:
        return proveedor.completar(INSTRUCCION_DIC08, datos, ESQUEMA_DIC08)
    except ErrorDeRed:
        return proveedor.completar(INSTRUCCION_DIC08, datos, ESQUEMA_DIC08)


def _parsear(texto: str) -> dict:
    try:
        d = json.loads(texto)
    except (TypeError, ValueError) as e:
        raise RespuestaInvalida(str(e))
    if not isinstance(d, dict) or not isinstance(d.get("propuestas"), list):
        raise RespuestaInvalida("sin lista 'propuestas'")
    return d


def _confianza(v) -> str:
    return v if v in ("alta", "media", "baja") else "baja"


def _procesar_parte(m: Manifiesto, parte: ContextoLote, proveedor, raiz: Path, sid: str,
                    alertas: list) -> list:
    datos = serializar_datos(parte)
    it = Interaccion(sid=sid, proveedor=proveedor.nombre, modelo="", version_prompt=VERSION_PROMPT,
                     solicitud={"huecos": [h.ubicacion for h in parte.huecos],
                                "n_campos": len(parte.campos), "n_caracteres": len(datos)},
                     instruccion_hash=hash_instruccion(), estado="procesada", alertas=list(alertas))
    try:
        resp = _llamar(proveedor, datos)
    except ErrorDeRed as e:
        it.estado, it.alertas = "error", it.alertas + ["error_de_red"]
        it.respuesta = str(e)
        registrar(raiz, it)
        raise
    it.modelo, it.respuesta = resp.modelo, resp.texto
    it.tokens_entrada, it.tokens_salida, it.duracion_ms = resp.tokens_entrada, resp.tokens_salida, resp.duracion_ms
    try:
        cuerpo = _parsear(resp.texto)
    except RespuestaInvalida:
        it.estado, it.alertas = "error", it.alertas + ["respuesta_invalida"]
        registrar(raiz, it)
        raise

    por_ubic = {h.ubicacion: h for h in parte.huecos}
    salida = {}
    for item in cuerpo["propuestas"]:
        if not isinstance(item, dict):
            it.alertas.append("respuesta_invalida")
            continue
        ubic = item.get("ubicacion")
        if ubic not in por_ubic or ubic in salida:
            it.alertas.append("ubicacion_inventada")
            continue
        h = por_ubic[ubic]
        base = dict(id=uuid.uuid4().hex, ubicacion=ubic, cita=_cita(m, h), creada=_ahora(),
                    confianza=_confianza(item.get("confianza")))
        if item.get("condicion") is None:
            salida[ubic] = Propuesta(veredicto="modelo_declino", motivo_modelo=item.get("motivo"), **base)
            continue
        try:
            cond = Condicion(**item["condicion"])
        except (ValidationError, TypeError):
            salida[ubic] = Propuesta(veredicto="esquema_invalido", **base)
            continue
        veredicto, normalizada = verificar(cond, ubic, m)
        salida[ubic] = Propuesta(veredicto=veredicto, condicion=normalizada, **base)
    for ubic, h in por_ubic.items():
        if ubic not in salida:
            salida[ubic] = Propuesta(id=uuid.uuid4().hex, ubicacion=ubic, cita=_cita(m, h),
                                     creada=_ahora(), veredicto="sin_respuesta")
    if any(p.veredicto != "aceptable" for p in salida.values()):
        it.estado = "sujeta_a_validacion"
    registrar(raiz, it)
    return [salida[h.ubicacion] for h in parte.huecos]


def proponer_lote(m: Manifiesto, huecos: list, proveedor, raiz: Path, sid: str,
                  max_tokens: int = 24000) -> list:
    ctx = contexto_dic08(m, huecos)
    if not ctx.huecos:
        return []
    partes = partir_lote(ctx, max_tokens)
    alertas = ["lote_partido"] if len(partes) > 1 else []
    resultado = []
    for parte in partes:
        if not parte.huecos:
            continue
        parte_alertas = alertas + [f"hueco_omitido:{u}" for (u, _) in parte.omitidos]
        resultado.extend(_procesar_parte(m, parte, proveedor, raiz, sid, parte_alertas))
    return resultado
