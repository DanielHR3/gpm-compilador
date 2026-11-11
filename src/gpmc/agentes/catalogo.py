"""Catálogo de campos aprobados (spec 2026-11-11 «Fase 3 compacta»).

Los Diccionarios que el equipo ya aprobó repiten casi la mitad de sus campos
(CURP, folio, pago…). Aquí se juntan los que aparecen en dos o más trámites,
con las celdas tal como el equipo las escribió, para que el modelo los cite
por su `@@id` y el Compilador escriba la fila. Nunca se copia la columna de
ejemplos, que trae datos de casos reales, ni la condición de visibilidad, que
depende de los demás campos de cada trámite.
"""
import collections
import importlib.resources
import re
import unicodedata
from pathlib import Path
from typing import Optional

import yaml

from gpmc.extractores.diccionario import _celdas, _es_separador

COLUMNAS = ["Nombre del Campo", "Tipo de Dato", "Componente Sugerido", "Obligatorio",
            "Condición de Visibilidad", "Límite / Especificaciones", "Catálogo de Valores",
            "Descripción"]
# Columna canónica -> prefijos con que la titulan los Diccionarios de la wiki.
_ALIAS = {
    "Nombre del Campo": ("nombre del campo",),
    "Tipo de Dato": ("tipo de dato",),
    "Componente Sugerido": ("componente",),
    "Obligatorio": ("obligatorio",),
    "Límite / Especificaciones": ("limite",),
    "Catálogo de Valores": ("catalogo de valores",),
    "Descripción": ("descripcion",),
}
_ID = re.compile(r"`@@([a-z0-9_]+)`")
MINIMO_TRAMITES = 2
ARCHIVO = "campos.yaml"


