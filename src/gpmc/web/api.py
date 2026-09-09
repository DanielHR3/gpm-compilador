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
import re
import secrets
import shutil
from pathlib import Path
from typing import List, Literal, Optional, Tuple

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from gpmc.compilador.a_gpm import compilar
from gpmc.estimador import estimar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.nucleo.formato import serializar
from gpmc.nucleo.huecos import HuecoOut, bloquean
from gpmc.nucleo.manifiesto import guardar
from gpmc.simulador.analisis import analizar
from gpmc.web.sesiones import (
    ARCHIVO_VISTAS,
    INSUMOS,
    _MAX_SUBIDA,
    _purgar_sesiones,
    carpeta_de,
    escribir_reconocidos,
    huecos_vivos,
    manifiesto_de,
    reconocidos_de,
)


class EstadoExpediente(BaseModel):
    """Cuerpo de las respuestas 200/201 de `/api/v1/expedientes`."""

    sid: str
    manifiesto: dict
    huecos: List[HuecoOut]
    estimacion: dict
    problemas: List[str]
    tiene_vistas: bool


# Mismo mapeo tipo->codigo que usa el HTML `POST /resolver` para limpiar
# `huecos.json`: cada resolucion tacha el hueco `(codigo, ubicacion)`.
_TIPO_A_CODIGO = {
    "mmd03": "MMD-03",
    "meta01": "META-01",
    "meta02": "META-02",
    "api03": "API-03",
}


class ResolucionIn(BaseModel):
    """Una resolucion de hueco: donde aplicarla y con que valor."""

    tipo: Literal["mmd03", "meta01", "meta02", "api03"]
    ubicacion: str
    valor: str


class ResolverIn(BaseModel):
    """Cuerpo de `POST /api/v1/expedientes/{sid}/resolver`."""

    resoluciones: List[ResolucionIn]


class ReconocerIn(BaseModel):
    """Cuerpo de `POST /api/v1/expedientes/{sid}/reconocer`."""

    codigo: str
    ubicacion: str


class EstadoResolver(BaseModel):
    """Respuesta 200 de `/resolver`: manifiesto ya guardado + huecos vivos."""

    manifiesto: dict
    huecos: List[HuecoOut]


