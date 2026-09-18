"""Asistente web del compilador.

Cascara delgada sobre el nucleo: no contiene logica de dominio. Todo lo que
hace es recibir archivos, llamar a los extractores y al compilador, y servir
sus salidas. Esa separacion es la que permite que la CLI y las pruebas existan
sin navegador.
"""

from typing import Optional
import importlib.resources
import json
import os
import re
import secrets
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile, Form
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from gpmc.compilador.a_gpm import compilar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.nucleo.formato import serializar
from gpmc.nucleo.huecos import bloquean
from gpmc.nucleo.manifiesto import cargar, guardar
from gpmc.simulador.html import generar as generar_simulador
from gpmc.web import plantillas
from gpmc.web.sesiones import (
    carpeta_de,
    manifiesto_de,
    huecos_vivos,
    reconocidos_de,
    escribir_reconocidos,
    _SESION_VALIDA,
    # Movidos a sesiones.py en Task 3: api.py los necesita y app.py importa
    # api.py de forma local dentro de crear_app; tenerlos aqui crearia el
    # ciclo api.py -> app.py -> api.py.
    INSUMOS,
    ARCHIVO_VISTAS,
    _MAX_SUBIDA,
    _purgar_sesiones,
)

# CSP del SPA React: mas laxa que el `sandbox` de /vistas porque aqui el HTML lo
# generamos nosotros. Se aplica a TODA respuesta HTML de `_servir_spa` (incluido
# `GET /index.html`, que es un archivo real de dist/ y entra por la rama de
# FileResponse). No la fija el middleware de cabeceras seguras.
_CSP_SPA = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; font-src 'self' data:"
)


