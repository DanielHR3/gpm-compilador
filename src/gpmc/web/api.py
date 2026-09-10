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
from typing import Annotated, List, Literal, Optional, Tuple, Union

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from gpmc.compilador.a_gpm import compilar
from gpmc.estimador import estimar
from gpmc.extractores.expediente import (
    SinPermiso,
    _mapear_nodos_a_pantallas,
    extraer_expediente,
    ramas_de_compuerta,
)
from gpmc.nucleo.formato import serializar
from gpmc.nucleo.huecos import HuecoOut, bloquean
from gpmc.nucleo.manifiesto import Conexion, Condicion, Manifiesto, guardar
from gpmc.simulador.analisis import analizar
from gpmc.web.reensamblado import reensamblar_flujo, rm_de_tobe
from gpmc.web.sesiones import (
    ARCHIVO_VISTAS,
    INSUMOS,
    _MAX_SUBIDA,
    _purgar_sesiones,
    carpeta_de,
    compuertas_de,
    escribir_compuertas,
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


def _campos_declarados(m: Manifiesto) -> set:
    """Nombres de todos los campos declarados en el manifiesto (todas las
    pantallas). Usado por las ramas `dic08`, `mmd04campo` y `mmd04rama` de
    `resolver_expediente` para validar que una `Condicion` (o el `campo` de
    `mmd04campo`) no referencie uno inexistente (spec 5.1 / Ruling 5)."""
    return {c.nombre for p in m.pantallas for c in p.campos}


class ResolucionIn(BaseModel):
    """Una resolucion de hueco: donde aplicarla y con que valor."""

    tipo: Literal["mmd03", "meta01", "meta02", "api03"]
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
            # `_leer` devuelve None sólo si el archivo excede el tope (ya anotado
            # en `grandes`). Un archivo de 0 bytes es `b""`: se persiste para que
            # el extractor emita un hueco en vez de "no se subió".
            if contenido is not None:
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
                    while cola:
                        actual = cola.pop(0)
                        for a in rm.aristas:
                            if a.de != actual:
                                continue
                            if a.a in ids_if:
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
                resueltos.append(("MMD-04", res.ubicacion))
                continue
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
