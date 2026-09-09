"""Helpers de sesión del asistente web.

Antes eran closures dentro de `crear_app` (cerraban sobre `raiz`); ahora son
funciones de módulo que reciben `raiz` (o `carpeta`) como argumento, para que
`web/api.py` pueda importarlas sin arrastrar toda la app.
"""

import json
import re
from pathlib import Path
from typing import Optional

from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import cargar

_SESION_VALIDA = re.compile(r"\A[0-9a-f]{16}\Z")


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
