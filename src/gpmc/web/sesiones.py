"""Helpers de sesión del asistente web.

Antes eran closures dentro de `crear_app` (cerraban sobre `raiz`); ahora son
funciones de módulo que reciben `raiz` (o `carpeta`) como argumento, para que
`web/api.py` pueda importarlas sin arrastrar toda la app.
"""

import json
import re
import shutil
import time
from pathlib import Path
from typing import Optional

from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import cargar

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

# Documentos de apoyo del expediente: diagramas en PNG, PDF escaneados, oficios.
# No alimentan al extractor —igual que las vistas— pero el analista los necesita
# a la vista mientras resuelve los huecos.
CARPETA_ADJUNTOS = "adjuntos"

# Plantillas de los documentos que el tramite genera (.md con {{variables}}).
# A diferencia de los adjuntos, estas SI alimentan al extractor.
CARPETA_DOCUMENTOS = "documentos"

_IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def nombre_seguro(nombre: str) -> str:
    """Un nombre de archivo que no puede escribir fuera de su carpeta.

    Lo escribe quien sube el archivo, asi que se trata como hostil: se tira todo
    separador de ruta y todo tramo '..'. Se conservan espacios y acentos, que
    son normales en un documento de gobierno y no hacen dano.
    """
    tramos = [t for t in re.split(r"[\\/]+", nombre or "") if t not in ("", ".", "..")]
    limpio = "_".join(tramos).strip().strip(".")
    return limpio or "adjunto"


def tipo_de_adjunto(nombre: str) -> str:
    """'imagen', 'pdf' u 'otro': decide como se muestra, no como se lee."""
    sufijo = Path(nombre).suffix.lower()
    if sufijo in _IMAGENES:
        return "imagen"
    return "pdf" if sufijo == ".pdf" else "otro"


def adjuntos_de(carpeta: Path) -> "list[dict]":
    """Los adjuntos de una sesion, en el orden en que se subieron."""
    d = carpeta / CARPETA_ADJUNTOS
    if not d.is_dir():
        return []
    archivos = sorted(d.iterdir(), key=lambda p: p.stat().st_mtime)
    return [
        {"nombre": a.name, "tipo": tipo_de_adjunto(a.name)}
        for a in archivos if a.is_file()
    ]


# Un .md de trámite pesa unos KB; 10 MB es holgado y frena una subida de varios
# GB que agotaría la memoria del proceso (lee el archivo entero en RAM).
_MAX_SUBIDA = 10 * 1024 * 1024

# El asistente corre permanente (launchd KeepAlive) y cada /extraer deja una
# carpeta de sesión. Sin limpieza se acumulan hasta llenar el disco. No hay
# cron ni scheduler: se barren las viejas al arrancar y en cada /extraer.
_TTL_SESION_DIAS = 7


def _purgar_sesiones(raiz: Path, dias: int = _TTL_SESION_DIAS) -> None:
    """Borra las carpetas de sesión sin tocar hace más de `dias`. Solo mira
    carpetas con nombre de sesión válido (16 hex), así nunca borra otra cosa
    del almacén. Nunca propaga un error: una limpieza fallida no tumba nada."""
    limite = time.time() - dias * 86400
    try:
        candidatas = list(raiz.iterdir())
    except OSError:
        return
    for d in candidatas:
        try:
            if (d.is_dir() and _SESION_VALIDA.match(d.name)
                    and d.stat().st_mtime < limite):
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def carpeta_de(raiz: Path, sid: str) -> Optional[Path]:
    """Resuelve la sesion. El identificador se valida contra un patron
    estricto: nunca se interpola en una ruta sin comprobarlo."""
    if not _SESION_VALIDA.match(sid or ""):
        return None
    destino = raiz / sid
    return destino if destino.is_dir() else None


def manifiesto_de(raiz: Path, sid: str):
    carpeta = carpeta_de(raiz, sid)
    if carpeta is None:
        return None
    ruta = carpeta / "manifiesto.yaml"
    return cargar(ruta) if ruta.exists() else None


def huecos_vivos(carpeta: Path) -> "list[Hueco]":
    ruta = carpeta / "huecos.json"
    if not ruta.exists():
        return []
    return [Hueco(**d) for d in json.loads(ruta.read_text(encoding="utf-8"))]


def reconocidos_de(carpeta: Path) -> set:
    """Huecos 'falta_dato' que una persona marcó como "los configuro a mano
    en la plataforma". Cada entrada es (codigo, ubicacion)."""
    ruta = carpeta / "reconocidos.json"
    if not ruta.exists():
        return set()
    return {tuple(x) for x in json.loads(ruta.read_text(encoding="utf-8"))}


def escribir_reconocidos(carpeta: Path, rec: set) -> None:
    (carpeta / "reconocidos.json").write_text(
        json.dumps(sorted(rec), ensure_ascii=False), encoding="utf-8")


def compuertas_de(carpeta: Path) -> dict:
    """Overrides de campo por compuerta ({id_compuerta: nombre_campo}) que una
    persona fijó a mano para compuertas que el diagrama TO-BE no ramificó
    solo. Alimenta `_flujo_ramificado(overrides=...)` vía `reensamblar_flujo`."""
    ruta = carpeta / "compuertas.json"
    if not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_compuertas(carpeta: Path, d: dict) -> None:
    (carpeta / "compuertas.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")


def propuestas_de(carpeta: Path):
    """Estado y propuestas del generador de IA para esta sesion, o None si el
    generador nunca corrio (sin proveedor)."""
    ruta = carpeta / "propuestas.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_propuestas(carpeta: Path, d: dict) -> None:
    (carpeta / "propuestas.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")
