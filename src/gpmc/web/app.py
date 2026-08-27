"""Asistente web del compilador.

Cascara delgada sobre el nucleo: no contiene logica de dominio. Todo lo que
hace es recibir archivos, llamar a los extractores y al compilador, y servir
sus salidas. Esa separacion es la que permite que la CLI y las pruebas existan
sin navegador.
"""

from typing import Optional
import re
import secrets
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from gpmc.compilador.a_gpm import compilar
from gpmc.estimador import estimar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.nucleo.formato import serializar
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

    @app.post("/extraer", response_class=HTMLResponse)
    async def extraer(
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
            # r.huecos son Hueco tipados; la plantilla espera texto.
            motivo = str(r.huecos[0]) if r.huecos else "no se pudo extraer el manifiesto"
            return HTMLResponse(plantillas.portada(error=motivo))

        guardar(r.manifiesto, carpeta / "manifiesto.yaml")
        (carpeta / "huecos.txt").write_text(
            "\n".join(str(h) for h in r.huecos), encoding="utf-8"
        )
        return RedirectResponse(f"/revisar/{sid}", status_code=303)

    @app.get("/revisar/{sid}", response_class=HTMLResponse)
    def revisar(sid: str):
        m = _manifiesto(sid)
        if m is None:
            return HTMLResponse("Sesión no encontrada.", status_code=404)
        carpeta = _carpeta(sid)
        crudo = (carpeta / "huecos.txt").read_text(encoding="utf-8")
        huecos = [h for h in crudo.splitlines() if h.strip()]
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
