"""Fase 3 del asistente: TO-BE y Diccionario propuestos desde el AS-IS.

Router aparte de `api.py` por tamano, con el mismo prefijo `/api/v1`. Importa
de `gpmc.web.api` (helpers de modulo) y de `gpmc.web.sesiones`; nunca de
`gpmc.web.app`, que es quien lo incluye.

La regla que gobierna este archivo: `agentes/` genera y la API persiste. Un
borrador entra a los insumos de la sesion SOLO en `/decision` (aceptada o
corregida) o en `/subir`; y cuando los dos documentos estan resueltos se corre
el extractor de siempre.
"""
import logging
import secrets
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpmc.agentes.fase3 import Documento, Generados, generar, puede_generar
from gpmc.agentes.proveedor import NingunProveedor
from gpmc.extractores import metadatos as ext_meta
from gpmc.web.api import a_texto
from gpmc.web.sesiones import (
    CARPETA_ADJUNTOS, INSUMOS, _MAX_SUBIDA, _purgar_sesiones, carpeta_de,
    escribir_generados, generados_de, nombre_seguro,
)

log = logging.getLogger("gpmc.web.api_fase3")

CLAVE_INSUMO = {"diccionario": "diccionario", "tobe": "to_be"}   # documento -> INSUMOS


class GeneradosOut(BaseModel):
    estado: str
    motivo: Optional[str] = None
    nombre: Optional[str] = None
    diccionario: Optional[Documento] = None
    tobe: Optional[Documento] = None


def crear_router_fase3(raiz: Path, proveedor, entorno: Optional[dict] = None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")
    _hay_ia = not isinstance(proveedor, NingunProveedor)

    def _motivo_para_no_generar() -> Optional[str]:
        if not _hay_ia:
            return "No hay un proveedor de IA configurado en el servidor."
        return puede_generar(entorno)

    def generar_en_segundo_plano(sid: str) -> None:
        """Corre tras responder 202. `generar` nunca propaga; aqui solo se
        persiste lo que devuelva."""
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return
        as_is = (carpeta / INSUMOS["as_is"]).read_text(encoding="utf-8", errors="replace")
        g = generar(as_is, proveedor, raiz, sid)
        log.info("fase3 sid=%s estado=%s", sid, g.estado)
        escribir_generados(carpeta, g.model_dump(mode="json"))

    @r.post("/expedientes/proponer")
    async def proponer_expediente(
        tareas: BackgroundTasks,
        as_is: UploadFile = File(None),
        adjuntos: List[UploadFile] = File(None),
    ):
        if as_is is None or not as_is.filename:
            return JSONResponse(status_code=422, content={"error": "hace falta el Análisis AS-IS"})
        _purgar_sesiones(raiz)
        sid = secrets.token_hex(8)
        carpeta = raiz / sid
        carpeta.mkdir(parents=True, exist_ok=True)
        datos = await as_is.read(_MAX_SUBIDA + 1)
        if len(datos) > _MAX_SUBIDA:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=413, content={
                "error": "archivo demasiado grande", "archivos": [as_is.filename],
                "limite_mb": _MAX_SUBIDA // (1024 * 1024)})
        try:
            texto = a_texto(as_is.filename, datos)
        except ValueError as e:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={
                "error": "no se pudo leer el documento", "archivos": [f"{as_is.filename}: {e}"]})
        (carpeta / INSUMOS["as_is"]).write_bytes(texto)
        for adjunto in (adjuntos or []):
            if adjunto is None or not adjunto.filename:
                continue
            d = await adjunto.read(_MAX_SUBIDA + 1)
            if not d or len(d) > _MAX_SUBIDA:
                continue
            destino = carpeta / CARPETA_ADJUNTOS
            destino.mkdir(parents=True, exist_ok=True)
            (destino / nombre_seguro(adjunto.filename)).write_bytes(d)

        tramite = ext_meta.extraer(texto.decode("utf-8", errors="replace")).tramite
        nombre = tramite.nombre if tramite and tramite.nombre != "[por confirmar]" else None
        motivo = _motivo_para_no_generar()
        if motivo:
            escribir_generados(carpeta, Generados(estado="sin_licencia", motivo=motivo,
                                                  nombre=nombre).model_dump(mode="json"))
            log.info("fase3 sid=%s sin_licencia", sid)
            return JSONResponse(status_code=200, content={"sid": sid, "estado": "sin_licencia"})
        escribir_generados(carpeta, Generados(estado="generando", nombre=nombre).model_dump(mode="json"))
        tareas.add_task(generar_en_segundo_plano, sid)
        return JSONResponse(status_code=202, content={"sid": sid, "estado": "generando"})

    @r.get("/expedientes/{sid}/generados", response_model=GeneradosOut)
    async def leer_generados(sid: str):
        carpeta = carpeta_de(raiz, sid)
        d = generados_de(carpeta) if carpeta else None
        if d is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        return GeneradosOut(**d)

    return r
