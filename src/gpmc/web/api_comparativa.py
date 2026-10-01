"""API de la comparativa de antes y despues: `/api/v1/expedientes/{sid}/comparativa`.

Lee los insumos de la sesion, llama a `comparativa.armar` y responde. Desde el
2026-10-01 tambien orquesta al agente que completa los lados vacios y propone
puntos de mejora: lo lanza en segundo plano y persiste su resultado en
`comparativa.json`. Importa de `gpmc.web.sesiones`, nunca de `gpmc.web.app`.
"""
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from gpmc.agentes.comparativa import analizar
from gpmc.agentes.fase3 import modo_pruebas, puede_generar
from gpmc.agentes.proveedor import NingunProveedor
from gpmc.comparativa.armar import (
    METRICAS, Comparativa, a_dict, comparar, lados_sin_dato, no_disponible)
from gpmc.comparativa.documento import a_html
from gpmc.comparativa.documentos import desde_dicts, reconciliar
from gpmc.comparativa.propuestas import (
    conservar_descartes, mejoras_a_dicts, mejoras_desde, propuestas_desde)
from gpmc.extractores import as_is as ext_as_is
from gpmc.extractores import rediseno as ext_rediseno
from gpmc.web.sesiones import (
    INSUMOS,
    carpeta_de,
    comparativa_de,
    documentos_de,
    escribir_comparativa,
    manifiesto_de,
)

log = logging.getLogger("gpmc.web.api_comparativa")

_CLAVES = {k for k, _ in METRICAS}

# El hilo de fondo muere si el servicio se reinicia a media tarea. Misma
# ventana que «Documentos del tramite» y la Fase 3.
MAX_ANALIZANDO = timedelta(minutes=20)
MOTIVO_INTERRUMPIDO = ("El análisis se interrumpió (el servidor se reinició o falló a media "
                       "tarea). Vuelve a intentarlo.")
MOTIVO_SIN_AS_IS = ("No se cargó el Análisis AS-IS en este expediente: sin el antes no hay "
                    "comparativa. Vuelve a cargar el expediente con su AS-IS.")

# Un candado por sesion alrededor de cada leer-modificar-escribir de
# `comparativa.json`: el hilo del analisis, lo que declara una persona y los
# descartes escriben el mismo archivo.
_CANDADOS: dict = {}
_CANDADO_DE_CANDADOS = threading.Lock()


def _candado(sid: str) -> threading.Lock:
    with _CANDADO_DE_CANDADOS:
        return _CANDADOS.setdefault(sid, threading.Lock())


class Declaracion(BaseModel):
    clave: str
    antes: str = Field(default="", max_length=80)
    despues: str = Field(default="", max_length=80)


class Descarte(BaseModel):
    descartada: bool = True


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _leer(carpeta: Path, insumo: str) -> str:
    ruta = carpeta / INSUMOS[insumo]
    if not ruta.is_file():
        return ""
    return ruta.read_text(encoding="utf-8", errors="replace")


def _analisis_de(d: dict) -> dict:
    """Lo guardado del agente, con un `analizando` viejo leido como error."""
    a = d.get("analisis")
    if not isinstance(a, dict):
        return {}
    if a.get("estado") != "analizando":
        return a
    try:
        iniciado = datetime.fromisoformat(a.get("iniciado") or "")
    except ValueError:
        return {**a, "estado": "error", "motivo": MOTIVO_INTERRUMPIDO}
    if datetime.now(timezone.utc) - iniciado <= MAX_ANALIZANDO:
        return a
    return {**a, "estado": "error", "motivo": MOTIVO_INTERRUMPIDO}


