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
import logging
import re
import secrets
import shutil
from pathlib import Path
from typing import Annotated, List, Literal, Optional, Tuple, Union

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from gpmc.compilador.a_gpm import compilar
from gpmc.estimador import estimar
from gpmc.extractores.documentos import vale_para
from gpmc.extractores.expediente import (
    SinPermiso,
    _mapear_nodos_a_pantallas,
    extraer_expediente,
    ramas_de_compuerta,
)
from gpmc.nucleo.formato import serializar
from gpmc.nucleo.grupos import OBSERVADOS as GRUPOS_OBSERVADOS
from gpmc.nucleo.huecos import HuecoOut, bloquean
from gpmc.nucleo.manifiesto import Conexion, Condicion, Manifiesto, guardar
from gpmc.simulador.analisis import analizar
from gpmc.web.reensamblado import reensamblar_flujo, rm_de_tobe
from gpmc.agentes import crear_proveedor, proponer_dic08
from gpmc.agentes.proveedor import NingunProveedor

# Identificadores y conteos, NUNCA el contenido de un expediente: este registro
# es texto plano en la maquina que sirve al equipo.
log = logging.getLogger("gpmc.web.api")
from gpmc.extractores.docx import a_markdown
from gpmc.extractores import pdf as ext_pdf
from gpmc.web.clasificador import clasificar
from gpmc.web import tablero
from gpmc.web.sesiones import (
    CARPETA_ADJUNTOS,
    CARPETA_DOCUMENTOS,
    adjuntos_de,
    nombre_seguro,
    ARCHIVO_VISTAS,
    INSUMOS,
    _MAX_SUBIDA,
    _purgar_sesiones,
    carpeta_de,
    compuertas_de,
    escribir_compuertas,
    escribir_huecos,
    escribir_propuestas,
    generados_de,
    escribir_reconocidos,
    huecos_vivos,
    manifiesto_de,
    propuestas_de,
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
    # Documentos de apoyo (diagramas, PDF): se muestran, no se extraen.
    adjuntos: List[dict] = []
    # Los `(codigo, ubicacion)` ya marcados como "se configuran a mano".
    # Sin esto la SPA los pierde de vista al recargar: el servidor los
    # conserva —la puerta del .gpm sigue levantada— pero el wizard vuelve a
    # pintar el hueco como pendiente y el analista cree que perdio su trabajo.
    reconocidos: List[List[str]]
    # True si el generador de IA corrio (o esta corriendo) para esta sesion:
    # la SPA solo consulta /propuestas cuando vale la pena.
    propuestas_pendientes: bool = False


# Mismo mapeo tipo->codigo que usa el HTML `POST /resolver` para limpiar
# `huecos.json`: cada resolucion tacha el hueco `(codigo, ubicacion)`.
_TIPO_A_CODIGO = {
    "mmd03": "MMD-03",
    "meta01": "META-01",
    "meta02": "META-02",
    "meta04": "META-04",
    "api03": "API-03",
    "meta07": "META-07",
    "doc04": "DOC-04",
    "act01": "ACT-01",
}


def _si_o_no(valor: str) -> Optional[bool]:
    """«Sí», «si», «NO»... como booleano; cualquier otra cosa, None."""
    llano = (valor or "").strip().lower().replace("í", "i")
    return {"si": True, "no": False}.get(llano)


def _campos_declarados(m: Manifiesto) -> set:
    """Nombres de todos los campos declarados en el manifiesto (todas las
    pantallas). Usado por las ramas `dic08`, `mmd04campo` y `mmd04rama` de
    `resolver_expediente` para validar que una `Condicion` (o el `campo` de
    `mmd04campo`) no referencie uno inexistente (spec 5.1 / Ruling 5)."""
    return {c.nombre for p in m.pantallas for c in p.campos}


class ResolucionIn(BaseModel):
    """Una resolucion de hueco: donde aplicarla y con que valor."""

    tipo: Literal["mmd03", "meta01", "meta02", "meta04", "api03",
                  "meta07", "doc04", "act01"]
    ubicacion: str
    valor: str


class ResolucionDic08(BaseModel):
    """Resolucion del hueco DIC-08: fija `condicion_visible` en un campo."""

    tipo: Literal["dic08"]
    ubicacion: str
    condicion: Condicion


class ResolucionMmd04Campo(BaseModel):
    """Resolucion del hueco MMD-04: fija el `@@campo` de una compuerta que
    el TO-BE no nombro, y dispara el reensamblado del flujo."""

    tipo: Literal["mmd04campo"]
    ubicacion: str  # id de la compuerta (gate id) en el Mermaid del TO-BE
    campo: str


class RamaResuelta(BaseModel):
    """Una rama de compuerta con la `Condicion` que la persona eligio a mano
    (respaldo cuando `mmd04campo` no basta: ver `ramas_de_compuerta`)."""

    a: str  # id del nodo destino en el Mermaid del TO-BE (de `ramas_de_compuerta`)
    condicion: Condicion


class ResolucionMmd04Rama(BaseModel):
    """Resolucion del hueco MMD-04 por rama: fija una `Condicion` por cada
    arista que sale de la compuerta, en vez de un solo `@@campo`."""

    tipo: Literal["mmd04rama"]
    ubicacion: str  # id de la compuerta (gate id) en el Mermaid del TO-BE
    ramas: List[RamaResuelta]


class ResolverIn(BaseModel):
    """Cuerpo de `POST /api/v1/expedientes/{sid}/resolver`."""

    resoluciones: List[
        Annotated[
            Union[ResolucionIn, ResolucionDic08, ResolucionMmd04Campo, ResolucionMmd04Rama],
            Field(discriminator="tipo"),
        ]
    ]


class ClasificarIn(BaseModel):
    """Los nombres de archivo de una carpeta de expediente, tal como los ve el
    navegador (rutas relativas, `Documentos/Oficio.pdf`)."""
    archivos: List[str] = Field(..., max_length=2000)


class CatalogoOut(BaseModel):
    clave: str
    proveedor: str
    tipo: str                     # catalogo | consulta
    url: str
    sinonimos: List[str] = []     # lo que un Diccionario escribe para activarlo
    campos_respuesta: List[str] = []


class CatalogosOut(BaseModel):
    catalogos: List[CatalogoOut]
    nota: str


class TramiteHistorialOut(BaseModel):
    sid: str
    nombre: str
    dependencia: str
    # ISO 8601 con zona. Sale de la carpeta de sesion: cada resolver/reconocer
    # la toca, asi que es "ultima vez que alguien trabajo en esto".
    modificado: str


class HistorialOut(BaseModel):
    tramites: List[TramiteHistorialOut]


class ConteoOut(BaseModel):
    nombre: str
    tramites: int
    porcentaje: int
    etiqueta: Optional[str] = None


class HuecoTableroOut(BaseModel):
    codigo: str
    tramites: int
    total: int


class ComplejidadOut(BaseModel):
    clave: str
    nombre: str
    dependencia: str
    nivel: str
    metricas: dict


class DependenciaOut(BaseModel):
    nombre: str
    tramites: int


class CatalogoTableroOut(BaseModel):
    clave: str
    proveedor: str = ""
    descripcion: str = ""
    tramites: int


class SemanaOut(BaseModel):
    semana: str
    tramites: int


class IndicadoresOut(BaseModel):
    requisitos_distintos: int
    promedio_campos: float
    promedio_huecos: float
    con_integracion: int


class MatrizOut(BaseModel):
    filas: List[str]
    columnas: List[str]
    celdas: List[List[int]]
    maximo: int = 0


class NivelOut(BaseModel):
    nivel: str
    tramites: int


class TableroOut(BaseModel):
    """Cuentas del tablero de Simplificación. Solo agregados."""
    total_tramites: int
    dependencias: List[DependenciaOut]
    ultimo_registro: Optional[str]
    requisitos: List[ConteoOut]
    campos_compartidos: List[ConteoOut]
    huecos: List[HuecoTableroOut]
    complejidad: List[ComplejidadOut]
    catalogos: List[CatalogoTableroOut]
    actividad: List[SemanaOut]
    indicadores: IndicadoresOut
    matriz_huecos: MatrizOut
    matriz_requisitos: MatrizOut
    niveles: List[NivelOut]
    metricas_max: dict


class ClasificarOut(BaseModel):
    """A que zona del asistente va cada archivo. Solo nombres: el navegador
    sube los bytes despues, ya repartidos, a `POST /expedientes`."""
    as_is: Optional[str] = None
    to_be: Optional[str] = None
    diccionario: Optional[str] = None
    vistas: Optional[str] = None
    adjuntos: List[str] = []
    documentos: List[str] = []
    ignorados: List[str] = []
    avisos: List[str] = []


class PropuestasOut(BaseModel):
    """Estado del generador de IA y las propuestas que vale la pena mostrar:
    aceptables por el filtro determinista y todavia sin decision."""
    estado: str                       # proponiendo | listo | error | sin_proveedor
    motivo: Optional[str] = None
    propuestas: List[dict] = []


class DecisionIn(BaseModel):
    decision: Literal["aceptada", "corregida", "descartada"]
    condicion_final: Optional[Condicion] = None


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
        adjuntos=adjuntos_de(carpeta),
        reconocidos=[list(t) for t in sorted(reconocidos_de(carpeta))],
        propuestas_pendientes=(propuestas_de(carpeta) is not None),
    )


