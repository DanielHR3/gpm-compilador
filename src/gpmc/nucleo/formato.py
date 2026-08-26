"""Serializacion del formato .gpm, fiel al export de la plataforma.

La plataforma GPM corre sobre PHP y exporta con json_encode sin la bandera
JSON_UNESCAPED_SLASHES, de modo que toda diagonal aparece escapada como \\/.
Ademas usa separadores compactos y escapa los caracteres no ASCII.

Verificado byte a byte contra dos exports autenticos e independientes:
un export de referencia (plataforma) y otro export de referencia (otra implementacion).
"""

import json
from pathlib import Path


def serializar(obj: dict) -> str:
    """Convierte un objeto a la forma textual exacta que produce la plataforma."""
    crudo = json.dumps(obj, separators=(",", ":"), ensure_ascii=True)
    return crudo.replace("/", "\\/")


def escribir(obj: dict, ruta: Path) -> None:
    """Guarda un .gpm en el formato de la plataforma, sin salto de linea final."""
    Path(ruta).write_text(serializar(obj), encoding="utf-8")


def leer(ruta: Path) -> dict:
    """Carga un .gpm."""
    return json.loads(Path(ruta).read_text(encoding="utf-8"))
