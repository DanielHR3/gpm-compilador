"""`GET /api/v1/expedientes?ruts_id=…`: estado del expediente para Simplifica.

Solo lectura, con un token de servicio (spec 2026-11-06-api-de-estado-para-simplifica):

- El token sale de `GPMC_TOKEN_SERVICIO` y se lee en cada petición, así se puede
  rotar sin reiniciar. Sin la variable la ruta no existe (404).
- Solo por la cabecera `Authorization: Bearer …`, nunca en la URL. Se compara en
  tiempo constante y abre únicamente esta ruta: no crea sesión ni es una persona.
- Ausente, sin `Bearer` o distinto: siempre el mismo 401, sin pistas.
- La respuesta es la de `estado.consultar`: sin datos del ciudadano.

El middleware de `acceso.py` exceptúa esta ruta de su 401 por falta de sesión;
la valida este manejador y él marca `request.state.servicio` para la auditoría.
"""

import hmac
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gpmc.web import estado

NO_ENCONTRADO = {"error": "no encontrado"}
NO_AUTORIZADO = {"error": "no autorizado"}


def _token_esperado(entorno: Optional[dict]) -> str:
    e = entorno if entorno is not None else os.environ
    return (e.get("GPMC_TOKEN_SERVICIO") or "").strip()


def _token_recibido(request: Request) -> str:
    cabecera = request.headers.get("authorization") or ""
    esquema, _, valor = cabecera.partition(" ")
    if esquema.lower() != "bearer":
        return ""
    return valor.strip()


def crear_router_estado(raiz: Path, entorno: Optional[dict] = None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")

    @r.get("/expedientes")
    async def estado_de_expedientes(request: Request):
        esperado = _token_esperado(entorno)
        if not esperado:
            return JSONResponse(status_code=404, content=NO_ENCONTRADO)
        recibido = _token_recibido(request)
        if not recibido or not hmac.compare_digest(recibido.encode("utf-8"), esperado.encode("utf-8")):
            return JSONResponse(status_code=401, content=NO_AUTORIZADO)
        request.state.servicio = True
        ruts_id = request.query_params.get("ruts_id")
        if ruts_id is None or not estado.RUTS_VALIDO.match(ruts_id):
            return JSONResponse(status_code=422, content={
                "error": "ruts_id debe ser alfanumérico de 1 a 20 caracteres"})
        return {"expedientes": estado.consultar(raiz, ruts_id)}

    return r