def a_texto(nombre: str, datos: bytes) -> bytes:
    """Un .docx o un PDF se convierte al Markdown que lee el extractor; lo
    demas pasa tal cual. Lanza ValueError si no se puede leer.

    El equipo que construye GPM entrega el Diccionario en Word; antes habia
    que pasarlo a Markdown a mano, tramite por tramite, antes de poder compilar.
    """
    n = (nombre or "").lower()
    if n.endswith(".docx"):
        return a_markdown(datos).encode("utf-8")
    if n.endswith(".pdf"):
        return ext_pdf.a_markdown(datos).encode("utf-8")
    return datos


def extraer_y_persistir(raiz: Path, sid: str, carpeta: Path):
    """Corre el extractor sobre la carpeta de la sesion y persiste lo que
    `GET /expedientes/{sid}` necesita. Devuelve `(EstadoExpediente, None)` o
    `(None, motivo)` si no hubo manifiesto; no borra nada: quien llama decide
    si la sesion sobrevive (en `POST /expedientes` no; en la Fase 3 si, porque
    un insumo se puede volver a subir encima). Propaga `SinPermiso`."""
    res = extraer_expediente(carpeta)
    if res.manifiesto is None:
        # El motivo es el hueco que CORTO la extraccion (INS-03, DIC-00), no el
        # primero de la lista: ese suele ser un metadato sin importancia y
        # decia «no se encontro la dependencia» cuando faltaban las pantallas.
        causa = next((h for h in res.huecos if h.nivel == "bloqueante"),
                     res.huecos[0] if res.huecos else None)
        return None, (causa.mensaje if causa else "no se pudo extraer el manifiesto")
    guardar(res.manifiesto, carpeta / "manifiesto.yaml")
    # Los Hueco tipados se persisten como JSON para que GET /expedientes/{sid}
    # los reconstruya sin volver a correr el extractor.
    escribir_huecos(carpeta, res.huecos)
    log.info("expediente extraido sid=%s pantallas=%d campos=%d huecos=%d bloquean=%d",
             sid, len(res.manifiesto.pantallas),
             sum(len(p.campos) for p in res.manifiesto.pantallas),
             len(res.huecos), len(bloquean(res.huecos)))
    # Registro del tablero: solo agregados, y se hace aqui (al extraer) y
    # no al descargar el .gpm, por decision del usuario del 2026-09-23.
    linea = tablero.resumir(res.manifiesto, res.huecos)
    if linea is None:
        log.info("tablero: sid=%s sin nombre de tramite, no se registra", sid)
    else:
        tablero.registrar(raiz, linea)
    return _estado(sid, carpeta, res.manifiesto), None