def _plano(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip()


def _filas(texto: str):
    """(id, {columna canónica: celda}) por cada fila con `@@id` de cada tabla."""
    mapa = None
    for linea in texto.splitlines():
        if not linea.lstrip().startswith("|"):
            mapa = None
            continue
        celdas = _celdas(linea)
        if celdas and _plano(celdas[0]).startswith("nombre del campo"):
            mapa = {}
            for i, c in enumerate(celdas):
                for canon, alias in _ALIAS.items():
                    if _plano(c).startswith(alias):
                        mapa[i] = canon
            continue
        if mapa is None or _es_separador(linea):
            continue
        m = _ID.search(linea)
        if not m:
            continue
        fila = {}
        for i, c in enumerate(celdas):
            canon = mapa.get(i)
            if canon:
                valor = _ID.sub("", c).strip()
                if valor and _plano(valor) not in ("n/a", "-", "—"):
                    fila[canon] = valor
        if fila.get("Nombre del Campo"):
            yield m.group(1), fila


def construir(wiki: Path, minimo: int = MINIMO_TRAMITES) -> dict:
    """Recorre `Diccionario de Datos.md` bajo `wiki` y devuelve el catálogo.
    De cada columna se queda el valor más repetido entre los trámites."""
    vistos = collections.defaultdict(list)          # id -> [fila por trámite]
    for d in sorted(Path(wiki).rglob("Diccionario de Datos.md")):
        del_tramite = {}
        for cid, fila in _filas(d.read_text(encoding="utf-8", errors="ignore")):
            del_tramite.setdefault(cid, fila)
        for cid, fila in del_tramite.items():
            vistos[cid].append(fila)
    campos = {}
    for cid, filas in vistos.items():
        if len(filas) < minimo:
            continue
        celdas = {}
        for col in COLUMNAS:
            valores = collections.Counter(f[col] for f in filas if f.get(col))
            if valores:
                celdas[col] = valores.most_common(1)[0][0]
        campos[cid] = {"etiqueta": celdas["Nombre del Campo"], "tipo": celdas.get("Tipo de Dato", "Texto"),
                       "tramites": len(filas), "celdas": celdas}
    orden = sorted(campos, key=lambda c: (-campos[c]["tramites"], c))
    return {"version": 1, "campos": {c: campos[c] for c in orden}}


def guardar(catalogo: dict, ruta: Path) -> None:
    Path(ruta).write_text(yaml.safe_dump(catalogo, allow_unicode=True, sort_keys=False, width=1000),
                          encoding="utf-8")


def cargar(ruta: Optional[Path] = None) -> dict:
    """El catálogo versionado en el repo; vacío si aún no se ha construido."""
    try:
        texto = (Path(ruta).read_text(encoding="utf-8") if ruta else
                 importlib.resources.files("gpmc.agentes").joinpath("datos", ARCHIVO).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError):
        return {"version": 0, "campos": {}}
    return yaml.safe_load(texto) or {"version": 0, "campos": {}}


def fila(catalogo: dict, cid: str) -> list:
    """Las ocho celdas de un campo del catálogo, con su `@@id` en la descripción."""
    celdas = catalogo["campos"][cid]["celdas"]
    f = [celdas.get(col, "") for col in COLUMNAS]
    f[4] = ""                                        # la visibilidad es de cada trámite
    f[6] = f[6] or "N/A"
    f[7] = f"{f[7]} `@@{cid}`".strip()
    return f


def _celda(t: str) -> str:
    return str(t).replace("|", "/").replace("\n", " ").strip()   # el extractor no lee «\\|»


def diccionario_markdown(tramite: str, pantallas: list) -> str:
    """`pantallas`: [(actor, nombre, [fila de ocho celdas])] -> el Diccionario
    en la forma que lee `extractores.diccionario`."""
    partes = [f"# Diccionario de Datos — {tramite}", "", "## Sección 1 — Pantallas", ""]
    for n, (actor, nombre, filas) in enumerate(pantallas, 1):
        partes += [f"### Pantalla {n} — {actor.upper()} — {nombre}", "",
                   "| " + " | ".join(COLUMNAS) + " |", "| " + " | ".join(["---"] * len(COLUMNAS)) + " |"]
        partes += ["| " + " | ".join(_celda(c) for c in f) + " |" for f in filas]
        partes.append("")
    return "\n".join(partes)


def para_el_modelo(catalogo: dict) -> str:
    """Una línea por campo, lo mínimo para que el modelo lo reconozca."""
    return "\n".join(f"@@{cid} · {c['etiqueta']} · {c['tipo']}" for cid, c in catalogo["campos"].items())


# --- Recuperación: solo lo que toca al trámite (idea de ARGUS, Jiang et al. 2025) ---
# Léxica y local a propósito: sin embeddings ni red, y reproducible en pruebas.
UNIVERSAL = 8            # campos presentes en tantos trámites viajan siempre
MAXIMO = 60
_VACIAS = {"para", "como", "este", "esta", "tipo", "dato", "datos", "numero", "nombre", "fecha",
           "documento", "campo", "campos", "sobre", "desde", "hasta", "entre", "tramite"}


def _palabras(t: str) -> set:
    return {p[:6] for p in re.findall(r"[a-z]{4,}", _plano(t)) if p not in _VACIAS}


def relevantes(catalogo: dict, as_is: str, maximo: int = MAXIMO) -> dict:
    """El subconjunto del catálogo que vale la pena enseñarle al modelo para
    este AS-IS: los universales y los que comparten palabras con el texto."""
    texto = _palabras(as_is)
    puntuados = []
    for cid, c in catalogo["campos"].items():
        propias = _palabras(c["etiqueta"]) | _palabras(cid.replace("_", " "))
        toca = len(propias & texto) / len(propias) if propias else 0.0
        if c["tramites"] >= UNIVERSAL or toca >= 0.5:
            puntuados.append((-(c["tramites"] >= UNIVERSAL), -toca, -c["tramites"], cid))
    elegidos = [cid for *_, cid in sorted(puntuados)[:maximo]]
    return {"version": catalogo.get("version"), "campos": {c: catalogo["campos"][c] for c in elegidos}}
