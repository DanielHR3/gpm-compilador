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

from fastapi import FastAPI, File, UploadFile, Form
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
        return plantillas.revision(m, huecos, analizar(m).problemas, estimar(m), sid)

    @app.get("/simulador/{sid}", response_class=HTMLResponse)
    def simulador(sid: str):
        m = _manifiesto(sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        return generar_simulador(m)

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
