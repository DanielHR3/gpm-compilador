"""Registro permanente para el tablero de Simplificación: `tablero.jsonl`.

Una línea JSON por trámite, escrita al extraer (`POST /expedientes`), con
SOLO agregados: nunca valores de catálogo, textos de plantilla, condiciones,
adjuntos ni el sid. Vive en el almacén de sesiones pero `_purgar_sesiones`
no lo toca (solo borra carpetas con nombre de sesión). La identidad es
`planeacion.registro.clave(nombre)`: el mismo trámite reemplaza su línea.
"""

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gpmc.estimador import estimar
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.integraciones import CATALOGOS, clave_de
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.planeacion.registro import clave

log = logging.getLogger("gpmc.web.tablero")

ARCHIVO = "tablero.jsonl"
_SIN_NOMBRE = {"", "[por confirmar]"}
# Las etiquetas de los campos archivo del Diccionario vienen como
# «Documento: Tarjeta de Circulación»; el prefijo no es parte del requisito.
_PREFIJO_DOC = "documento:"


def _requisito(etiqueta: str) -> str:
    t = (etiqueta or "").strip()
    if t.lower().startswith(_PREFIJO_DOC):
        t = t[len(_PREFIJO_DOC):].strip()
    return t


def resumir(m: Manifiesto, huecos: "list[Hueco]",
            ahora: Optional[datetime] = None) -> Optional[dict]:
    """La línea del registro para `m`, o None si el trámite no tiene nombre."""
    nombre = (m.tramite.nombre or "").strip()
    if nombre in _SIN_NOMBRE:
        return None
    ahora = ahora or datetime.now(timezone.utc)
    campos = [c for p in m.pantallas for c in p.campos]
    requisitos: "list[str]" = []
    vistos = set()
    for c in campos:
        if c.tipo != "file":
            continue
        r = _requisito(c.etiqueta or c.nombre)
        k = clave(r)
        if r and k not in vistos:
            vistos.add(k)
            requisitos.append(r)
    catalogos = sorted({k for k in (clave_de(c.origen) for c in campos if c.origen)
                        if k in CATALOGOS})
    est = estimar(m)
    return {
        "clave": clave(nombre),
        "nombre": nombre,
        "dependencia": m.tramite.dependencia,
        "homoclave": m.tramite.homoclave,
        "registrado": ahora.isoformat(),
        "requisitos": requisitos,
        "campos": [c.nombre.lstrip("@") for c in campos],
        "huecos": dict(Counter(h.codigo for h in huecos)),
        "metricas": {
            "tareas": est.metricas.tareas, "bifurcaciones": est.metricas.bifurcaciones,
            "vistas": est.metricas.vistas, "campos": est.metricas.campos,
            "acciones": est.metricas.acciones, "integraciones": est.metricas.integraciones,
        },
        "nivel": est.nivel,
        "catalogos": catalogos,
        "actores": len(m.actores),
        "documentos": sum(1 for a in m.acciones if a.tipo == "documento"),
    }


def leer(raiz: Path) -> "list[dict]":
    """Todas las líneas válidas. Una corrupta se salta y se anota con su número."""
    ruta = raiz / ARCHIVO
    if not ruta.exists():
        return []
    salida = []
    for n, cruda in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        if not cruda.strip():
            continue
        try:
            d = json.loads(cruda)
        except json.JSONDecodeError:
            log.warning("tablero.jsonl: linea %d ilegible, se salta", n)
            continue
        if isinstance(d, dict) and d.get("clave"):
            salida.append(d)
    return salida


def registrar(raiz: Path, linea: dict) -> None:
    """Escribe `linea` reemplazando la de la misma clave. El archivo es chico:
    se reescribe entero en un solo write_text, así nunca quedan dos líneas de
    un mismo trámite aunque dos extracciones terminen casi a la vez."""
    lineas = [l for l in leer(raiz) if l["clave"] != linea["clave"]]
    lineas.append(linea)
    (raiz / ARCHIVO).write_text(
        "".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lineas),
        encoding="utf-8",
    )
