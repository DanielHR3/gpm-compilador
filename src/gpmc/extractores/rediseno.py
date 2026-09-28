"""Lee de la Propuesta TO-BE lo que el equipo escribio sobre el cambio.

El diagrama lo lee `mermaid.py`. Aqui va la prosa: los cambios concretos frente
al AS-IS, lo que se elimino, el impacto estimado y, si el equipo la escribe, la
tabla «Metricas del rediseño». Nada se reescribe: la comparativa enseña estos
puntos tal cual, porque son la palabra del equipo y no una cuenta del compilador.
"""
import re
from dataclasses import dataclass, field

from gpmc.extractores.as_is import PUNTO, titulo_de

_ENC_CAMBIOS = re.compile(r"^(?:#+\s*|\*\*)Cambios concretos", re.I)
_ENC_ELIMINAR = re.compile(r"^(?:#+\s*|\*\*)Principio aplicado", re.I)
_ENC_IMPACTO = re.compile(r"^(?:#+\s*|\*\*)Impacto estimado", re.I)
_ENC_METRICAS = re.compile(r"^#+\s*M[eé]tricas del redise[nñ]o", re.I)
_FILA = re.compile(r"^\s*\|(.+)\|\s*$")
_ELIMINA = re.compile(r"elimin", re.I)


@dataclass
class Punto:
    titulo: str
    texto: str


@dataclass
class Rediseno:
    cambios: list = field(default_factory=list)
    eliminaciones: list = field(default_factory=list)
    impacto: list = field(default_factory=list)
    declaradas: list = field(default_factory=list)


def _lista_tras(lineas: list, encabezado) -> list:
    """Los puntos de primer nivel que siguen a `encabezado`. Un parrafo o una
    cita antes del primer punto es la introduccion y se salta; despues del
    primer punto, cualquier cosa que no sea punto cierra la lista."""
    salida, dentro = [], False
    for linea in lineas:
        if not dentro:
            dentro = bool(encabezado.match(linea))
            continue
        if not linea.strip():
            continue
        m = PUNTO.match(linea)
        if m:
            if not linea[:1].isspace():
                salida.append(Punto(titulo_de(m.group(1)), m.group(1).strip()))
            continue
        if linea.startswith("#") or linea.startswith("**") or salida:
            break
    return salida


def _declaradas(lineas: list) -> list:
    filas, dentro = [], False
    for linea in lineas:
        if not dentro:
            dentro = bool(_ENC_METRICAS.match(linea))
            continue
        if linea.startswith("#"):
            break
        m = _FILA.match(linea)
        if not m:
            continue
        celdas = [c.strip() for c in m.group(1).split("|")]
        if len(celdas) < 3 or not celdas[0]:
            continue
        if set(celdas[0]) <= set("-: "):
            continue
        if celdas[0].lower() in ("métrica", "metrica"):
            continue
        filas.append((celdas[0], celdas[1], celdas[2]))
    return filas


def extraer(texto: str) -> Rediseno:
    lineas = (texto or "").splitlines()
    cambios = _lista_tras(lineas, _ENC_CAMBIOS)
    eliminaciones = _lista_tras(lineas, _ENC_ELIMINAR)
    vistos = {p.texto for p in eliminaciones}
    eliminaciones += [p for p in cambios
                      if _ELIMINA.search(p.texto) and p.texto not in vistos]
    return Rediseno(
        cambios=cambios,
        eliminaciones=eliminaciones,
        impacto=_lista_tras(lineas, _ENC_IMPACTO),
        declaradas=_declaradas(lineas),
    )