def _armar(raiz: Path, sid: str, con_agente: bool = True
           ) -> Tuple[Optional[Comparativa], Optional[JSONResponse]]:
    """`con_agente=False` arma solo lo que cuenta el compilador: es la base
    sobre la que se decide que lados se le piden al modelo."""
    carpeta = carpeta_de(raiz, sid)
    m = manifiesto_de(raiz, sid)
    if carpeta is None or m is None:
        return None, JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
    as_is = _leer(carpeta, "as_is")
    if not as_is.strip():
        return no_disponible(MOTIVO_SIN_AS_IS), None
    guardado = comparativa_de(carpeta)
    declaradas = guardado.get("declaradas")
    analisis = _analisis_de(guardado) if con_agente else {}
    # Lo que una persona ya decidio en «Documentos del tramite», reconciliado
    # con el manifiesto de ahora.
    revisados = reconciliar(desde_dicts((documentos_de(carpeta) or {}).get("documentos")), m)
    return comparar(ext_as_is.extraer(as_is), ext_rediseno.extraer(_leer(carpeta, "to_be")),
                    m, declaradas if isinstance(declaradas, dict) else None,
                    documentos=revisados or None,
                    propuestas=propuestas_desde(analisis.get("propuestas")),
                    mejoras=mejoras_desde(analisis.get("mejoras"))), None


