"""Registro permanente del estado de cada expediente para Simplifica: `estado.jsonl`.

Una línea JSON por `ruts_id` con la primera fecha en que apareció cada
entregable. Lo lee `GET /api/v1/expedientes?ruts_id=…` (web/api_estado.py).
Vive en el almacén de sesiones pero `_purgar_sesiones` no lo toca (solo borra
carpetas con nombre de sesión): la purga se lleva la evidencia a los 7 días y
el estado tiene que sobrevivirla. Mismo patrón que `tablero.jsonl`: escritura
atómica y lectura tolerante.

Reglas (spec 2026-11-06-api-de-estado-para-simplifica):
- Solo por `ruts_id` exacto, alfanumérico de 1 a 20; nunca por nombre.
- Una fecha puesta no se reescribe: re-extraer otro día no la mueve.
- Un entregable sin evidencia es `None`, nunca una fecha supuesta.
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("gpmc.web.estado")

ARCHIVO = "estado.jsonl"
ENTREGABLES = ("as-is", "to-be", "diccionario", "bpmn", "gpm", "aprobacion", "publicado")
RUTS_VALIDO = re.compile(r"\A[A-Za-z0-9]{1,20}\Z")

# El extractor y una descarga del .gpm pueden coincidir: el ciclo
# leer-modificar-escribir de `anotar` va serializado dentro del proceso.
_CANDADO = threading.Lock()


def hoy() -> str:
    """AAAA-MM-DD en America/Mexico_City. Sin la base de zonas del sistema se
    usa −6 h fijo, el vigente desde que México quitó el horario de verano (2022)."""
    try:
        from zoneinfo import ZoneInfo
        zona = ZoneInfo("America/Mexico_City")
    except Exception:  # zoneinfo ausente o sin tzdata
        zona = timezone(timedelta(hours=-6))
    return datetime.now(zona).date().isoformat()


def _valido(ruts_id) -> bool:
    return isinstance(ruts_id, str) and bool(RUTS_VALIDO.match(ruts_id))


def _bien_formada(d) -> bool:
    if not isinstance(d, dict) or not _valido(d.get("ruts_id")):
        return False
    e = d.get("entregables")
    return isinstance(e, dict) and all(isinstance(e.get(k), (str, type(None))) for k in ENTREGABLES)


def leer(raiz: Path) -> "list[dict]":
    """Todas las líneas válidas. Una corrupta se salta y se anota con su número."""
    ruta = Path(raiz) / ARCHIVO
    try:
        if not ruta.exists():
            return []
        crudo = ruta.read_text(encoding="utf-8")
    except OSError:
        log.exception("estado.jsonl: no se pudo leer el registro")
        return []
    salida = []
    for n, cruda in enumerate(crudo.splitlines(), 1):
        if not cruda.strip():
            continue
        try:
            d = json.loads(cruda)
        except json.JSONDecodeError:
            log.warning("estado.jsonl: linea %d ilegible, se salta", n)
            continue
        if not _bien_formada(d):
            log.warning("estado.jsonl: linea %d con forma inesperada, se salta", n)
            continue
        salida.append({"ruts_id": d["ruts_id"],
                       "entregables": {k: d["entregables"].get(k) for k in ENTREGABLES}})
    return salida


def _escribir(raiz: Path, lineas: "list[dict]") -> bool:
    """Reescribe el archivo entero de forma atómica (temporal + os.replace). Nunca
    propaga un error: es un registro lateral y su fallo no debe tumbar la extracción
    ni la descarga."""
    destino = Path(raiz) / ARCHIVO
    temporal = Path(raiz) / (ARCHIVO + ".tmp")
    try:
        temporal.write_text(
            "".join(json.dumps(l, ensure_ascii=False) + "\n"
                    for l in sorted(lineas, key=lambda l: l["ruts_id"])),
            encoding="utf-8",
        )
        os.replace(temporal, destino)
        return True
    except OSError:
        log.exception("estado.jsonl: no se pudo escribir el registro")
        try:
            temporal.unlink()
        except OSError:
            pass
        return False


def anotar(raiz: Path, ruts_id: str, entregable: str, cuando: Optional[str] = None) -> bool:
    """Pone la fecha de `entregable` para `ruts_id` solo si aún no tenía. Devuelve
    False si el `ruts_id` o el entregable no son válidos, o si no se pudo escribir."""
    if not _valido(ruts_id) or entregable not in ENTREGABLES:
        return False
    with _CANDADO:
        lineas = leer(raiz)
        linea = next((l for l in lineas if l["ruts_id"] == ruts_id), None)
        if linea is None:
            linea = {"ruts_id": ruts_id, "entregables": {k: None for k in ENTREGABLES}}
            lineas.append(linea)
        if linea["entregables"][entregable] is not None:
            return True
        linea["entregables"][entregable] = cuando or hoy()
        return _escribir(raiz, lineas)


def consultar(raiz: Path, ruts_id: str) -> "list[dict]":
    """El contrato que espera Simplifica (`shared/compilador.py`): lista vacía si no
    hay expediente con ese `ruts_id`; si lo hay, uno solo con las siete claves."""
    if not _valido(ruts_id):
        return []
    for l in leer(raiz):
        if l["ruts_id"] == ruts_id:
            fechas = [f for f in l["entregables"].values() if f]
            return [{"analista": "", "actualizado": max(fechas) if fechas else "",
                     "entregables": dict(l["entregables"])}]
    return []


# Archivo de la sesion (claves de `sesiones.INSUMOS`) -> entregable del contrato.
_ENTREGABLE_DE_INSUMO = {"as_is": "as-is", "to_be": "to-be", "diccionario": "diccionario"}


def anotar_insumos(raiz: Path, carpeta: Path, ruts_id: str) -> None:
    """Tras extraer: anota cada insumo que existe en la carpeta de la sesión. Sin
    `ruts_id` no hace nada (el expediente no está ligado a Simplifica)."""
    if not ruts_id:
        return
    from gpmc.web.sesiones import INSUMOS  # web/ es quien conoce los nombres de archivo
    for clave, entregable in _ENTREGABLE_DE_INSUMO.items():
        try:
            existe = (Path(carpeta) / INSUMOS[clave]).exists()
        except OSError:
            existe = False
        if existe:
            anotar(raiz, ruts_id, entregable)
