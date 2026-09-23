"""Registro permanente para el tablero de Simplificación: `tablero.jsonl`.

Una línea JSON por trámite, escrita al extraer (`POST /expedientes`), con
SOLO agregados: nunca valores de catálogo, textos de plantilla, condiciones,
adjuntos ni el sid. Vive en el almacén de sesiones pero `_purgar_sesiones`
no lo toca (solo borra carpetas con nombre de sesión). La identidad es
`planeacion.registro.clave(nombre)`: el mismo trámite reemplaza su línea.
"""

import json
import logging
import os
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
# La fila «Vista de solo lectura (Origen → Destino)» del Diccionario es de tipo
# N/A y nombra una pantalla; el extractor la clasifica como archivo por el
# «visor de archivos», pero no es un documento que entregue el ciudadano.
_NO_ES_REQUISITO = ("vista de solo lectura",)


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
        if r.lower().startswith(_NO_ES_REQUISITO):
            continue
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
        # Rotulo humano de cada campo (solo si difiere del nombre tecnico): el
        # tablero enseña «CURP del propietario», no `curp_propietario`.
        "etiquetas": {c.nombre.lstrip("@"): c.etiqueta for c in campos
                      if c.etiqueta and c.etiqueta != c.nombre},
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
        # Una linea de un esquema anterior o editada a mano no puede tumbar
        # el endpoint entero: se exige lo minimo que `agregar` va a usar.
        if not _bien_formada(d):
            log.warning("tablero.jsonl: linea %d sin clave, nombre o fecha valida, se salta", n)
            continue
        salida.append(d)
    return salida


def _bien_formada(d) -> bool:
    if not isinstance(d, dict) or not d.get("clave") or not d.get("nombre"):
        return False
    try:
        datetime.fromisoformat(str(d.get("registrado", "")))
    except ValueError:
        return False
    return True


def _escribir(raiz: Path, lineas: "list[dict]") -> bool:
    """Reescribe el archivo entero de forma atomica (temporal + os.replace):
    un corte a mitad de escritura deja el archivo anterior, no uno vacio.
    Nunca propaga un error: el tablero es un registro lateral y su fallo no
    debe tumbar la extraccion ni dejar una sesion a medias."""
    destino = raiz / ARCHIVO
    temporal = raiz / (ARCHIVO + ".tmp")
    try:
        temporal.write_text(
            "".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lineas),
            encoding="utf-8",
        )
        os.replace(temporal, destino)
        return True
    except OSError:
        log.exception("tablero.jsonl: no se pudo escribir el registro")
        try:
            temporal.unlink()
        except OSError:
            pass
        return False


def registrar(raiz: Path, linea: dict) -> bool:
    """Escribe `linea` reemplazando la de la misma clave. Devuelve False si no
    se pudo escribir (ya quedo en el log).

    Es leer-modificar-escribir sin candado. No hay carrera porque el asistente
    corre en un solo proceso de uvicorn y los handlers son `async def` sobre
    el mismo loop (igual que `reconocidos.json` y `huecos.json`). Si algun dia
    se sirve con `--workers > 1`, hay que serializar este archivo, o un
    proceso pisaria la linea que otro acaba de escribir.
    """
    lineas = [l for l in leer(raiz) if l["clave"] != linea["clave"]]
    lineas.append(linea)
    return _escribir(raiz, lineas)


def actualizar_rotulos(raiz: Path, linea: dict) -> bool:
    """Corrige nombre, dependencia y homoclave de una linea ya registrada y
    conserva todo lo demas (huecos, metricas, fecha). Sin AS-IS el manifiesto
    nace con dependencia «[por confirmar]» y el analista la resuelve despues,
    en el orden que quiera. Devuelve False si la clave no estaba."""
    lineas = leer(raiz)
    for l in lineas:
        if l["clave"] == linea["clave"]:
            for k in ("nombre", "dependencia", "homoclave"):
                l[k] = linea[k]
            return _escribir(raiz, lineas)
    return False


# --- agregados para GET /api/v1/tablero -------------------------------------

