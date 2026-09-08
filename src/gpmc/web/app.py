"""Asistente web del compilador.

Cascara delgada sobre el nucleo: no contiene logica de dominio. Todo lo que
hace es recibir archivos, llamar a los extractores y al compilador, y servir
sus salidas. Esa separacion es la que permite que la CLI y las pruebas existan
sin navegador.
"""

from typing import Optional
import importlib.resources
import json
import re
import secrets
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from gpmc.compilador.a_gpm import compilar
from gpmc.estimador import estimar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.nucleo.formato import serializar
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import cargar, guardar
from gpmc.simulador.analisis import analizar
from gpmc.simulador.html import generar as generar_simulador
from gpmc.web import plantillas

_SESION_VALIDA = re.compile(r"\A[0-9a-f]{16}\Z")

INSUMOS = {
    "as_is": "Análisis AS-IS.md",
    "to_be": "Propuesta TO-BE.md",
    "diccionario": "Diccionario de Datos.md",
}

# El HTML de vistas es referencia visual, no insumo de extraccion. Se guarda
# en la sesion para que el analista lo consulte durante la revision, pero no
# alimenta al extractor ni al compilador: el origen de verdad de las pantallas
# sigue siendo el Diccionario de Datos.
ARCHIVO_VISTAS = "Vistas.html"


def crear_app(almacen: Optional[Path] = None) -> FastAPI:
    raiz = Path(almacen) if almacen else Path(tempfile.mkdtemp(prefix="gpmc-"))
    raiz.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Compilador GPM")

    def _carpeta(sid: str) -> Optional[Path]:
        """Resuelve la sesion. El identificador se valida contra un patron
        estricto: nunca se interpola en una ruta sin comprobarlo."""
        if not _SESION_VALIDA.match(sid or ""):
            return None
        destino = raiz / sid
        return destino if destino.is_dir() else None

    def _manifiesto(sid: str):
        carpeta = _carpeta(sid)
        if carpeta is None:
            return None
        ruta = carpeta / "manifiesto.yaml"
        return cargar(ruta) if ruta.exists() else None

    @app.get("/", response_class=HTMLResponse)
    def portada():
        return plantillas.portada()

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
        subidos = {"as_is": as_is, "to_be": to_be, "diccionario": diccionario}
        sid = secrets.token_hex(8)
        carpeta = raiz / sid
        carpeta.mkdir(parents=True, exist_ok=True)

        for clave, archivo in subidos.items():
            if archivo is None:
                continue
            contenido = await archivo.read()
            if contenido:
                (carpeta / INSUMOS[clave]).write_bytes(contenido)

        # El HTML de vistas es referencia visual: se persiste para consulta en
        # /revisar pero no alimenta al extractor.
        if vistas is not None:
            contenido_vistas = await vistas.read()
            if contenido_vistas:
                (carpeta / ARCHIVO_VISTAS).write_bytes(contenido_vistas)

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

    @app.get("/revisar/{sid}", response_class=HTMLResponse)
    def revisar(sid: str):
        m = _manifiesto(sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        carpeta = _carpeta(sid)
        datos = json.loads((carpeta / "huecos.json").read_text(encoding="utf-8"))
        huecos = [Hueco(**d) for d in datos]
        tiene_vistas = (carpeta / ARCHIVO_VISTAS).exists()
        return plantillas.revision(
            m, huecos, analizar(m).problemas, estimar(m), sid,
            tiene_vistas=tiene_vistas,
        )

    @app.post("/resolver/{sid}")
    async def resolver(sid: str, request: Request):
        m = _manifiesto(sid)
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
            carpeta = _carpeta(sid)
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
        m = _manifiesto(sid)
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
        carpeta = _carpeta(sid)
        if carpeta is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        ruta = carpeta / ARCHIVO_VISTAS
        if not ruta.exists():
            return HTMLResponse("No se subió archivo de vistas.", status_code=404)
        return HTMLResponse(ruta.read_text(encoding="utf-8"))

    @app.get("/aprobacion/{sid}", response_class=HTMLResponse)
    def aprobacion(sid: str):
        m = _manifiesto(sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        from gpmc.compilador.aprobacion import generar_aprobacion
        return generar_aprobacion(m)

    @app.get("/descargar/{sid}/{que}")
    def descargar(sid: str, que: str):
        m = _manifiesto(sid)
        if m is None:
            return Response("Sesión no encontrada.", status_code=404)
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", m.tramite.nombre)[:60] or "tramite"

        if que == "gpm":
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
            destino = _carpeta(sid) / "manifiesto.yaml"
            return Response(
                destino.read_text(encoding="utf-8"),
                media_type="application/x-yaml",
                headers={"content-disposition": f'attachment; filename="{base}.yaml"'},
            )
        return Response("Salida no reconocida.", status_code=404)

    return app


app = crear_app()