def crear_router_comparativa(raiz: Path, proveedor=None,
                             entorno: Optional[dict] = None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")
    proveedor = proveedor if proveedor is not None else NingunProveedor()
    hay_ia = not isinstance(proveedor, NingunProveedor)

    def _motivo_para_no_analizar() -> Optional[str]:
        if not hay_ia:
            return "No hay un proveedor de IA configurado en el servidor."
        return puede_generar(entorno)

    def _estado_del_analisis(carpeta: Path) -> dict:
        a = _analisis_de(comparativa_de(carpeta))
        motivo = _motivo_para_no_analizar()
        return {"estado": a.get("estado") or "sin_analizar", "motivo": a.get("motivo"),
                "pasos": a.get("pasos") or [], "puede_analizar": motivo is None,
                "motivo_analizar": motivo,
                "pruebas": motivo is None and modo_pruebas(entorno),
                "modelo": a.get("modelo") or "", "terminado": a.get("terminado")}

    def _respuesta(sid: str):
        c, error = _armar(raiz, sid)
        if error is not None:
            return error
        return {**a_dict(c), "analisis": _estado_del_analisis(carpeta_de(raiz, sid))}

    def _anotador(carpeta: Path, sid: str):
        def avisar(mensaje: str) -> None:
            with _candado(sid):
                d = comparativa_de(carpeta)
                a = d.get("analisis") if isinstance(d.get("analisis"), dict) else {}
                a["pasos"] = list(a.get("pasos") or []) + [{"t": _ahora(), "mensaje": mensaje}]
                escribir_comparativa(carpeta, {**d, "analisis": a})
        return avisar

    def analizar_en_segundo_plano(sid: str, usuario: str) -> None:
        carpeta, m = carpeta_de(raiz, sid), manifiesto_de(raiz, sid)
        base, _ = _armar(raiz, sid, con_agente=False)
        if carpeta is None or m is None or base is None:
            return
        a = analizar(_leer(carpeta, "as_is"), _leer(carpeta, "to_be"), m, lados_sin_dato(base),
                     proveedor, raiz, sid, avisar=_anotador(carpeta, sid), usuario=usuario)
        log.info("comparativa sid=%s estado=%s propuestas=%s mejoras=%s",
                 sid, a.estado, len(a.propuestas), len(a.mejoras))
        with _candado(sid):
            # Lo previo se lee AHORA y no al empezar: la persona pudo descartar
            # un punto o declarar un dato mientras el agente trabajaba.
            d = comparativa_de(carpeta)
            previo = d.get("analisis") if isinstance(d.get("analisis"), dict) else {}
            previas = mejoras_desde(previo.get("mejoras"))
            if a.estado == "error":
                # Un fallo de red no borra trabajo: se queda lo que habia.
                propuestas, mejoras = previo.get("propuestas") or [], previas
            else:
                propuestas = a.propuestas
                # Si solo fallo la segunda llamada, los puntos anteriores siguen valiendo.
                mejoras = conservar_descartes(mejoras_desde(a.mejoras), previas) \
                    if a.mejoras or "mejoras_no_disponibles" not in a.alertas else previas
            escribir_comparativa(carpeta, {**d, "analisis": {
                "estado": a.estado, "motivo": a.motivo, "modelo": a.modelo or previo.get("modelo"),
                "iniciado": previo.get("iniciado"), "terminado": _ahora(),
                "pasos": previo.get("pasos") or [], "alertas": a.alertas,
                "propuestas": propuestas, "mejoras": mejoras_a_dicts(mejoras)}})

    @r.get("/expedientes/{sid}/comparativa")
    async def leer_comparativa(sid: str):
        return _respuesta(sid)

    @r.post("/expedientes/{sid}/comparativa/declarar")
    async def declarar(sid: str, cuerpo: Declaracion):
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None or manifiesto_de(raiz, sid) is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        if cuerpo.clave not in _CLAVES:
            return JSONResponse(status_code=422, content={
                "error": f"«{cuerpo.clave}» no es una métrica de la comparativa"})
        with _candado(sid):
            d = comparativa_de(carpeta)
            declaradas = d.get("declaradas")
            if not isinstance(declaradas, dict):
                declaradas = {}
            declaradas[cuerpo.clave] = {
                "antes": cuerpo.antes.strip(),
                "despues": cuerpo.despues.strip(),
                "cuando": _ahora(),
            }
            d["declaradas"] = declaradas
            escribir_comparativa(carpeta, d)
        return _respuesta(sid)

    @r.post("/expedientes/{sid}/comparativa/analizar")
    async def analizar_comparativa(sid: str, request: Request, tareas: BackgroundTasks):
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None or manifiesto_de(raiz, sid) is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        motivo = _motivo_para_no_analizar()
        if motivo:
            return JSONResponse(status_code=409, content={"error": motivo})
        if not _leer(carpeta, "as_is").strip():
            return JSONResponse(status_code=409, content={"error": MOTIVO_SIN_AS_IS})
        with _candado(sid):
            d = comparativa_de(carpeta)
            previo = _analisis_de(d)
            if previo.get("estado") == "analizando":
                return JSONResponse(status_code=202, content={"estado": "analizando"})
            # Lo anterior se conserva mientras corre el nuevo: la pagina no se
            # vacia a media tarea.
            escribir_comparativa(carpeta, {**d, "analisis": {
                **previo, "estado": "analizando", "motivo": None, "iniciado": _ahora(),
                "pasos": []}})
        quien = getattr(request.state, "usuario", None)
        tareas.add_task(analizar_en_segundo_plano, sid, quien.correo if quien else "anonimo")
        return JSONResponse(status_code=202, content={"estado": "analizando"})

    @r.post("/expedientes/{sid}/comparativa/mejoras/{mejora_id}/descartar")
    async def descartar_mejora(sid: str, mejora_id: str, cuerpo: Descarte):
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None or manifiesto_de(raiz, sid) is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        with _candado(sid):
            d = comparativa_de(carpeta)
            a = d.get("analisis") if isinstance(d.get("analisis"), dict) else {}
            mejoras = mejoras_desde(a.get("mejoras"))
            mejora = next((x for x in mejoras if x.id == mejora_id), None)
            if mejora is None:
                return JSONResponse(status_code=404,
                                    content={"error": "punto de mejora no encontrado"})
            mejora.descartada = cuerpo.descartada
            escribir_comparativa(carpeta, {**d, "analisis": {
                **a, "mejoras": mejoras_a_dicts(mejoras)}})
        return _respuesta(sid)

    @r.get("/expedientes/{sid}/comparativa/documento")
    async def documento(sid: str):
        c, error = _armar(raiz, sid)
        if error is not None:
            return error
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", c.tramite)[:60].strip("-") or "tramite"
        return Response(
            a_html(c),
            media_type="text/html; charset=utf-8",
            headers={"content-disposition":
                     f'attachment; filename="Antes-y-despues-{base}.html"'},
        )

    return r
