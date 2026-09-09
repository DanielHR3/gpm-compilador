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