class EstadoReconocer(BaseModel):
    """Respuesta 200 de `/reconocer`: huecos vivos + los `(codigo, ubicacion)`
    marcados como "se configuran a mano en la plataforma"."""

    huecos: List[HuecoOut]
    reconocidos: List[List[str]]


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

    @r.post("/expedientes/{sid}/resolver", response_model=EstadoResolver)
    async def resolver_expediente(sid: str, cuerpo: ResolverIn):
        """Porta el bucle de `POST /resolver` de `app.py` a un cuerpo JSON.

        Cada `{tipo, ubicacion, valor}` toca el manifiesto en un sitio; tras
        aplicarlas se guarda `manifiesto.yaml` y se tachan de `huecos.json` los
        `(codigo, ubicacion)` resueltos. Devuelve el estado nuevo.
        """
        carpeta = carpeta_de(raiz, sid)
        m = manifiesto_de(raiz, sid)
        if carpeta is None or m is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})

        # `mmd03`/`api03` tachan el hueco por su ubicacion real (id de tarea /
        # nombre de campo, como `tarea_id` / `campo_nombre` en `app.py`).
        # `meta01`/`meta02` siempre se emiten con ubicacion "metadatos": el
        # handler HTML de referencia la fija a mano (`app.py` lineas 245, 250),
        # asi que aqui se ignora la `ubicacion` del cliente para la purga.
        resueltos = []  # type: List[Tuple[str, str]]
        for res in cuerpo.resoluciones:
            if not res.valor:
                continue
            codigo = _TIPO_A_CODIGO[res.tipo]
            if res.tipo == "mmd03":
                for t in m.flujo.tareas:
                    if t.id == res.ubicacion:
                        t.actor = res.valor
                        resueltos.append((codigo, res.ubicacion))
            elif res.tipo == "meta01":
                m.tramite.ruts.tiempo_entrega = res.valor
                resueltos.append((codigo, "metadatos"))
            elif res.tipo == "meta02":
                m.tramite.dependencia = res.valor
                resueltos.append((codigo, "metadatos"))
            elif res.tipo == "api03":
                campo = m.campo_por_nombre(res.ubicacion)
                if campo:
                    campo.dependencia_campo = res.valor
                    resueltos.append((codigo, res.ubicacion))

        guardar(m, carpeta / "manifiesto.yaml")

        ruta_huecos = carpeta / "huecos.json"
        if ruta_huecos.exists():
            datos = json.loads(ruta_huecos.read_text(encoding="utf-8"))
            datos = [h for h in datos
                     if (h.get("codigo"), h.get("ubicacion")) not in resueltos]
            ruta_huecos.write_text(json.dumps(datos, ensure_ascii=False),
                                   encoding="utf-8")

        return EstadoResolver(
            manifiesto=m.model_dump(mode="json"),
            huecos=[HuecoOut.desde(h) for h in huecos_vivos(carpeta)],
        )

    @r.post("/expedientes/{sid}/reconocer", response_model=EstadoReconocer)
    async def reconocer_expediente(sid: str, cuerpo: ReconocerIn):
        """Marca un hueco `falta_dato` como "se configura a mano en la
        plataforma": no toca el manifiesto, solo deja constancia."""
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        rec = reconocidos_de(carpeta)
        rec.add((cuerpo.codigo, cuerpo.ubicacion))
        escribir_reconocidos(carpeta, rec)
        return EstadoReconocer(
            huecos=[HuecoOut.desde(h) for h in huecos_vivos(carpeta)],
            reconocidos=[list(t) for t in sorted(rec)],
        )

    @r.get("/expedientes/{sid}/gpm")
    async def descargar_gpm(sid: str, modo: str = "produccion"):
        """Porta `GET /descargar/{sid}/gpm` (y `gpm-pruebas`) de `app.py`.

        Puerta del linter: no se entrega el .gpm mientras quede un hueco
        bloqueante, o uno de `falta_dato` que nadie resolvio (por `/resolver`)
        ni reconocio ("lo configuro a mano"). Se mira el estado vivo de la
        sesion. `modo="pruebas"` compila con `modo_pruebas=True`; a `409` se le
        responde JSON `{"bloqueantes": [...]}` en vez del `text/plain` del HTML.
        """
        m = manifiesto_de(raiz, sid)
        if m is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        carpeta = carpeta_de(raiz, sid)
        faltan = bloquean(huecos_vivos(carpeta), reconocidos_de(carpeta))
        if faltan:
            return JSONResponse(status_code=409, content={"bloqueantes": [
                {"codigo": h.codigo, "ubicacion": h.ubicacion,
                 "mensaje": h.mensaje}
                for h in faltan
            ]})
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", m.tramite.nombre)[:60] or "tramite"
        nombre = f"{base}-test-ui.gpm" if modo == "pruebas" else f"{base}.gpm"
        return Response(
            serializar(compilar(m, modo_pruebas=(modo == "pruebas"))),
            media_type="application/octet-stream",
            headers={"content-disposition": f'attachment; filename="{nombre}"'},
        )

    @r.get("/expedientes/{sid}/manifiesto")
    async def descargar_manifiesto(sid: str):
        """Sirve `manifiesto.yaml` inline (la SPA lo consume por `fetch`).

        Porta `GET /descargar/{sid}/manifiesto` de `app.py`, con `text/yaml`
        (no `application/x-yaml`) y sin `Content-Disposition`.
        """
        m = manifiesto_de(raiz, sid)
        if m is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        return Response(
            (carpeta_de(raiz, sid) / "manifiesto.yaml").read_text(encoding="utf-8"),
            media_type="text/yaml",
        )

    return r