# Los nombres son los que emite estimador.py (`orden = {"Bajo", "Medio", "Complejo"}`).
_NIVELES = ("Complejo", "Medio", "Bajo")
_ORDEN_NIVEL = {n: i for i, n in enumerate(_NIVELES)}


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
    agrupando variantes por `clave()` y mostrando el primer nombre visto.

    `clave()` solo iguala acentos, mayúsculas y puntuación: «Identificación
    Oficial» e «identificacion oficial» son una; «identificación oficial
    vigente» es otra. Un calificativo no agrupa, a propósito: decidir que
    «vigente» o «(copia)» sobran es inferir, y aquí no se infiere."""
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
    if campo == "campos":
        etiqueta_de: dict = {}
        for l in lineas:
            for nombre, etiqueta in l.get("etiquetas", {}).items():
                etiqueta_de.setdefault(clave(nombre), etiqueta)
        for f in filas:
            f["etiqueta"] = etiqueta_de.get(clave(f["nombre"]), f["nombre"])
    filas.sort(key=lambda f: (-f["tramites"], f["nombre"].lower()))
    return filas


def _por_clave(lineas: "list[dict]", k: str) -> dict:
    return next(l for l in lineas if l["clave"] == k)


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
    requisitos = _conteo_por_tramite(lineas, "requisitos")
    total = len(lineas)
    # Matriz tramite x codigo (mapa de calor): filas en el orden de complejidad,
    # columnas en el de la lista de huecos, para que las dos vistas coincidan.
    codigos = [h["codigo"] for h in huecos]
    matriz_huecos = [[int(l.get("huecos", {}).get(c, 0)) for c in codigos]
                     for l in (_por_clave(lineas, x["clave"]) for x in complejidad)]
    # Matriz requisito x tramite (presencia): filas por frecuencia, columnas
    # como la complejidad. Se compara por clave() para agrupar variantes.
    nombres = [c["nombre"] for c in complejidad]
    matriz_requisitos = [
        [1 if clave(r["nombre"]) in {clave(x) for x in _por_clave(lineas, c["clave"]).get("requisitos", [])}
         else 0 for c in complejidad]
        for r in requisitos]
    metricas = [l.get("metricas", {}) for l in lineas]
    claves_metricas = ("tareas", "bifurcaciones", "vistas", "campos", "acciones", "integraciones")
    return {
        "indicadores": {
            "requisitos_distintos": len(requisitos),
            "promedio_campos": round(sum(len(l.get("campos", [])) for l in lineas) / total, 1) if total else 0.0,
            "promedio_huecos": round(sum(sum(int(n) for n in l.get("huecos", {}).values())
                                         for l in lineas) / total, 1) if total else 0.0,
            "con_integracion": sum(1 for l in lineas if l.get("catalogos")),
        },
        "matriz_huecos": {"filas": nombres, "columnas": codigos, "celdas": matriz_huecos,
                          "maximo": max((v for fila in matriz_huecos for v in fila), default=0)},
        "matriz_requisitos": {"filas": [r["nombre"] for r in requisitos], "columnas": nombres,
                              "celdas": matriz_requisitos},
        "niveles": [{"nivel": n, "tramites": sum(1 for l in lineas if l.get("nivel") == n)}
                    for n in _NIVELES],
        "metricas_max": {k: max((int(m.get(k, 0)) for m in metricas), default=0)
                         for k in claves_metricas},
        "total_tramites": len(lineas),
        "dependencias": [{"nombre": d, "tramites": n}
                         for d, n in sorted(deps.items(), key=lambda x: (-x[1], x[0]))],
        "ultimo_registro": max((l["registrado"] for l in lineas if l.get("registrado")),
                               default=None),
        "requisitos": requisitos,
        "campos_compartidos": _conteo_por_tramite(lineas, "campos", minimo=2),
        "huecos": huecos,
        "complejidad": complejidad,
        "catalogos": [{"clave": k, "proveedor": CATALOGOS[k].proveedor if k in CATALOGOS else k,
                       "descripcion": CATALOGOS[k].descripcion if k in CATALOGOS else "",
                       "tramites": n}
                      for k, n in sorted(cat.items(), key=lambda x: (-x[1], x[0]))],
        "actividad": [{"semana": s, "tramites": por_semana.get(s, 0)}
                      for s in _ultimas_semanas(hoy)],
    }