def crear_app(almacen: Optional[Path] = None, proveedor=None) -> FastAPI:
    raiz = Path(almacen) if almacen else Path(tempfile.mkdtemp(prefix="gpmc-"))
    raiz.mkdir(parents=True, exist_ok=True)
    _purgar_sesiones(raiz)
    app = FastAPI(title="Compilador GPM")

    # Import local (no top-level): api.py importa de gpmc.web.sesiones, y app.py
    # es quien incluye el router. El import aqui dentro evita el ciclo de modulos.
    from gpmc.web.api import crear_router
    app.include_router(crear_router(raiz, proveedor=proveedor))

    @app.middleware("http")
    async def _cabeceras_seguras(request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp

    @app.get("/descargar-plantilla")
    def descargar_plantilla():
        # La plantilla viaja como dato del paquete gpmc.web: se lee con
        # importlib.resources para que siga funcionando tras `pip install`,
        # donde no existe el arbol de fuentes ni la carpeta ejemplos/.
        texto = (
            importlib.resources.files("gpmc.web")
            .joinpath("plantilla-diccionario.md")
            .read_text(encoding="utf-8")
        )
        return Response(
            texto,
            media_type="text/markdown",
            headers={"content-disposition": 'attachment; filename="plantilla-diccionario.md"'},
        )

    @app.get("/descargar-plantilla-tobe")
    def descargar_plantilla_tobe():
        # Mismo patron que /descargar-plantilla, para la Propuesta TO-BE.
        texto = (
            importlib.resources.files("gpmc.web")
            .joinpath("plantilla-tobe.md")
            .read_text(encoding="utf-8")
        )
        return Response(
            texto,
            media_type="text/markdown",
            headers={"content-disposition": 'attachment; filename="plantilla-tobe.md"'},
        )


    @app.get("/historial", response_class=HTMLResponse)
    def historial():
        archivos = []
        for carpeta in raiz.iterdir():
            if not carpeta.is_dir() or not _SESION_VALIDA.match(carpeta.name):
                continue
            manifiesto_path = carpeta / "manifiesto.yaml"
            if manifiesto_path.exists():
                try:
                    m = cargar(manifiesto_path)
                except Exception:
                    # Un directorio de sesion puede guardar un manifiesto de un
                    # esquema anterior o a medio escribir. cargar() revienta en
                    # ese caso; se omite esa sesion en vez de tumbar la pagina
                    # entera para todas las demas.
                    continue
                archivos.append({
                    "sid": carpeta.name,
                    "nombre": m.tramite.nombre,
                    "dependencia": m.tramite.dependencia,
                })
        return HTMLResponse(plantillas.historial(archivos))

    @app.post("/extraer", response_class=HTMLResponse)
    async def extraer(
        nombre_tramite: Optional[str] = Form(None),
        as_is: UploadFile = File(None),
        to_be: UploadFile = File(None),
        diccionario: UploadFile = File(...),
        vistas: UploadFile = File(None),
    ):
        _purgar_sesiones(raiz)
        subidos = {"as_is": as_is, "to_be": to_be, "diccionario": diccionario}
        sid = secrets.token_hex(8)
        carpeta = raiz / sid
        carpeta.mkdir(parents=True, exist_ok=True)

        grandes: list[str] = []

        async def _leer(archivo) -> Optional[bytes]:
            datos = await archivo.read(_MAX_SUBIDA + 1)
            if len(datos) > _MAX_SUBIDA:
                grandes.append(archivo.filename or "sin nombre")
                return None
            return datos

        for clave, archivo in subidos.items():
            if archivo is None:
                continue
            contenido = await _leer(archivo)
            # `_leer` devuelve None sólo si el archivo excede el tope. Un archivo
            # de 0 bytes es `b""`: se persiste para que el extractor emita un
            # hueco en vez de descartarlo en silencio.
            if contenido is not None:
                (carpeta / INSUMOS[clave]).write_bytes(contenido)

        # El HTML de vistas es referencia visual: se persiste para consulta en
        # /revisar pero no alimenta al extractor.
        if vistas is not None:
            contenido_vistas = await _leer(vistas)
            if contenido_vistas:
                (carpeta / ARCHIVO_VISTAS).write_bytes(contenido_vistas)

        # Un archivo que excede el tope se descartaba en silencio y el extractor
        # se quejaba de "falta el Diccionario". Ahora se dice qué pasó.
        if grandes:
            shutil.rmtree(carpeta, ignore_errors=True)
            lista = ", ".join(f"«{n}»" for n in grandes)
            mb = _MAX_SUBIDA // (1024 * 1024)
            return HTMLResponse(plantillas.portada(
                error=f"El archivo {lista} supera el límite de {mb} MB. "
                      f"Quítale imágenes embebidas o divídelo, y vuelve a subirlo."
            ))

        try:
            r = extraer_expediente(carpeta)
        except SinPermiso as exc:
            return HTMLResponse(plantillas.portada(error=str(exc)))
            
        if r.manifiesto is None:
            motivo = r.huecos[0].mensaje if r.huecos else "no se pudo extraer el manifiesto"
            return HTMLResponse(plantillas.portada(error=motivo))

        if nombre_tramite and nombre_tramite.strip():
            # Si el as-is no tenía nombre o falló, pero el usuario lo proveyó, lo usamos
            if r.manifiesto.tramite.nombre == "[por confirmar]":
                r.manifiesto.tramite.nombre = nombre_tramite.strip()
                # Quitamos el hueco META-04 si existe
                r.huecos = [h for h in r.huecos if h.codigo != "META-04"]

        guardar(r.manifiesto, carpeta / "manifiesto.yaml")
        # Los Hueco tipados se persisten como JSON para que /revisar los
        # reconstruya sin volver a correr el extractor.
        huecos_serializables = [
            {"nivel": h.nivel, "codigo": h.codigo, "ubicacion": h.ubicacion,
             "mensaje": h.mensaje, "propuesta": h.propuesta}
            for h in r.huecos
        ]
        (carpeta / "huecos.json").write_text(
            json.dumps(huecos_serializables, ensure_ascii=False), encoding="utf-8"
        )
        return RedirectResponse(f"/revisar/{sid}", status_code=303)

    @app.post("/reconocer/{sid}")
    async def reconocer(sid: str, request: Request):
        """Marca un hueco 'falta_dato' como "lo configuro a mano en la
        plataforma". No cambia el manifiesto ni el .gpm; solo levanta la puerta
        del linter para ese hueco, dejando constancia de la decisión.

        Deuda técnica: este handler (y /resolver) hace read-modify-write sobre
        reconocidos.json / huecos.json sin candado. Hoy no hay carrera —un
        analista por sesión, uvicorn async monoproceso—; si se pasa a
        `--workers > 1` o a un pool de hilos, hay que serializar por `sid`.
        """
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        form = await request.form()
        marca = str(form.get("reconocer") or "")
        if "|" in marca:
            codigo, ubicacion = marca.split("|", 1)
            rec = reconocidos_de(carpeta)
            rec.add((codigo, ubicacion))
            escribir_reconocidos(carpeta, rec)
        return RedirectResponse(f"/revisar/{sid}", status_code=303)

    @app.post("/resolver/{sid}")
    async def resolver(sid: str, request: Request):
        m = manifiesto_de(raiz, sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
            
        form = await request.form()
        resueltos = []
        
        # Procesar MMD-03 (Asignación de actores a tareas)
        for key, value in form.items():
            if key.startswith("mmd03_") and value:
                tarea_id = key.split("_", 1)[1]
                for t in m.flujo.tareas:
                    if t.id == tarea_id:
                        t.actor = str(value)
                        resueltos.append(("MMD-03", tarea_id))
                        
            # Procesar META-01 (Tiempo de respuesta)
            if key == "meta01" and value:
                m.tramite.ruts.tiempo_entrega = str(value)
                resueltos.append(("META-01", "metadatos"))
                
            # Procesar META-02 (Dependencia)
            if key == "meta02" and value:
                m.tramite.dependencia = str(value)
                resueltos.append(("META-02", "metadatos"))
                
            # Procesar API-03 (Dependencia de campo en catálogo)
            if key.startswith("api03_") and value:
                campo_nombre = key.split("_", 1)[1]
                campo = m.campo_por_nombre(campo_nombre)
                if campo:
                    campo.dependencia_campo = str(value)
                    resueltos.append(("API-03", campo_nombre))
                    
        # Persistir los cambios si hubo alguno
        if resueltos:
            carpeta = carpeta_de(raiz, sid)
            guardar(m, carpeta / "manifiesto.yaml")
            
            # Limpiar los huecos que ya se resolvieron
            datos_huecos = json.loads((carpeta / "huecos.json").read_text(encoding="utf-8"))
            nuevos_huecos = []
            for h in datos_huecos:
                codigo = h.get("codigo")
                ubicacion = h.get("ubicacion")
                if (codigo, ubicacion) not in resueltos:
                    nuevos_huecos.append(h)
                    
            (carpeta / "huecos.json").write_text(
                json.dumps(nuevos_huecos, ensure_ascii=False), encoding="utf-8"
            )
            
        return RedirectResponse(f"/revisar/{sid}", status_code=303)

    @app.get("/simulador/{sid}", response_class=HTMLResponse)
    def simulador(sid: str):
        m = manifiesto_de(raiz, sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        return generar_simulador(m)

    @app.get("/vistas/{sid}", response_class=HTMLResponse)
    def vistas(sid: str):
        """Sirve el mockup de vistas subido por Simplificacion.

        Es referencia visual: el compilador no lo consume. Se despliega en
        una pestana aparte para que el analista compare sus pantallas
        propuestas contra lo que el extractor produjo del Diccionario.
        """
        carpeta = carpeta_de(raiz, sid)
        if carpeta is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        ruta = carpeta / ARCHIVO_VISTAS
        if not ruta.exists():
            return HTMLResponse("No se subió archivo de vistas.", status_code=404)
        # El HTML lo sube el analista sin pasar por ningún saneamiento. Se sirve
        # con CSP `sandbox`: la plataforma lo trata como origen opaco —sin
        # scripts, sin acceso al mismo origen— así un mockup con `<script>` no
        # puede leer otras sesiones ni ejecutar nada en el contexto del servidor.
        return HTMLResponse(
            ruta.read_text(encoding="utf-8"),
            headers={"Content-Security-Policy": "sandbox; default-src 'none'; "
                     "img-src data: blob:; style-src 'unsafe-inline'; font-src data:"},
        )

    @app.get("/aprobacion/{sid}", response_class=HTMLResponse)
    def aprobacion(sid: str):
        m = manifiesto_de(raiz, sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        from gpmc.compilador.aprobacion import generar_aprobacion
        return generar_aprobacion(m)

    @app.get("/descargar/{sid}/{que}")
    def descargar(sid: str, que: str):
        m = manifiesto_de(raiz, sid)
        if m is None:
            return Response("Sesión no encontrada.", status_code=404)
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", m.tramite.nombre)[:60] or "tramite"

        if que == "gpm":
            # Puerta del linter: no se entrega el .gpm mientras quede un hueco
            # bloqueante, o uno de falta_dato que nadie resolvió (por /resolver)
            # ni reconoció ("lo configuro a mano"). Se mira el estado vivo de la
            # sesión, que ya refleja lo resuelto en /resolver.
            carpeta = carpeta_de(raiz, sid)
            faltan = bloquean(huecos_vivos(carpeta), reconocidos_de(carpeta))
            if faltan:
                lineas = "\n".join(f"  [{h.codigo}] {h.ubicacion} {h.mensaje}" for h in faltan)
                return Response(
                    f"No se puede descargar el .gpm: {len(faltan)} hueco(s) sin "
                    f"resolver ni reconocer.\n\n{lineas}\n",
                    status_code=409,
                    media_type="text/plain; charset=utf-8",
                )
            return Response(
                serializar(compilar(m)),
                media_type="application/octet-stream",
                headers={"content-disposition": f'attachment; filename="{base}.gpm"'},
            )
        if que == "gpm-pruebas":
            return Response(
                serializar(compilar(m, modo_pruebas=True)),
                media_type="application/octet-stream",
                headers={"content-disposition": f'attachment; filename="{base}-test-ui.gpm"'},
            )
        if que == "manifiesto":
            destino = carpeta_de(raiz, sid) / "manifiesto.yaml"
            return Response(
                destino.read_text(encoding="utf-8"),
                media_type="application/x-yaml",
                headers={"content-disposition": f'attachment; filename="{base}.yaml"'},
            )
        return Response("Salida no reconocida.", status_code=404)

    # SPA React compilada (Task 6). Task 11 la movió de /app a / y a la
    # catch-all `/{ruta:path}`, registrada al final para que las rutas exactas
    # (/api, /simulador, /historial, …) ganen precedencia. `dist` se resuelve
    # una vez al crear la app; la variable de entorno gana para que las pruebas
    # apunten a un arbol falso.
    # El shell del SPA se revalida en cada carga; los assets, nunca.
    #
    # Vite le pone al bundle el hash de su contenido en el nombre
    # (`index-BFJjVLio.js`), asi que un contenido nuevo es un nombre nuevo:
    # cachearlos para siempre no arriesga nada y ahorra un viaje por carga. El
    # `index.html` es lo contrario -- mismo nombre, contenido que cambia en cada
    # despliegue, y dentro los nombres de los assets. Sin `no-cache`, cada
    # navegador decide por su cuenta cuanto se lo queda (heuristica sobre
    # `last-modified`), y un shell viejo pide un `.js` que ya no esta en disco.
    _CACHE_SHELL = "no-cache"          # revalida siempre; 304 si no cambio
    _CACHE_ASSET = "public, max-age=31536000, immutable"

    dist = Path(os.environ.get(
        "GPMC_FRONTEND_DIST",
        Path(__file__).resolve().parents[3] / "frontend" / "dist",
    ))

    # Primer segmento de ruta que pertenece a un handler HTML/JSON, no a la SPA.
    # La catch-all está declarada al final, así que estas rutas ya se resuelven
    # antes por su handler exacto. La comprobación de abajo es por segmento
    # exacto (`ruta.split("/")[0] in _PREFIJOS_NO_SPA`): sólo un prefijo conocido
    # seguido de `/...` (p. ej. `/api/bogus`, `/historial/x`) da 404. Un typo
    # como `/historial-xyz` o `/simuladorr/x` NO casa y cae al shell del SPA con
    # 200 + index.html — comportamiento estándar de una SPA (cualquier ruta
    # desconocida la resuelve el router de cliente).
    _PREFIJOS_NO_SPA = {
        "api", "simulador", "aprobacion", "historial", "vistas",
        "descargar", "descargar-plantilla", "extraer", "resolver", "reconocer",
    }

    def _servir_spa(ruta: str = ""):
        if not (dist / "index.html").exists():
            return PlainTextResponse(
                "El frontend no está compilado. Corre "
                "`cd frontend && npm ci && npm run build`.",
                status_code=503,
            )
        # Contencion: `ruta` viene del cliente sin sanear y puede traer `..`
        # (incluso percent-encoded). Se resuelve el candidato y se exige que
        # cuelgue de `dist`; si se sale, cae al fallback de index.html igual
        # que cualquier ruta de cliente desconocida.
        dist_r = dist.resolve()
        cand_r = (dist / ruta).resolve()
        dentro = cand_r == dist_r or dist_r in cand_r.parents
        if ruta and dentro and cand_r.is_file():
            resp = FileResponse(cand_r)
            # `index.html` es un archivo real de dist/, así que `GET /index.html`
            # entra por aquí: sin esto serviría el mismo SPA sin CSP. Los assets
            # (.js/.css/.woff2) no necesitan la política del documento.
            if cand_r.suffix == ".html":
                resp.headers["Content-Security-Policy"] = _CSP_SPA
                resp.headers["Cache-Control"] = _CACHE_SHELL
            else:
                resp.headers["Cache-Control"] = _CACHE_ASSET
            return resp
        # Typo bajo un prefijo de handler real: 404, no fallback SPA.
        if ruta and ruta.split("/")[0] in _PREFIJOS_NO_SPA:
            return PlainTextResponse("No encontrado.", status_code=404)
        resp = FileResponse(dist / "index.html")
        resp.headers["Content-Security-Policy"] = _CSP_SPA
        resp.headers["Cache-Control"] = _CACHE_SHELL
        return resp

    # Catch-all de la SPA, declarada al final: `/` y `/<lo-que-sea>`. Las rutas
    # exactas de arriba (/api, /simulador, /historial, …) se resuelven primero;
    # todo lo demás cae aquí y sirve el index.html (client-side routing), salvo
    # un archivo real de dist/ o un typo bajo un prefijo conocido (→ 404).
    @app.get("/")
    def _spa_raiz():
        return _servir_spa("")

    @app.get("/{ruta:path}")
    def _spa(ruta: str = ""):
        return _servir_spa(ruta)

    return app


app = crear_app()
