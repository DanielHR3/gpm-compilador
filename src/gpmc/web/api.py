"""API JSON del asistente web: `/api/v1`.

Cascara delgada, como `app.py`, pero responde JSON en vez de HTML. El handler
de `POST /expedientes` reproduce la logica de `POST /extraer` de `app.py`
(purga, lectura con tope, escritura de insumos y `Vistas.html`,
`extraer_expediente`, y persistencia de `manifiesto.yaml` + `huecos.json`),
solo que devuelve el estado del expediente como JSON.

Este modulo importa de `gpmc.web.sesiones`, nunca de `gpmc.web.app`: es `app.py`
quien incluye este router, con un import local, para no cerrar el ciclo.
"""

import dataclasses
import json
import secrets
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpmc.estimador import estimar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.nucleo.huecos import HuecoOut
from gpmc.nucleo.manifiesto import guardar
from gpmc.simulador.analisis import analizar
from gpmc.web.sesiones import (
    ARCHIVO_VISTAS,
    INSUMOS,
    _MAX_SUBIDA,
    _purgar_sesiones,
    carpeta_de,
    huecos_vivos,
    manifiesto_de,
)


class EstadoExpediente(BaseModel):
    """Cuerpo de las respuestas 200/201 de `/api/v1/expedientes`."""

    sid: str
    manifiesto: dict
    huecos: List[HuecoOut]
    estimacion: dict
    problemas: List[str]
    tiene_vistas: bool


def _estado(sid: str, carpeta: Path, manifiesto) -> EstadoExpediente:
    return EstadoExpediente(
        sid=sid,
        manifiesto=manifiesto.model_dump(mode="json"),
        huecos=[HuecoOut.desde(h) for h in huecos_vivos(carpeta)],
        estimacion=dataclasses.asdict(estimar(manifiesto)),
        problemas=analizar(manifiesto).problemas,
        tiene_vistas=(carpeta / ARCHIVO_VISTAS).exists(),
    )


def crear_router(raiz: Path) -> APIRouter:
    r = APIRouter(prefix="/api/v1")

    @r.post("/expedientes", status_code=201, response_model=EstadoExpediente)
    async def crear_expediente(
        as_is: UploadFile = File(None),
        to_be: UploadFile = File(None),
        diccionario: UploadFile = File(...),
        vistas: UploadFile = File(None),
    ):
        _purgar_sesiones(raiz)
        sid = secrets.token_hex(8)
        carpeta = raiz / sid
        carpeta.mkdir(parents=True, exist_ok=True)

        grandes = []  # type: List[str]

        async def _leer(archivo):
            # type: (UploadFile) -> Optional[bytes]
            datos = await archivo.read(_MAX_SUBIDA + 1)
            if len(datos) > _MAX_SUBIDA:
                grandes.append(archivo.filename or "sin nombre")
                return None
            return datos

        for clave, archivo in {"as_is": as_is, "to_be": to_be,
                               "diccionario": diccionario}.items():
            if archivo is None:
                continue
            contenido = await _leer(archivo)
            if contenido:
                (carpeta / INSUMOS[clave]).write_bytes(contenido)

        # El HTML de vistas es referencia visual: se persiste para consulta pero
        # no alimenta al extractor.
        if vistas is not None:
            contenido_vistas = await _leer(vistas)
            if contenido_vistas:
                (carpeta / ARCHIVO_VISTAS).write_bytes(contenido_vistas)

        if grandes:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=413, content={
                "error": "archivo demasiado grande",
                "archivos": grandes,
                "limite_mb": _MAX_SUBIDA // (1024 * 1024),
            })

        try:
            res = extraer_expediente(carpeta)
        except SinPermiso as exc:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={"error": str(exc)})

        if res.manifiesto is None:
            motivo = (res.huecos[0].mensaje if res.huecos
                      else "no se pudo extraer el manifiesto")
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={"error": motivo})

        guardar(res.manifiesto, carpeta / "manifiesto.yaml")
        # Los Hueco tipados se persisten como JSON para que GET /expedientes/{sid}
        # los reconstruya sin volver a correr el extractor. Mismo formato que
        # POST /extraer.
        (carpeta / "huecos.json").write_text(
            json.dumps(
                [{"nivel": h.nivel, "codigo": h.codigo, "ubicacion": h.ubicacion,
                  "mensaje": h.mensaje, "propuesta": h.propuesta}
                 for h in res.huecos],
                ensure_ascii=False),
            encoding="utf-8",
        )
        return _estado(sid, carpeta, res.manifiesto)

    @r.get("/expedientes/{sid}", response_model=EstadoExpediente)
    async def leer_expediente(sid: str):
        carpeta = carpeta_de(raiz, sid)
        m = manifiesto_de(raiz, sid)
        if carpeta is None or m is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        return _estado(sid, carpeta, m)

    return r
