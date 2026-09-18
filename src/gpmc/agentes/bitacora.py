"""Bitacora de interaccion con el modelo, con los campos que exige la
"Licencia AI" del entregable de Planeacion (pags. 68-69): id, timestamp,
sistema origen, usuario, solicitud, instruccion, respuesta, tokens, estado.

Append-only (una linea JSON por interaccion) y en el almacen GLOBAL, no en la
carpeta de sesion: la purga por TTL de sesiones no debe llevarsela. Sin purga
propia hasta que Planeacion fije el periodo de retencion.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

RUTA_BITACORA = "bitacora-ia.jsonl"


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


class Interaccion(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = Field(default_factory=_ahora)
    sistema_origen: str = "gpm-compilador"
    usuario: str = "anonimo"          # hasta que el asistente tenga autenticacion
    sid: str
    proveedor: str
    modelo: str
    version_prompt: str
    solicitud: dict                   # resumen: huecos, n_campos, n_caracteres
    instruccion_hash: str
    respuesta: Optional[str] = None
    tokens_entrada: Optional[int] = None
    tokens_salida: Optional[int] = None
    duracion_ms: int = 0
    estado: str                       # procesada | error | sujeta_a_validacion
    alertas: list = []


def registrar(raiz: Path, it: Interaccion) -> None:
    ruta = Path(raiz) / RUTA_BITACORA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(it.model_dump(), ensure_ascii=False) + "\n")


def leer(raiz: Path) -> list:
    ruta = Path(raiz) / RUTA_BITACORA
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
