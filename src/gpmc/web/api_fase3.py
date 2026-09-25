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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, File, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpmc.agentes.bitacora import Interaccion, registrar
from gpmc.agentes.fase3 import (Documento, Generados, extraer_borradores, generar,
                                modo_pruebas, puede_generar, vista_de)
from gpmc.agentes.proveedor import NingunProveedor
from gpmc.extractores import metadatos as ext_meta
from gpmc.extractores.expediente import SinPermiso
from gpmc.web.api import a_texto, extraer_y_persistir, lanzar_propuestas_dic08
from gpmc.web.sesiones import (
    CARPETA_ADJUNTOS, INSUMOS, _MAX_SUBIDA, _purgar_sesiones, carpeta_de,
    escribir_generados, generados_de, nombre_seguro,
)

log = logging.getLogger("gpmc.web.api_fase3")

CLAVE_INSUMO = {"diccionario": "diccionario", "tobe": "to_be"}   # documento -> INSUMOS


# Hasta cuatro llamadas con tres intentos de 60 s caben de sobra en 20
# minutos. Un `generando` mas viejo es una generacion que ya no corre: el
# servicio se reinicio a media tarea (launchd lo reinicia en cada despliegue)
# o el hilo murio antes de escribir. Sin esto la sesion quedaba atorada para
# siempre y sin zonas de carga.
MAX_GENERANDO = timedelta(minutes=20)

MOTIVO_INTERRUMPIDA = ("La generación se interrumpió (el servidor se reinició o falló a "
                       "media tarea). Sube el Diccionario y el TO-BE que tengas.")


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def anotador_de_pasos(carpeta: Path):
    """La funcion `avisar` que recibe `generar`: cada paso se agrega a
    `generados.json` en cuanto ocurre, sin pisar lo demas, para que la SPA lo
    vea en su siguiente consulta. Lee-modifica-escribe atomico: el hilo de
    fondo es el unico que escribe mientras el estado es `generando`."""
    def avisar(mensaje: str) -> None:
        d = generados_de(carpeta) or {}
        d["pasos"] = list(d.get("pasos") or []) + [{"t": _ahora(), "mensaje": mensaje}]
        escribir_generados(carpeta, d)
    return avisar


def _vigente(d: dict) -> dict:
    """`generados.json` tal como debe verse ahora: un `generando` viejo se
    lee como `error`. Sin `iniciado` (sesiones de antes) se deja como esta."""
    if d.get("estado") != "generando" or not d.get("iniciado"):
        return d
    try:
        iniciado = datetime.fromisoformat(d["iniciado"])
    except ValueError:
        return d
    if datetime.now(timezone.utc) - iniciado <= MAX_GENERANDO:
        return d
    return {**d, "estado": "error", "motivo": MOTIVO_INTERRUMPIDA}


def _con_vista(carpeta: Path, d: dict) -> dict:
    """Las sesiones de antes de la vista por pantallas (2026-09-24) no traen
    `vista`, y la SPA decia «no pudo leer pantallas» aunque si se podia. Se
    calcula una vez, con el mismo extractor, y se guarda."""
    doc = d.get("diccionario")
    if not doc or "vista" in doc:
        return d
    as_is = (carpeta / INSUMOS["as_is"]).read_text(encoding="utf-8", errors="replace") \
        if (carpeta / INSUMOS["as_is"]).exists() else ""
    tobe = (d.get("tobe") or {}).get("texto", "")
    m, _ = extraer_borradores(as_is, doc.get("texto", ""), tobe)
    doc["vista"] = vista_de(m)
    escribir_generados(carpeta, d)
    return d


def generados_vigentes(carpeta: Optional[Path]) -> Optional[dict]:
    d = generados_de(carpeta) if carpeta else None
    return _vigente(_con_vista(carpeta, d)) if d is not None else None


class GeneradosOut(BaseModel):
    estado: str
    motivo: Optional[str] = None
    nombre: Optional[str] = None
    diccionario: Optional[Documento] = None
    tobe: Optional[Documento] = None
    # Que documento ya tiene archivo en la sesion: con eso la SPA abre en el
    # paso correcto al recargar (`declinada` sola no dice si ya se subio el propio).
    insumos: dict = {}
    # Lo que el agente fue haciendo: [{t, mensaje}], en orden.
    pasos: list = []


