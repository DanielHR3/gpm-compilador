"""API de la comparativa de antes y despues: `/api/v1/expedientes/{sid}/comparativa`.

Cascara delgada: lee los insumos de la sesion, llama a `comparativa.armar` y
responde. Importa de `gpmc.web.sesiones`, nunca de `gpmc.web.app`.
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from gpmc.comparativa.armar import METRICAS, Comparativa, a_dict, comparar, no_disponible
from gpmc.comparativa.documento import a_html
from gpmc.extractores import as_is as ext_as_is
from gpmc.extractores import rediseno as ext_rediseno
from gpmc.web.sesiones import (
    INSUMOS,
    carpeta_de,
    comparativa_de,
    escribir_comparativa,
    manifiesto_de,
)

_CLAVES = {k for k, _ in METRICAS}


class Declaracion(BaseModel):
    clave: str
    antes: str = Field(default="", max_length=80)
    despues: str = Field(default="", max_length=80)


def _leer(carpeta: Path, insumo: str) -> str:
    ruta = carpeta / INSUMOS[insumo]
    if not ruta.is_file():
        return ""
    return ruta.read_text(encoding="utf-8", errors="replace")


def _armar(raiz: Path, sid: str) -> Tuple[Optional[Comparativa], Optional[JSONResponse]]:
    carpeta = carpeta_de(raiz, sid)
    m = manifiesto_de(raiz, sid)
    if carpeta is None or m is None:
        return None, JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
    as_is = _leer(carpeta, "as_is")
    if not as_is.strip():
        return no_disponible(
            "No se cargó el Análisis AS-IS en este expediente: sin el antes no hay "
            "comparativa. Vuelve a cargar el expediente con su AS-IS."), None
    declaradas = comparativa_de(carpeta).get("declaradas")
    return comparar(ext_as_is.extraer(as_is), ext_rediseno.extraer(_leer(carpeta, "to_be")),
                    m, declaradas if isinstance(declaradas, dict) else None), None


def crear_router_comparativa(raiz: Path) -> APIRouter:
    r = APIRouter(prefix="/api/v1")

    @r.get("/expedientes/{sid}/comparativa")
    async def leer_comparativa(sid: str):
        c, error = _armar(raiz, sid)
        return error if error is not None else a_dict(c)

    @r.post("/expedientes/{sid}/comparativa/declarar")
    async def declarar(sid: str, cuerpo: Declaracion):
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None or manifiesto_de(raiz, sid) is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        if cuerpo.clave not in _CLAVES:
            return JSONResponse(status_code=422, content={
                "error": f"«{cuerpo.clave}» no es una métrica de la comparativa"})
        d = comparativa_de(carpeta)
        declaradas = d.get("declaradas")
        if not isinstance(declaradas, dict):
            declaradas = {}
        declaradas[cuerpo.clave] = {
            "antes": cuerpo.antes.strip(),
            "despues": cuerpo.despues.strip(),
            "cuando": datetime.now(timezone.utc).isoformat(),
        }
        d["declaradas"] = declaradas
        escribir_comparativa(carpeta, d)
        c, error = _armar(raiz, sid)
        return error if error is not None else a_dict(c)

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
