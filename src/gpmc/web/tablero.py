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
from datetime import date, datetime, timedelta, timezone
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


# --- agregados para GET /api/v1/tablero -------------------------------------

_ORDEN_NIVEL = {"Alto": 0, "Medio": 1, "Bajo": 2}


def _semana(iso: str) -> str:
    y, w, _ = datetime.fromisoformat(iso).isocalendar()
    return f"{y}-W{w:02d}"


def _ultimas_semanas(hoy: date, n: int = 12) -> "list[str]":
    lunes = hoy - timedelta(days=hoy.weekday())
    salida = []
    for i in range(n - 1, -1, -1):
        y, w, _ = (lunes - timedelta(weeks=i)).isocalendar()
        salida.append(f"{y}-W{w:02d}")
    return salida


def _conteo_por_tramite(lineas: "list[dict]", campo: str, minimo: int = 1) -> "list[dict]":
    """Cuántos trámites traen cada valor de `campo` (lista de strings),
    agrupando variantes por `clave()` y mostrando el primer nombre visto."""
    total = len(lineas)
    cuenta: Counter = Counter()
    nombre_de: dict = {}
    for l in lineas:
        valores = [x for x in l.get(campo, []) if x]
        for k in {clave(x) for x in valores}:
            cuenta[k] += 1
        for x in valores:
            nombre_de.setdefault(clave(x), x)
    filas = [{"nombre": nombre_de[k], "tramites": c, "porcentaje": round(100 * c / total)}
             for k, c in cuenta.items() if c >= minimo]
    filas.sort(key=lambda f: (-f["tramites"], f["nombre"].lower()))
    return filas


def agregar(lineas: "list[dict]", dependencia: Optional[str] = None,
            hoy: Optional[date] = None) -> dict:
    """Las cuentas del tablero, listas para pintar. Nunca falla por vacío."""
    hoy = hoy or datetime.now(timezone.utc).date()
    if dependencia:
        lineas = [l for l in lineas if l.get("dependencia") == dependencia]
    deps = Counter(l.get("dependencia", "") for l in lineas)
    huecos_tramites: Counter = Counter()
    huecos_total: Counter = Counter()
    for l in lineas:
        for cod, n in l.get("huecos", {}).items():
            huecos_tramites[cod] += 1
            huecos_total[cod] += int(n)
    huecos = [{"codigo": c, "tramites": huecos_tramites[c], "total": huecos_total[c]}
              for c in huecos_tramites]
    # Por tramites y no por total: un expediente con cuarenta DIC-06 no debe
    # tapar a un codigo que sale en todos.
    huecos.sort(key=lambda h: (-h["tramites"], -h["total"], h["codigo"]))
    complejidad = [{"clave": l["clave"], "nombre": l["nombre"],
                    "dependencia": l.get("dependencia", ""), "nivel": l.get("nivel", ""),
                    "metricas": l.get("metricas", {})} for l in lineas]
    complejidad.sort(key=lambda c: (_ORDEN_NIVEL.get(c["nivel"], 9), c["nombre"].lower()))
    cat: Counter = Counter(k for l in lineas for k in l.get("catalogos", []))
    por_semana = Counter(_semana(l["registrado"]) for l in lineas if l.get("registrado"))
    return {
        "total_tramites": len(lineas),
        "dependencias": [{"nombre": d, "tramites": n}
                         for d, n in sorted(deps.items(), key=lambda x: (-x[1], x[0]))],
        "ultimo_registro": max((l["registrado"] for l in lineas if l.get("registrado")),
                               default=None),
        "requisitos": _conteo_por_tramite(lineas, "requisitos"),
        "campos_compartidos": _conteo_por_tramite(lineas, "campos", minimo=2),
        "huecos": huecos,
        "complejidad": complejidad,
        "catalogos": [{"clave": k, "tramites": n}
                      for k, n in sorted(cat.items(), key=lambda x: (-x[1], x[0]))],
        "actividad": [{"semana": s, "tramites": por_semana.get(s, 0)}
                      for s in _ultimas_semanas(hoy)],
    }