class DecisionDocumentoIn(BaseModel):
    decision: Literal["aceptada", "corregida", "declinada"]
    texto_final: Optional[str] = None


def crear_router_fase3(raiz: Path, proveedor, entorno: Optional[dict] = None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")
    _hay_ia = not isinstance(proveedor, NingunProveedor)

    def _motivo_para_no_generar() -> Optional[str]:
        if not _hay_ia:
            return "No hay un proveedor de IA configurado en el servidor."
        return puede_generar(entorno)

    def generar_en_segundo_plano(sid: str, usuario: str = "anonimo") -> None:
        """Corre tras responder 202. `generar` nunca propaga; aqui solo se
        persiste lo que devuelva."""
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return
        as_is = (carpeta / INSUMOS["as_is"]).read_text(encoding="utf-8", errors="replace")
        g = generar(as_is, proveedor, raiz, sid, avisar=anotador_de_pasos(carpeta), usuario=usuario)
        log.info("fase3 sid=%s estado=%s", sid, g.estado)
        d = g.model_dump(mode="json")
        # Los pasos ya estan en disco con su hora real; solo si faltaran (una
        # sesion vieja sin `pasos`) se reconstruyen con la hora de ahora.
        previos = (generados_de(carpeta) or {}).get("pasos") or []
        d["pasos"] = previos if [x["mensaje"] for x in previos] == g.pasos else \
            [{"t": _ahora(), "mensaje": m} for m in g.pasos]
        escribir_generados(carpeta, d)

    @r.post("/expedientes/proponer")
    async def proponer_expediente(
        request: Request,
        tareas: BackgroundTasks,
        as_is: UploadFile = File(None),
        adjuntos: List[UploadFile] = File(None),
    ):
        if as_is is None or not as_is.filename:
            return JSONResponse(status_code=422, content={"error": "hace falta el Análisis AS-IS"})
        _purgar_sesiones(raiz)
        sid = secrets.token_hex(8)
        request.state.sid = sid          # la auditoria lo lee al salir
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
        escribir_generados(carpeta, {**Generados(estado="generando", nombre=nombre).model_dump(mode="json"),
                                      "iniciado": _ahora()})
        quien = getattr(request.state, "usuario", None)
        tareas.add_task(generar_en_segundo_plano, sid, quien.correo if quien else "anonimo")
        return JSONResponse(status_code=202, content={"sid": sid, "estado": "generando"})

    def _resuelto(carpeta: Path, documento: str) -> bool:
        """Un documento esta resuelto cuando su insumo existe en la sesion: lo
        escriben `aceptada`, `corregida` o `/subir`; `declinada` sola no."""
        return (carpeta / INSUMOS[CLAVE_INSUMO[documento]]).exists()

    def _salida(carpeta: Path, d: dict) -> GeneradosOut:
        return GeneradosOut(**{**d, "insumos": {doc: _resuelto(carpeta, doc) for doc in CLAVE_INSUMO}})

    @r.get("/capacidades")
    async def leer_capacidades():
        """Si este servidor puede proponer desde el AS-IS. La SPA lo pregunta
        antes de que nadie suba nada: enterarse del candado despues de subir
        el AS-IS era la peor experiencia posible."""
        motivo = _motivo_para_no_generar()
        # `pruebas`: el candado esta abierto sin licencia; la SPA lo avisa.
        return {"proponer": motivo is None, "motivo": motivo,
                "pruebas": motivo is None and modo_pruebas(entorno)}

    @r.get("/expedientes/{sid}/generados", response_model=GeneradosOut)
    async def leer_generados(sid: str):
        carpeta = carpeta_de(raiz, sid)
        d = generados_vigentes(carpeta)
        if d is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        return _salida(carpeta, d)

    def _anotar_decision(sid: str, documento: str, decision: str, version: str) -> None:
        registrar(raiz, Interaccion(
            sid=sid, proveedor=proveedor.nombre, modelo="", version_prompt=version,
            solicitud={"decision": decision}, instruccion_hash="", estado="decision",
            documento=documento))

    def _si_ambos_resueltos(sid: str, carpeta: Path, d: dict, tareas: BackgroundTasks):
        if not (_resuelto(carpeta, "diccionario") and _resuelto(carpeta, "tobe")):
            return _salida(carpeta, d)
        try:
            est, motivo = extraer_y_persistir(raiz, sid, carpeta)
        except SinPermiso as exc:
            return JSONResponse(status_code=422, content={"error": str(exc)})
        if est is None:
            # La sesion queda intacta: se puede subir otro archivo encima.
            return JSONResponse(status_code=422, content={"error": motivo})
        # Mismo asistente que una sesion subida con Diccionario: con DIC-08,
        # arrancan las propuestas de visibilidad (spec, Parte 1, paso 6).
        return lanzar_propuestas_dic08(raiz, proveedor, sid, carpeta, tareas, est)

    def _documento_valido(documento: str):
        if documento not in CLAVE_INSUMO:
            return JSONResponse(status_code=422, content={"error": "documento debe ser diccionario o tobe"})
        return None

    @r.post("/expedientes/{sid}/generados/{documento}/decision")
    async def decidir_documento(sid: str, documento: str, cuerpo: DecisionDocumentoIn,
                                tareas: BackgroundTasks):
        invalido = _documento_valido(documento)
        if invalido is not None:
            return invalido
        carpeta = carpeta_de(raiz, sid)
        d = generados_vigentes(carpeta)
        if d is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        if d["estado"] != "listo" or d.get(documento) is None:
            return JSONResponse(status_code=409, content={"error": "no hay propuesta que decidir"})
        doc = d[documento]
        if doc["decision"] != "pendiente":
            return JSONResponse(status_code=409, content={"error": "el documento ya tenía decisión"})
        if cuerpo.decision == "corregida" and not (cuerpo.texto_final or "").strip():
            return JSONResponse(status_code=422, content={"error": "corregida exige texto_final"})
        if cuerpo.decision != "declinada":
            texto = cuerpo.texto_final if cuerpo.decision == "corregida" else doc["texto"]
            (carpeta / INSUMOS[CLAVE_INSUMO[documento]]).write_text(texto, encoding="utf-8")
        doc["decision"] = cuerpo.decision
        escribir_generados(carpeta, d)
        _anotar_decision(sid, documento, cuerpo.decision, doc["version_prompt"])
        log.info("fase3 sid=%s %s=%s", sid, documento, cuerpo.decision)
        return _si_ambos_resueltos(sid, carpeta, d, tareas)

    @r.post("/expedientes/{sid}/generados/{documento}/subir")
    async def subir_documento(sid: str, documento: str, tareas: BackgroundTasks,
                              archivo: UploadFile = File(...)):
        """Para el declinado (o para una sesion en error / sin_licencia): el
        archivo propio entra como insumo y aplica la misma regla de «ambos
        resueltos». Vale mientras no haya manifiesto: asi un 422 del extractor
        se corrige subiendo otro archivo encima."""
        invalido = _documento_valido(documento)
        if invalido is not None:
            return invalido
        carpeta = carpeta_de(raiz, sid)
        d = generados_vigentes(carpeta)
        if d is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        if (carpeta / "manifiesto.yaml").exists():
            return JSONResponse(status_code=409, content={"error": "el expediente ya se extrajo"})
        datos = await archivo.read(_MAX_SUBIDA + 1)
        if len(datos) > _MAX_SUBIDA:
            return JSONResponse(status_code=413, content={
                "error": "archivo demasiado grande", "archivos": [archivo.filename],
                "limite_mb": _MAX_SUBIDA // (1024 * 1024)})
        try:
            texto = a_texto(archivo.filename or "", datos)
        except ValueError as e:
            return JSONResponse(status_code=422, content={
                "error": "no se pudo leer el documento", "archivos": [f"{archivo.filename}: {e}"]})
        (carpeta / INSUMOS[CLAVE_INSUMO[documento]]).write_bytes(texto)
        # Se relee despues del `await`: una decision sobre el otro documento
        # pudo llegar mientras se recibia el archivo, y escribir el `d` de
        # antes la revertia a `pendiente`.
        d = generados_vigentes(carpeta) or d
        # Subir el propio sobre una propuesta —sin decidir o ya aceptada— es
        # declinarla: el registro de la Licencia AI no puede decir que se uso el
        # texto del modelo cuando el que quedo es el de una persona.
        if d.get(documento) is not None and d[documento]["decision"] != "declinada":
            d[documento]["decision"] = "declinada"
            escribir_generados(carpeta, d)
            _anotar_decision(sid, documento, "declinada", d[documento]["version_prompt"])
        log.info("fase3 sid=%s %s subido", sid, documento)
        return _si_ambos_resueltos(sid, carpeta, d, tareas)

    return r
