"""API de «Documentos del tramite»: `/api/v1/expedientes/{sid}/documentos`.

Orquesta: lee los insumos de la sesion, llama al agente en segundo plano y
persiste `documentos.json`. Importa de `gpmc.web.sesiones`, nunca de
`gpmc.web.app`.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from gpmc.agentes.documentos import analizar
from gpmc.agentes.fase3 import modo_pruebas, puede_generar
from gpmc.agentes.proveedor import NingunProveedor
from gpmc.comparativa import documentos as docs_tramite
from gpmc.comparativa.pagina_documentos import a_html
from gpmc.web.sesiones import (
    INSUMOS,
    carpeta_de,
    documentos_de,
    escribir_documentos,
    manifiesto_de,
)

log = logging.getLogger("gpmc.web.api_documentos")

# El hilo de fondo muere si el servicio se reinicia a media tarea (launchd lo
# reinicia en cada despliegue). Misma ventana que la Fase 3.
MAX_ANALIZANDO = timedelta(minutes=20)
MOTIVO_INTERRUMPIDO = ("El análisis se interrumpió (el servidor se reinició o falló a media "
                       "tarea). Vuelve a intentarlo o asigna los destinos a mano.")
MOTIVO_SIN_AS_IS = ("No se cargó el Análisis AS-IS en este expediente: no hay documentos de "
                    "antes que revisar.")


class DecisionIn(BaseModel):
    destino: str
    motivo: str = Field(default="", max_length=docs_tramite.MAX_MOTIVO)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _leer(carpeta: Path, insumo: str) -> str:
    ruta = carpeta / INSUMOS[insumo]
    return ruta.read_text(encoding="utf-8", errors="replace") if ruta.is_file() else ""


def _vigente(d: dict) -> dict:
    if d.get("estado") != "analizando":
        return d
    try:
        iniciado = datetime.fromisoformat(d.get("iniciado") or "")
    except ValueError:
        return {**d, "estado": "error", "motivo": MOTIVO_INTERRUMPIDO}
    if datetime.now(timezone.utc) - iniciado <= MAX_ANALIZANDO:
        return d
    return {**d, "estado": "error", "motivo": MOTIVO_INTERRUMPIDO}


def crear_router_documentos(raiz: Path, proveedor, entorno: Optional[dict] = None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")
    hay_ia = not isinstance(proveedor, NingunProveedor)

    def _motivo_para_no_analizar() -> Optional[str]:
        if not hay_ia:
            return "No hay un proveedor de IA configurado en el servidor."
        return puede_generar(entorno)

    def _sesion(sid: str):
        carpeta, m = carpeta_de(raiz, sid), manifiesto_de(raiz, sid)
        if carpeta is None or m is None:
            return None, None
        return carpeta, m

    def _documentos(carpeta: Path, m, d: dict) -> list:
        """Lo guardado, reconciliado con el manifiesto de ahora; sin nada
        guardado, el inventario del lector."""
        docs = docs_tramite.desde_dicts(d.get("documentos"))
        if not docs:
            return docs_tramite.inventario_determinista(_leer(carpeta, "as_is"), m)
        return docs_tramite.reconciliar(docs, m)

    def _estado(carpeta: Path, m) -> dict:
        motivo = _motivo_para_no_analizar()
        comun = {"puede_analizar": motivo is None, "motivo_analizar": motivo,
                 "pruebas": motivo is None and modo_pruebas(entorno)}
        if not _leer(carpeta, "as_is").strip():
            return {"disponible": False, "motivo": MOTIVO_SIN_AS_IS, "estado": "sin_analizar",
                    "motivo_estado": None, "pasos": [], "origen": "lector", "documentos": [],
                    "resumen": docs_tramite.resumen([], m), **comun}
        d = _vigente(documentos_de(carpeta) or {})
        docs = _documentos(carpeta, m, d)
        return {"disponible": True, "motivo": "", "estado": d.get("estado") or "sin_analizar",
                "motivo_estado": d.get("motivo"), "pasos": d.get("pasos") or [],
                "origen": d.get("origen") or "lector",
                "documentos": docs_tramite.a_dicts(docs),
                "resumen": docs_tramite.resumen(docs, m), **comun}

    def _guardar_documentos(carpeta: Path, docs: list) -> None:
        d = _vigente(documentos_de(carpeta) or {})
        estado = d.get("estado") if d.get("estado") in ("lista", "error") else "sin_analizar"
        escribir_documentos(carpeta, {**d, "estado": estado,
                                      "documentos": docs_tramite.a_dicts(docs)})

    def _anotador(carpeta: Path):
        def avisar(mensaje: str) -> None:
            d = documentos_de(carpeta) or {}
            d["pasos"] = list(d.get("pasos") or []) + [{"t": _ahora(), "mensaje": mensaje}]
            escribir_documentos(carpeta, d)
        return avisar

    def analizar_en_segundo_plano(sid: str, usuario: str) -> None:
        carpeta, m = _sesion(sid)
        if carpeta is None:
            return
        previos = docs_tramite.desde_dicts((documentos_de(carpeta) or {}).get("documentos"))
        a = analizar(_leer(carpeta, "as_is"), _leer(carpeta, "to_be"), m, proveedor, raiz, sid,
                     avisar=_anotador(carpeta), usuario=usuario)
        log.info("documentos sid=%s estado=%s n=%s", sid, a.estado, len(a.documentos))
        nuevos = docs_tramite.conservar_decisiones(
            docs_tramite.desde_dicts(a.documentos), previos)
        d = documentos_de(carpeta) or {}
        escribir_documentos(carpeta, {
            "estado": a.estado, "motivo": a.motivo, "origen": a.origen,
            "iniciado": d.get("iniciado"), "pasos": d.get("pasos") or [],
            "documentos": docs_tramite.a_dicts(nuevos)})

    @r.get("/expedientes/{sid}/documentos")
    async def leer_documentos(sid: str):
        carpeta, m = _sesion(sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        return _estado(carpeta, m)

    @r.post("/expedientes/{sid}/documentos/analizar")
    async def analizar_documentos(sid: str, request: Request, tareas: BackgroundTasks):
        carpeta, m = _sesion(sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        motivo = _motivo_para_no_analizar()
        if motivo:
            return JSONResponse(status_code=409, content={"error": motivo})
        if not _leer(carpeta, "as_is").strip():
            return JSONResponse(status_code=409, content={"error": MOTIVO_SIN_AS_IS})
        d = _vigente(documentos_de(carpeta) or {})
        if d.get("estado") == "analizando":
            return JSONResponse(status_code=202, content={"estado": "analizando"})
        escribir_documentos(carpeta, {**d, "estado": "analizando", "motivo": None,
                                      "iniciado": _ahora(), "pasos": []})
        quien = getattr(request.state, "usuario", None)
        tareas.add_task(analizar_en_segundo_plano, sid, quien.correo if quien else "anonimo")
        return JSONResponse(status_code=202, content={"estado": "analizando"})

    @r.post("/expedientes/{sid}/documentos/aceptar-verificados")
    async def aceptar_verificados(sid: str):
        carpeta, m = _sesion(sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        docs = _documentos(carpeta, m, _vigente(documentos_de(carpeta) or {}))
        for doc in docs:
            if doc.estado == "propuesto" and not doc.veredicto \
                    and doc.destino in docs_tramite.DESTINOS:
                docs_tramite.decidir(doc, doc.destino)
        _guardar_documentos(carpeta, docs)
        return _estado(carpeta, m)

    @r.post("/expedientes/{sid}/documentos/{doc_id}/decision")
    async def decidir_destino(sid: str, doc_id: str, cuerpo: DecisionIn):
        carpeta, m = _sesion(sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        if cuerpo.destino not in docs_tramite.DESTINOS:
            return JSONResponse(status_code=422, content={
                "error": f"«{cuerpo.destino[:40]}» no es un destino"})
        docs = _documentos(carpeta, m, _vigente(documentos_de(carpeta) or {}))
        doc = next((x for x in docs if x.id == doc_id), None)
        if doc is None:
            return JSONResponse(status_code=404, content={"error": "documento no encontrado"})
        docs_tramite.decidir(doc, cuerpo.destino, cuerpo.motivo)
        _guardar_documentos(carpeta, docs)
        return _estado(carpeta, m)

    @r.get("/expedientes/{sid}/documentos/descarga")
    async def descargar(sid: str):
        carpeta, m = _sesion(sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        docs = _documentos(carpeta, m, _vigente(documentos_de(carpeta) or {})) \
            if _leer(carpeta, "as_is").strip() else []
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", m.tramite.nombre)[:60].strip("-") or "tramite"
        return Response(
            a_html(m.tramite.nombre, docs_tramite.resumen(docs, m), docs),
            media_type="text/html; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="Documentos-{base}.html"'})

    return r