def generar_propuestas(raiz: Path, proveedor, sid: str) -> None:
    """Corre en BackgroundTasks tras extraer (POST /expedientes o la Fase 3).
    Nunca deja excepciones sin capturar: un fallo aqui es `estado=error`, no un
    500 y no un bloqueo de la entrega."""
    carpeta = carpeta_de(raiz, sid)
    m = manifiesto_de(raiz, sid)
    if carpeta is None or m is None:
        return
    try:
        props = proponer_dic08(m, huecos_vivos(carpeta), proveedor, raiz, sid)
        log.info("propuestas sid=%s generadas=%d aceptables=%d declinadas=%d",
                 sid, len(props),
                 sum(1 for p in props if p.veredicto == "aceptable"),
                 sum(1 for p in props if p.veredicto == "modelo_declino"))
        escribir_propuestas(carpeta, {
            "estado": "listo", "motivo": None,
            "generadas": datetime.now(timezone.utc).isoformat(),
            "propuestas": [p.model_dump(mode="json") for p in props]})
    except Exception as exc:  # ErrorDeRed, RespuestaInvalida, o lo que sea
        # Con `exc_info` va la traza entera: si el fallo es del proveedor su
        # detalle esta en `bitacora-ia.jsonl`, pero un defecto NUESTRO no
        # dejaba rastro en ningun sitio.
        log.error("propuestas sid=%s fallaron: %s", sid, type(exc).__name__, exc_info=exc)
        escribir_propuestas(carpeta, {
            "estado": "error", "generadas": None, "propuestas": [],
            "motivo": "No se pudieron generar propuestas con IA; puedes "
                      f"resolver a mano. ({type(exc).__name__})"})


def lanzar_propuestas_dic08(raiz: Path, proveedor, sid: str, carpeta: Path,
                            tareas: BackgroundTasks, est: "EstadoExpediente") -> "EstadoExpediente":
    """Si hay proveedor y el expediente trae DIC-08, deja `propuestas.json` en
    `proponiendo`, programa la generacion y devuelve el estado con
    `propuestas_pendientes=True`. Lo usan los dos caminos que extraen —POST
    /expedientes y la Fase 3—, para que el asistente de huecos sea el mismo."""
    if isinstance(proveedor, NingunProveedor) or not any(h.codigo == "DIC-08" for h in est.huecos):
        return est
    escribir_propuestas(carpeta, {"estado": "proponiendo", "motivo": None,
                                  "generadas": None, "propuestas": []})
    tareas.add_task(generar_propuestas, raiz, proveedor, sid)
    return _estado(sid, carpeta, manifiesto_de(raiz, sid))


