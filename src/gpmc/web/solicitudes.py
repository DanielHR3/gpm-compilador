"""Trámites que Simplifica envía al Compilador («Enviar al Compilador»): `solicitudes.jsonl`.

Una línea por `ruts_id` con la ficha que mandó Simplifica (nombre, dependencia, datos de RUTS), cuándo llegó y si
alguien ya la vio. Es lo que enciende la campanita de la SPA. Mismo patrón que `estado.jsonl`: se lee en bytes, se
reescribe de forma atómica, conserva las líneas rotas y `_purgar_sesiones` no lo toca.
Spec: docs/superpowers/specs/2026-11-10-solicitudes-desde-simplifica-design.md
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from gpmc.web.estado import RUTS_VALIDO

log = logging.getLogger("gpmc.web.solicitudes")

ARCHIVO = "solicitudes.jsonl"
CAMPOS = ("nombre", "dependencia", "enviado_por")
CAMPOS_RUTS = ("costo", "tiempo_entrega", "description")
LARGO = 300
LARGO_DESCRIPCION = 2000
# Ficha estructurada (M-110 de Simplifica, 2026-11-11): los requisitos del trámite con quién los
# emite y qué hacer con ellos, y sus etapas en orden. Opcionales: el contrato anterior sigue valiendo.
CAMPOS_REQUISITO = ("nombre", "emisor", "tratamiento")
MAX_REQUISITOS = 80
MAX_ETAPAS = 60

_CANDADO = threading.Lock()


def ahora() -> str:
    """Fecha y hora en America/Mexico_City, sin zona (AAAA-MM-DDTHH:MM:SS)."""
    try:
        from zoneinfo import ZoneInfo
        zona = ZoneInfo("America/Mexico_City")
    except Exception:
        zona = timezone(timedelta(hours=-6))
    return datetime.now(zona).replace(microsecond=0, tzinfo=None).isoformat()


def _texto(valor, largo: int) -> str:
    return " ".join(str(valor or "").split())[:largo]


def limpiar(cuerpo) -> Optional[dict]:
    """La ficha validada y recortada, o None si no cumple el contrato (claves de más, ruts_id inválido o sin nombre)."""
    if not isinstance(cuerpo, dict) or set(cuerpo) - {"ruts_id", "ruts", "requisitos", "etapas", *CAMPOS}:
        return None
    requisitos, etapas = cuerpo.get("requisitos") or [], cuerpo.get("etapas") or []
    if (not isinstance(requisitos, list) or len(requisitos) > MAX_REQUISITOS
            or not all(isinstance(r, dict) and not set(r) - set(CAMPOS_REQUISITO) and _texto(r.get("nombre"), LARGO)
                       for r in requisitos)):
        return None
    if not isinstance(etapas, list) or len(etapas) > MAX_ETAPAS or not all(isinstance(e, str) for e in etapas):
        return None
    ruts_id = cuerpo.get("ruts_id")
    if not isinstance(ruts_id, str) or not RUTS_VALIDO.match(ruts_id):
        return None
    ruts = cuerpo.get("ruts") or {}
    if not isinstance(ruts, dict) or set(ruts) - set(CAMPOS_RUTS):
        return None
    ficha = {"ruts_id": ruts_id, **{c: _texto(cuerpo.get(c), LARGO) for c in CAMPOS},
             "ruts": {c: _texto(ruts.get(c), LARGO_DESCRIPCION if c == "description" else LARGO) for c in CAMPOS_RUTS},
             "requisitos": [{c: _texto(r.get(c), LARGO) for c in CAMPOS_REQUISITO} for r in requisitos],
             "etapas": [e for e in (_texto(e, LARGO) for e in etapas) if e]}
    if not ficha["nombre"] or not ficha["dependencia"]:
        return None
    return ficha


def _cargar(raiz: Path) -> "tuple[list[dict], list[bytes]]":
    ruta = Path(raiz) / ARCHIVO
    try:
        if not ruta.exists():
            return [], []
        crudo = ruta.read_bytes()
    except OSError:
        log.exception("solicitudes.jsonl: no se pudo leer")
        return [], []
    validas, rotas = [], []
    for n, linea in enumerate(crudo.split(b"\n"), 1):
        if not linea.strip():
            continue
        try:
            d = json.loads(linea.decode("utf-8"))
        except ValueError:
            log.warning("solicitudes.jsonl: linea %d ilegible, se salta", n)
            rotas.append(linea)
            continue
        ficha = limpiar({k: v for k, v in d.items() if k not in ("recibida", "nueva")}) if isinstance(d, dict) else None
        if ficha is None:
            log.warning("solicitudes.jsonl: linea %d con forma inesperada, se salta", n)
            rotas.append(linea)
            continue
        ficha["recibida"] = str(d.get("recibida") or "")
        ficha["nueva"] = bool(d.get("nueva"))
        validas.append(ficha)
    return validas, rotas


def leer(raiz: Path) -> "list[dict]":
    """Todas, de la más reciente a la más vieja."""
    return sorted(_cargar(raiz)[0], key=lambda s: s["recibida"], reverse=True)


def _escribir(raiz: Path, lineas: "list[dict]", rotas: "list[bytes]") -> bool:
    destino = Path(raiz) / ARCHIVO
    temporal = Path(raiz) / (ARCHIVO + ".tmp")
    try:
        temporal.write_bytes(b"".join(json.dumps(l, ensure_ascii=False).encode("utf-8") + b"\n"
                                      for l in sorted(lineas, key=lambda l: l["ruts_id"]))
                             + b"".join(r + b"\n" for r in rotas))
        os.replace(temporal, destino)
        return True
    except OSError:
        log.exception("solicitudes.jsonl: no se pudo escribir")
        try:
            temporal.unlink()
        except OSError:
            pass
        return False


def registrar(raiz: Path, ficha: dict) -> bool:
    """Guarda (o reemplaza) la ficha de ese `ruts_id` y la marca como nueva."""
    limpia = limpiar(ficha)
    if limpia is None:
        return False
    with _CANDADO:
        lineas, rotas = _cargar(raiz)
        lineas = [l for l in lineas if l["ruts_id"] != limpia["ruts_id"]]
        lineas.append({**limpia, "recibida": ahora(), "nueva": True})
        return _escribir(raiz, lineas, rotas)


def marcar_vista(raiz: Path, ruts_id: str) -> bool:
    """False si no hay solicitud con ese `ruts_id`."""
    with _CANDADO:
        lineas, rotas = _cargar(raiz)
        for l in lineas:
            if l["ruts_id"] == ruts_id:
                l["nueva"] = False
                return _escribir(raiz, lineas, rotas)
    return False


def buscar(raiz: Path, ruts_id: str) -> Optional[dict]:
    return next((s for s in leer(raiz) if s["ruts_id"] == ruts_id), None)


def as_is_inicial(ficha: dict) -> str:
    """AS-IS para empezar el expediente: frontmatter con `ruts_id` y dependencia (lo que lee `extractores/metadatos`)
    y los datos de RUTS que mandó Simplifica. El analista lo completa y lo sube como insumo."""
    def comillas(t: str) -> str:
        return '"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"'
    r = ficha.get("ruts") or {}
    nombre = " ".join(ficha["nombre"].split())
    partes = [
        "---", f'ruts_id: "{ficha["ruts_id"]}"', f"dependencia: {comillas(ficha['dependencia'])}", "---",
        f"# Análisis AS-IS — {nombre}", "",
        "> Enviado desde Simplifica" + (f" por {ficha['enviado_por']}" if ficha.get("enviado_por") else "") + ".",
        "", "## Ficha de RUTS", "",
        f"**Tiempo de respuesta:** {r.get('tiempo_entrega') or '[por confirmar]'}",
        f"**Costo:** {r.get('costo') or '[por confirmar]'}",
        "", r.get("description") or "", ""]
    requisitos = ficha.get("requisitos") or []
    if requisitos:
        # En la forma que lee `extractores.as_is.requisitos_del_as_is`: lista anidada, y la nota
        # después de la raya. El nombre no puede llevar raya ni paréntesis propios.
        partes += ["- **Requisitos:**"]
        for q in requisitos:
            nombre = re.sub(r"\s+[—–-]\s+", ", ", re.sub(r"\s*\([^()]*\)", "", q["nombre"])).strip()
            nota = "; ".join(x for x in (f"lo emite {q['emisor']}" if q.get("emisor") else "", q.get("tratamiento") or "") if x)
            partes.append(f"  - {nombre}" + (f" — {nota}" if nota else ""))
        partes.append("")
    partes += ["## Descripción del flujo actual", ""]
    partes += [f"{n}. {e}" for n, e in enumerate(ficha.get("etapas") or [], 1)]
    partes += ["", ""]
    return "\n".join(partes)
