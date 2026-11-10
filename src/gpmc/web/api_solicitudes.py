"""«Enviar al Compilador» desde Simplifica y la campanita de la SPA.

- `POST /api/v1/solicitudes`: Simplifica, con su token de envío (`GPMC_TOKEN_ENVIO`, distinto del de lectura).
  Sin la variable la ruta no existe (404); token ausente, sin `Bearer` o distinto: el mismo 401.
- `GET /api/v1/solicitudes`, `POST …/{ruts_id}/vista` y `GET …/{ruts_id}/as-is`: personas con sesión
  (el middleware de acceso.py las protege como cualquier `/api/`).
Spec: docs/superpowers/specs/2026-11-10-solicitudes-desde-simplifica-design.md
"""

import hmac
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from gpmc.web import solicitudes
from gpmc.web.estado import RUTS_VALIDO

NO_ENCONTRADO = {"error": "no encontrado"}
NO_AUTORIZADO = {"error": "no autorizado"}


def _token_de(request: Request) -> str:
    esquema, _, valor = (request.headers.get("authorization") or "").partition(" ")
    return valor.strip() if esquema.lower() == "bearer" else ""


def crear_router_solicitudes(raiz: Path, entorno: Optional[dict] = None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")

    @r.post("/solicitudes")
    async def recibir(request: Request):
        e = entorno if entorno is not None else os.environ
        esperado = (e.get("GPMC_TOKEN_ENVIO") or "").strip()
        if not esperado:
            return JSONResponse(status_code=404, content=NO_ENCONTRADO)
        recibido = _token_de(request)
        if not recibido or not hmac.compare_digest(recibido.encode("utf-8"), esperado.encode("utf-8")):
            return JSONResponse(status_code=401, content=NO_AUTORIZADO)
        try:
            cuerpo = await request.json()
        except ValueError:
            cuerpo = None
        ficha = solicitudes.limpiar(cuerpo)
        if ficha is None:
            return JSONResponse(status_code=422, content={"error": "ficha incompleta o con datos de más"})
        if not solicitudes.registrar(raiz, ficha):
            return JSONResponse(status_code=503, content={"error": "no se pudo guardar la solicitud"})
        request.state.solicitud_recibida = ficha["ruts_id"]
        return JSONResponse(status_code=201, content={"ok": True})

    @r.get("/solicitudes")
    async def listar():
        lista = solicitudes.leer(raiz)
        return {"solicitudes": lista, "nuevas": sum(1 for s in lista if s["nueva"])}

    @r.post("/solicitudes/{ruts_id}/vista")
    async def vista(ruts_id: str):
        if not RUTS_VALIDO.match(ruts_id) or not solicitudes.marcar_vista(raiz, ruts_id):
            return JSONResponse(status_code=404, content=NO_ENCONTRADO)
        return {"ok": True}

    @r.get("/solicitudes/{ruts_id}/as-is")
    async def as_is(ruts_id: str):
        ficha = solicitudes.buscar(raiz, ruts_id) if RUTS_VALIDO.match(ruts_id) else None
        if ficha is None:
            return JSONResponse(status_code=404, content=NO_ENCONTRADO)
        return Response(solicitudes.as_is_inicial(ficha), media_type="text/markdown; charset=utf-8",
                        headers={"content-disposition": 'attachment; filename="Analisis AS-IS.md"'})

    return r