def crear_router(raiz: Path, proveedor=None) -> APIRouter:
    r = APIRouter(prefix="/api/v1")
    # El proveedor de IA se inyecta (las pruebas pasan ProveedorFalso); sin
    # inyeccion se lee del entorno. Sin configuracion, NingunProveedor: todo lo
    # de abajo se comporta como si el generador no existiera.
    _proveedor = proveedor if proveedor is not None else crear_proveedor()

    @r.get("/historial", response_model=HistorialOut)
    async def listar_historial():
        """Los expedientes que hay en el almacen, para la seccion «Historial».

        Una carpeta de sesion puede guardar un manifiesto de un esquema
        anterior o a medio escribir; `cargar` revienta en ese caso y se omite
        esa sesion en vez de tumbar la lista entera para las demas.
        """
        from gpmc.nucleo.manifiesto import cargar
        from gpmc.web.sesiones import _SESION_VALIDA
        filas = []
        for carpeta in raiz.iterdir():
            if not carpeta.is_dir() or not _SESION_VALIDA.match(carpeta.name):
                continue
            ruta = carpeta / "manifiesto.yaml"
            if not ruta.exists():
                continue
            try:
                m = cargar(ruta)
            except Exception:
                continue
            mtime = carpeta.stat().st_mtime
            filas.append((mtime, TramiteHistorialOut(
                sid=carpeta.name, nombre=m.tramite.nombre,
                dependencia=m.tramite.dependencia,
                modificado=datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat())))
        filas.sort(key=lambda f: f[0], reverse=True)
        return HistorialOut(tramites=[t for _, t in filas])

    @r.get("/tablero", response_model=TableroOut)
    async def leer_tablero(dependencia: Optional[str] = None):
        """Las cuentas del tablero de Simplificación. Solo agregados; sin
        registro responde 200 con listas vacías, nunca 404."""
        return TableroOut(**tablero.agregar(tablero.leer(raiz), dependencia=dependencia))

    @r.get("/grupos")
    async def listar_grupos():
        """Grupos de la plataforma ya vistos en uso, para sugerirlos en la
        tarjeta de `ACT-01`. Es ayuda, no catalogo: se puede escribir otro."""
        return {"grupos": list(GRUPOS_OBSERVADOS)}

    @r.get("/catalogos", response_model=CatalogosOut)
    async def listar_catalogos():
        """Lo que el compilador sabe emitir, para la seccion «Catalogos».

        Solo `CATALOGOS`: lo de pago o convenio (`PROPUESTAS`) no se lista
        porque no se emite y se configura en la plataforma. Nada se llama en
        vivo desde aqui: comprobar que un endpoint responde es del simulador.
        """
        from gpmc.nucleo.integraciones import CATALOGOS, SINONIMOS
        salida = []
        for clave, c in CATALOGOS.items():
            sinonimos = sorted(s for s, k in SINONIMOS.items() if k == clave)
            salida.append(CatalogoOut(
                clave=clave, proveedor=c.proveedor, tipo=c.tipo, url=c.url,
                sinonimos=sinonimos, campos_respuesta=list(c.campos_respuesta)))
        return CatalogosOut(
            catalogos=salida,
            nota=("Solo se listan los endpoints que el compilador emite. Los que exigen "
                  "credencial, pago o convenio no salen aquí: se configuran en la "
                  "plataforma como Acción PHP."))

    @r.post("/clasificar", response_model=ClasificarOut)
    async def clasificar_carpeta(cuerpo: ClasificarIn):
        """Dice a que zona va cada archivo de una carpeta, sin subir los bytes.

        El navegador manda solo la lista de nombres (`webkitdirectory` se la da
        entera), pinta el reparto en las zonas de carga y deja que la persona lo
        corrija antes de extraer. El criterio vive en `web/clasificador.py`, que
        reutiliza la normalizacion de nombres del extractor: una sola definicion
        de que es "el Diccionario" para la CLI y para el asistente.
        """
        return ClasificarOut(**dataclasses.asdict(clasificar(cuerpo.archivos)))

    @r.post("/expedientes", status_code=201, response_model=EstadoExpediente)
    async def crear_expediente(
        request: Request,
        tareas: BackgroundTasks,
        as_is: UploadFile = File(None),
        to_be: UploadFile = File(None),
        diccionario: UploadFile = File(...),
        vistas: UploadFile = File(None),
        adjuntos: List[UploadFile] = File(None),
        documentos: List[UploadFile] = File(None),
    ):
        _purgar_sesiones(raiz)
        sid = secrets.token_hex(8)
        request.state.sid = sid          # la auditoria lo lee al salir
        carpeta = raiz / sid
        carpeta.mkdir(parents=True, exist_ok=True)

        grandes = []  # type: List[str]
        ilegibles = []  # type: List[str]

        def _a_texto(archivo, datos):
            try:
                return a_texto(archivo.filename or "", datos)
            except ValueError as e:
                ilegibles.append(f"{archivo.filename or 'sin nombre'}: {e}")
                return None

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
            # `_leer` devuelve None sólo si el archivo excede el tope (ya anotado
            # en `grandes`). Un archivo de 0 bytes es `b""`: se persiste para que
            # el extractor emita un hueco en vez de "no se subió".
            if contenido is not None:
                contenido = _a_texto(archivo, contenido)
            if contenido is not None:
                (carpeta / INSUMOS[clave]).write_bytes(contenido)

        # El HTML de vistas es referencia visual: se persiste para consulta pero
        # no alimenta al extractor.
        if vistas is not None:
            contenido_vistas = await _leer(vistas)
            if contenido_vistas:
                (carpeta / ARCHIVO_VISTAS).write_bytes(contenido_vistas)

        # Documentos de apoyo: se guardan tal cual para que el analista los vea
        # junto a los huecos. No pasan por el extractor.
        for adjunto in (adjuntos or []):
            if adjunto is None or not adjunto.filename:
                continue
            datos = await _leer(adjunto)
            if not datos:
                continue
            destino = carpeta / CARPETA_ADJUNTOS
            destino.mkdir(parents=True, exist_ok=True)
            (destino / nombre_seguro(adjunto.filename)).write_bytes(datos)

        # Plantillas de los documentos que genera el tramite: a diferencia de
        # los adjuntos, estas SI las lee el extractor.
        for plantilla in (documentos or []):
            if plantilla is None or not plantilla.filename:
                continue
            datos = await _leer(plantilla)
            if not datos:
                continue
            destino = carpeta / CARPETA_DOCUMENTOS
            destino.mkdir(parents=True, exist_ok=True)
            (destino / nombre_seguro(plantilla.filename)).write_bytes(datos)

        if ilegibles:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={
                "error": "no se pudo leer el documento",
                "archivos": ilegibles,
            })

        if grandes:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=413, content={
                "error": "archivo demasiado grande",
                "archivos": grandes,
                "limite_mb": _MAX_SUBIDA // (1024 * 1024),
            })

        try:
            est, motivo = extraer_y_persistir(raiz, sid, carpeta)
        except SinPermiso as exc:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={"error": str(exc)})
        if est is None:
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={"error": motivo})
        return lanzar_propuestas_dic08(raiz, _proveedor, sid, carpeta, tareas, est)

    @r.get("/expedientes/{sid}", response_model=EstadoExpediente)
    async def leer_expediente(sid: str):
        carpeta = carpeta_de(raiz, sid)
        m = manifiesto_de(raiz, sid)
        if carpeta is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        if m is None:
            # Sesion nacida en la Fase 3 y aun sin manifiesto: la SPA abre
            # «Propuestas» con este estado en vez de decir que expiro.
            from gpmc.web.api_fase3 import generados_vigentes
            g = generados_vigentes(carpeta)
            if g is not None:
                return JSONResponse(status_code=409, content={"estado": g["estado"]})
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        return _estado(sid, carpeta, m)

    @r.get("/expedientes/{sid}/adjuntos/{nombre}")
    async def leer_adjunto(sid: str, nombre: str):
        """Un documento de apoyo del expediente.

        El nombre llega de la URL, asi que se sanea igual que al guardarlo y
        ademas se comprueba que el archivo resuelto siga dentro de la carpeta:
        un '..' codificado no puede sacar nada de la sesion.
        """
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        base = (carpeta / CARPETA_ADJUNTOS).resolve()
        archivo = (base / nombre_seguro(nombre)).resolve()
        if not archivo.is_file() or base not in archivo.parents:
            return JSONResponse(status_code=404,
                                content={"error": "adjunto no encontrado"})
        return FileResponse(archivo)

    @r.get("/expedientes/{sid}/insumos/to_be")
    async def leer_insumo_to_be(sid: str):
        """El texto del TO-BE de la sesion, para dibujarlo en la revision de
        huecos. Solo `to_be` (YAGNI); el nombre de la ruta deja sitio a los otros."""
        carpeta = carpeta_de(raiz, sid)
        ruta = carpeta / INSUMOS["to_be"] if carpeta else None
        if ruta is None or not ruta.is_file():
            return JSONResponse(status_code=404, content={"error": "sin TO-BE"})
        return Response(ruta.read_text(encoding="utf-8", errors="replace"),
                        media_type="text/markdown; charset=utf-8")

    @r.get("/expedientes/{sid}/compuerta/{gate_id}")
    async def leer_compuerta(sid: str, gate_id: str):
        """Estructura de una compuerta (respaldo por rama del hueco MMD-04):
        re-parsea el Mermaid del TO-BE de la sesion (mismo criterio que
        `reensamblar_flujo`) y expone `ramas_de_compuerta`, sin re-extraer el
        Diccionario ni tocar el manifiesto persistido."""
        carpeta = carpeta_de(raiz, sid)
        m = manifiesto_de(raiz, sid)
        if carpeta is None or m is None:
            return JSONResponse(status_code=404,
                                content={"error": "sesión no encontrada"})
        rm = rm_de_tobe(carpeta)
        est = ramas_de_compuerta(rm, m.pantallas, gate_id) if rm is not None else None
        if est is None:
            return JSONResponse(status_code=404, content={
                "error": f"compuerta no encontrada: {gate_id}"})
        return est

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
        # Para el tablero: un expediente sin AS-IS recibe su nombre aqui
        # (META-04), y la linea lleva los huecos que habia al nombrarlo.
        huecos_antes = huecos_vivos(carpeta)
        resueltos = []  # type: List[Tuple[str, str]]
        for res in cuerpo.resoluciones:
            if res.tipo == "dic08":
                if "::" not in res.ubicacion:
                    return JSONResponse(status_code=422, content={
                        "error": f"ubicacion invalida: {res.ubicacion}"})
                pantalla_id, campo_nombre = res.ubicacion.split("::", 1)
                pantalla = next((p for p in m.pantallas if p.id == pantalla_id), None)
                campo = (next((c for c in pantalla.campos if c.nombre == campo_nombre), None)
                         if pantalla else None)
                if campo is None:
                    return JSONResponse(status_code=422, content={
                        "error": f"campo no encontrado: {res.ubicacion}"})
                campos_declarados = _campos_declarados(m)
                campos_condicion = [res.condicion.campo] + [
                    cl.campo for cl in res.condicion.y]
                for cc in campos_condicion:
                    if cc not in campos_declarados:
                        return JSONResponse(status_code=422, content={
                            "error": f"la condicion referencia un campo no "
                                     f"declarado: {cc}"})
                # Las dos reglas que `agentes/verificar.py` ya aplicaba a las
                # propuestas del modelo, y que por esta via nadie comprobaba: se
                # podia guardar a mano una regla que la plataforma no puede
                # evaluar nunca. Es el mismo defecto que se le señalo al
                # Diccionario de Reposicion de Certificado.
                i_pantalla = {c.nombre: j for j, p in enumerate(m.pantallas)
                              for c in p.campos}
                i_objetivo = i_pantalla.get(campo_nombre, 0)
                for cc in campos_condicion:
                    if cc == campo_nombre:
                        log.warning("regla rechazada sid=%s %s motivo=autorreferencia campo=%s",
                                    sid, res.ubicacion, cc)
                        return JSONResponse(status_code=422, content={
                            "error": f"'{cc}' no puede decidir su propia "
                                     f"visibilidad: es el mismo campo"})
                    if i_pantalla.get(cc, 0) > i_objetivo:
                        log.warning("regla rechazada sid=%s %s motivo=campo_futuro campo=%s",
                                    sid, res.ubicacion, cc)
                        return JSONResponse(status_code=422, content={
                            "error": f"'{cc}' se captura despues que "
                                     f"'{campo_nombre}': cuando se llena esta "
                                     f"pantalla ese dato aun no existe"})
                campo.condicion_visible = res.condicion
                resueltos.append(("DIC-08", res.ubicacion))
                continue
            if res.tipo == "mmd04campo":
                campos_declarados = _campos_declarados(m)
                if res.campo not in campos_declarados:
                    return JSONResponse(status_code=422, content={
                        "error": f"campo no declarado en el manifiesto: {res.campo}"})
                d = compuertas_de(carpeta)
                d[res.ubicacion] = res.campo
                escribir_compuertas(carpeta, d)
                m = reensamblar_flujo(carpeta, m)
                resueltos.append(("MMD-04", res.ubicacion))
                if any(cx.cuando for cx in m.flujo.conexiones):
                    resueltos.append(("FLU-01", "flujo"))
                    resueltos.append(("FLU-02", "flujo"))
                continue
            if res.tipo == "mmd04rama":
                rm = rm_de_tobe(carpeta)
                est = (ramas_de_compuerta(rm, m.pantallas, res.ubicacion)
                       if rm is not None else None)
                if est is None:
                    return JSONResponse(status_code=422, content={
                        "error": f"compuerta no encontrada: {res.ubicacion}"})
                ids_validos = {r["a"] for r in est["ramas"]}
                for rama in res.ramas:
                    if rama.a not in ids_validos:
                        return JSONResponse(status_code=422, content={
                            "error": f"'{rama.a}' no es una rama de la "
                                     f"compuerta '{res.ubicacion}'"})
                campos_declarados = _campos_declarados(m)
                for rama in res.ramas:
                    campos_condicion = [rama.condicion.campo] + [
                        cl.campo for cl in rama.condicion.y]
                    for cc in campos_condicion:
                        if cc not in campos_declarados:
                            return JSONResponse(status_code=422, content={
                                "error": f"la condicion referencia un campo "
                                         f"no declarado: {cc}"})

                # `est["predecesora"]`/`rama.a` son ids de nodo del Mermaid del
                # TO-BE (p.ej. "T1"). Si la compuerta sigue sin ramificar, el
                # flujo del manifiesto es el respaldo lineal de
                # `extraer_expediente`, que usa sus propios ids de Tarea
                # ("t_<pantalla>", no los del diagrama) — hay que traducir
                # antes de tocar `m.flujo.conexiones`, o quedarían conexiones
                # colgando de tareas inexistentes.
                #
                # T9b / Hallazgo 1 (review de T9): si el mapeo nodo->pantalla
                # falla, o si CUALQUIER id no traduce a una Tarea real, no hay
                # fallback silencioso al id crudo: 422 antes de mutar nada.
                nodos_tarea = [n for n in rm.nodos if n.clase_nodo == "tarea"]
                mapa_pantallas = _mapear_nodos_a_pantallas(nodos_tarea, m.pantallas)

                def _tarea_id(mermaid_id):
                    # None si no se puede traducir (mapeo ausente, o ningun
                    # nodo/Tarea casa) — el llamador decide fallar con 422.
                    if mapa_pantallas is None:
                        return None
                    p = mapa_pantallas.get(mermaid_id)
                    if p is None:
                        return None
                    return next(
                        (t.id for t in m.flujo.tareas
                         if p.id in [pp.id for pp in t.pantallas]),
                        None,
                    )

                predecesora_id = _tarea_id(est["predecesora"])
                if predecesora_id is None:
                    return JSONResponse(status_code=422, content={
                        "error": f"no se pudo traducir el id '{est['predecesora']}' "
                                 f"del diagrama a una tarea real del manifiesto; "
                                 f"sincroniza el texto del nodo con el nombre de "
                                 f"la pantalla"})

                # T9b / Hallazgo 2 (review de T9): el respaldo lineal conecta
                # TODAS las pantallas en el orden del Diccionario, ignorando el
                # grafo Mermaid real — quitar solo la conexion que salia de la
                # predecesora deja un tramo residual entre ramas hermanas. Se
                # reconstruye, por rama, el tramo aguas abajo real caminando
                # `rm.aristas` desde `rama.a`, y se quita cualquier conexion
                # existente cuyo `.de` sea una de las tareas tocadas por ese
                # recorrido (no solo la de la predecesora).
                nodos_por_id = {n.id: n for n in rm.nodos}
                ids_if = {n.id for n in rm.nodos if n.clase_nodo == "inicio_fin"}

                nuevas_conexiones = {}  # (de, a) -> Conexion, para deduplicar
                ids_tocados = set()  # ids de Tarea (traducidos) tocados aguas abajo
                # T9c: ids de Tarea (traducidos) cuyo unico destino real
                # aguas abajo es "Fin" (mismo criterio que
                # `_flujo_ramificado` en extractores/expediente.py:
                # `terminal=(n.id in sale_if or n.id not in sale)`) — no
                # generan Conexion saliente, asi que hay que marcarlas
                # terminal=True o quedan como callejon sin salida.
                ids_terminales_reales = set()

                for rama in res.ramas:
                    nodo_inicio = nodos_por_id.get(rama.a)
                    if (nodo_inicio is not None
                            and nodo_inicio.clase_nodo == "compuerta"
                            and rama.a != res.ubicacion):
                        return JSONResponse(status_code=422, content={
                            "error": f"hay una compuerta sin resolver aguas "
                                     f"abajo de la rama '{rama.a}'"})

                    # BFS desde rama.a por rm.aristas, siguiendo solo aristas
                    # cuyo .de ya fue visitado. Un nodo inicio_fin ("Fin") es
                    # terminal para el recorrido: la arista que llega a el no
                    # genera Conexion (no hay Tarea real para "Fin"), y el
                    # recorrido no continua mas alla.
                    visitados = {rama.a}
                    cola = [rama.a]
                    aristas_utiles = []
                    ids_terminales_mermaid_rama = set()
                    while cola:
                        actual = cola.pop(0)
                        for a in rm.aristas:
                            if a.de != actual:
                                continue
                            if a.a in ids_if:
                                ids_terminales_mermaid_rama.add(a.de)
                                continue
                            destino = nodos_por_id.get(a.a)
                            if (destino is not None
                                    and destino.clase_nodo == "compuerta"
                                    and a.a != res.ubicacion):
                                return JSONResponse(status_code=422, content={
                                    "error": f"hay una compuerta sin resolver "
                                             f"aguas abajo de la rama "
                                             f"'{rama.a}'"})
                            aristas_utiles.append(a)
                            if a.a not in visitados:
                                visitados.add(a.a)
                                cola.append(a.a)

                    ids_traducidos = {}
                    for v in visitados:
                        tid = _tarea_id(v)
                        if tid is None:
                            return JSONResponse(status_code=422, content={
                                "error": f"no se pudo traducir el id '{v}' "
                                         f"del diagrama a una tarea real del "
                                         f"manifiesto; sincroniza el texto "
                                         f"del nodo con el nombre de la "
                                         f"pantalla"})
                        ids_traducidos[v] = tid

                    ids_tocados.update(ids_traducidos.values())
                    # `ids_terminales_mermaid_rama` ⊆ `visitados` (a.de
                    # siempre es un nodo ya visitado), asi que ya esta en
                    # `ids_traducidos` — sin riesgo de KeyError.
                    ids_terminales_reales.update(
                        ids_traducidos[v] for v in ids_terminales_mermaid_rama)
                    nuevas_conexiones[(predecesora_id, ids_traducidos[rama.a])] = (
                        Conexion(de=predecesora_id, a=ids_traducidos[rama.a],
                                 cuando=rama.condicion))
                    for a in aristas_utiles:
                        nuevas_conexiones[(ids_traducidos[a.de], ids_traducidos[a.a])] = (
                            Conexion(de=ids_traducidos[a.de], a=ids_traducidos[a.a],
                                     cuando=None))

                m.flujo.conexiones = [
                    cx for cx in m.flujo.conexiones
                    if cx.de != predecesora_id and cx.de not in ids_tocados]
                m.flujo.conexiones.extend(nuevas_conexiones.values())
                # T9c: marca terminal=True en las tareas cuyo unico destino
                # real aguas abajo es "Fin" (no se les genero ninguna
                # Conexion de salida) — sin tocar el flag de ninguna otra
                # Tarea, incluida la t_fin sintetica del armado lineal.
                for t in m.flujo.tareas:
                    if t.id in ids_terminales_reales:
                        t.terminal = True
                resueltos.append(("MMD-04", res.ubicacion))
                continue
            # Decisiones de publicacion (spec 2026-10-01). Van antes del
            # `if not res.valor` de abajo: aqui un valor vacio es un error de
            # quien llama, no una resolucion que se salta en silencio.
            if res.tipo == "meta07":
                publico = _si_o_no(res.valor)
                if publico is None:
                    return JSONResponse(status_code=422, content={
                        "error": "para decidir si el trámite es público se "
                                 "espera «si» o «no»"})
                m.tramite.ruts.publico = publico
                resueltos.append(("META-07", "metadatos"))
                continue
            if res.tipo == "doc04":
                nombre = res.ubicacion.split("/", 1)[-1]
                accion = next((a for a in m.acciones
                               if a.tipo == "documento" and a.nombre == nombre), None)
                if accion is None:
                    return JSONResponse(status_code=422, content={
                        "error": f"el trámite no tiene un documento «{nombre}»"})
                motivo = vale_para(accion, m.flujo, m.pantallas, res.valor)
                if motivo:
                    return JSONResponse(status_code=422, content={
                        "error": f"el documento «{nombre}» no puede generarse "
                                 f"en esa tarea: {motivo}"})
                # Se quita de donde este antes de colgarlo: dos eventos para
                # el mismo documento lo generarian dos veces.
                for t in m.flujo.tareas:
                    t.acciones_antes = [a for a in t.acciones_antes if a != nombre]
                    t.acciones_despues = [a for a in t.acciones_despues if a != nombre]
                next(t for t in m.flujo.tareas if t.id == res.valor).acciones_despues.append(nombre)
                resueltos.append(("DOC-04", f"documentos/{nombre}"))
                continue
            if res.tipo == "act01":
                actor = next((a for a in m.actores if a.id == res.ubicacion), None)
                if actor is None or actor.tipo != "grupo":
                    return JSONResponse(status_code=422, content={
                        "error": f"«{res.ubicacion}» no es un responsable al "
                                 f"que se le pueda asignar un grupo"})
                grupo = res.valor.strip()
                # La forma NO se valida: un export autentico trae
                # `grupo práctica`. Solo lo que no puede ser un nombre.
                if not grupo or "\n" in grupo or "\r" in grupo:
                    return JSONResponse(status_code=422, content={
                        "error": "escribe el nombre del grupo, en una sola línea"})
                actor.grupos_usuarios = [grupo]
                resueltos.append(("ACT-01", actor.id))
                continue
            if not res.valor:
                continue
            codigo = _TIPO_A_CODIGO[res.tipo]
            if res.tipo == "mmd03":
                tarea = next((t for t in m.flujo.tareas if t.id == res.ubicacion), None)
                if tarea is None:
                    # `res.ubicacion` puede ser el id del nodo en el diagrama
                    # Mermaid, no el id real de Tarea del manifiesto: si el
                    # flujo sigue en el respaldo lineal (compuertas sin
                    # @@campo, etiquetas que no casan, etc.), las Tareas usan
                    # sus propios ids por pantalla ("t_p1"), no los del
                    # diagrama ("T1") -- buscar por igualdad directa nunca
                    # casaba, y el handler devolvia 200 sin cambiar nada ni
                    # tachar el hueco (hallazgo post-sprint T15, "MMD-03
                    # placebo"). Se traduce via pantalla antes de rendirse,
                    # mismo patron que `_tarea_id` en la rama `mmd04rama`.
                    rm = rm_de_tobe(carpeta)
                    nodos_tarea = [n for n in rm.nodos if n.clase_nodo == "tarea"] if rm else []
                    mapa_pantallas = (
                        _mapear_nodos_a_pantallas(nodos_tarea, m.pantallas)
                        if rm else None
                    )
                    p = mapa_pantallas.get(res.ubicacion) if mapa_pantallas else None
                    if p is not None:
                        tarea = next(
                            (t for t in m.flujo.tareas
                             if p.id in [pp.id for pp in t.pantallas]),
                            None,
                        )
                if tarea is not None:
                    tarea.actor = res.valor
                    resueltos.append((codigo, res.ubicacion))
                elif rm is not None and any(
                    n.id == res.ubicacion and n.clase_nodo == "compuerta"
                    for n in rm.nodos
                ):
                    # Una compuerta es un punto de decision, no una tarea: no
                    # tiene actor que guardar en el modelo compilado. Aceptar
                    # y tachar el hueco es honesto (no hay nada que escribir,
                    # pero tampoco es un error del usuario); lo contrario
                    # seria repetir el mismo hallazgo con otro disfraz.
                    resueltos.append((codigo, res.ubicacion))
                else:
                    return JSONResponse(status_code=422, content={
                        "error": f"no se encontro la tarea '{res.ubicacion}' "
                                 f"en el manifiesto ni se pudo traducir desde "
                                 f"el diagrama a una pantalla real"})
            elif res.tipo == "meta01":
                m.tramite.ruts.tiempo_entrega = res.valor
                resueltos.append((codigo, "metadatos"))
            elif res.tipo == "meta02":
                m.tramite.dependencia = res.valor
                resueltos.append((codigo, "metadatos"))
            elif res.tipo == "meta04":
                m.tramite.nombre = res.valor
                resueltos.append((codigo, "metadatos"))
            elif res.tipo == "api03":
                campo = m.campo_por_nombre(res.ubicacion)
                if campo:
                    campo.dependencia_campo = res.valor
                    resueltos.append((codigo, res.ubicacion))

        guardar(m, carpeta / "manifiesto.yaml")
        # Si al extraer no habia nombre, el tramite no entro al tablero; entra
        # la primera vez que lo tiene. Una linea ya registrada solo corrige sus
        # rotulos (nombre, dependencia, homoclave): sus huecos son los de la
        # extraccion, no los que van quedando. Nunca revienta: el tablero es
        # un registro lateral.
        linea = tablero.resumir(m, huecos_antes)
        if linea is not None:
            # actualizar_rotulos devuelve False si la clave no estaba: entonces
            # es la primera vez que el tramite tiene nombre y se registra.
            if not tablero.actualizar_rotulos(raiz, linea):
                tablero.registrar(raiz, linea)

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

    @r.get("/expedientes/{sid}/propuestas", response_model=PropuestasOut)
    async def leer_propuestas(sid: str):
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        d = propuestas_de(carpeta)
        if d is None:
            return PropuestasOut(estado="sin_proveedor")
        visibles = [p for p in d.get("propuestas", [])
                    if p.get("veredicto") == "aceptable" and p.get("decision") is None]
        return PropuestasOut(estado=d["estado"], motivo=d.get("motivo"), propuestas=visibles)

    @r.post("/expedientes/{sid}/propuestas/{pid}/decision")
    async def decidir_propuesta(sid: str, pid: str, cuerpo: DecisionIn):
        """Solo anota. El manifiesto lo escribe /resolver, nunca esto."""
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        d = propuestas_de(carpeta) or {"estado": "sin_proveedor", "propuestas": []}
        p = next((x for x in d["propuestas"] if x.get("id") == pid), None)
        if p is None:
            return JSONResponse(status_code=404, content={"error": "propuesta no encontrada"})
        if p.get("decision") is not None:
            return JSONResponse(status_code=409, content={"error": "la propuesta ya tenía decisión"})
        p["decision"] = cuerpo.decision
        p["condicion_final"] = cuerpo.condicion_final.model_dump() if cuerpo.condicion_final else None
        p["decidida"] = datetime.now(timezone.utc).isoformat()
        escribir_propuestas(carpeta, d)
        return {"ok": True}

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
