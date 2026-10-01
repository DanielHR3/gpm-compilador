"""Lee de la Propuesta TO-BE lo que el equipo escribio sobre el cambio.

El diagrama lo lee `mermaid.py`. Aqui va la prosa: los cambios concretos frente
al AS-IS, lo que se elimino, el impacto estimado y, si el equipo la escribe, la
tabla «Metricas del rediseño». Nada se reescribe: la comparativa enseña estos
puntos tal cual, porque son la palabra del equipo y no una cuenta del compilador.
"""
import re
from dataclasses import dataclass, field

from gpmc.extractores.as_is import PUNTO, titulo_de
from gpmc.planeacion.registro import clave

_ENC_CAMBIOS = re.compile(r"^(?:#+\s*|\*\*)Cambios concretos", re.I)
_ENC_ELIMINAR = re.compile(r"^(?:#+\s*|\*\*)Principio aplicado", re.I)
_ENC_IMPACTO = re.compile(r"^(?:#+\s*|\*\*)Impacto estimado", re.I)
_ENC_METRICAS = re.compile(r"^#+\s*M[eé]tricas del redise[nñ]o", re.I)
_ENC_ELIMINACION = re.compile(r"^#+\s*An[aá]lisis de eliminaci[oó]n", re.I)
_FILA = re.compile(r"^\s*\|(.+)\|\s*$")

# Como responde el equipo a «¿Se elimina?», medido en los TO-BE de la boveda y
# en los que escribe la Fase 3 (2026-10-01). La clase solo sirve para contar y
# colorear: en pantalla va siempre la celda tal como la escribio el equipo.
_CAMBIA = ("se integra", "se sustituye", "se reduce", "se flexibiliza", "se fusiona",
           "se automatiza", "se simplifica")
_SIN_DECISION = ("sin decision", "pendiente", "por confirmar")
_ES_REQUISITO = ("requisito",)
_ES_PASO = ("paso", "etapa")


@dataclass
class Punto:
    titulo: str
    texto: str


@dataclass
class Elemento:
    """Una fila de «Analisis de eliminacion por requisito y por paso»."""
    nombre: str
    decision: str
    fundamento: str = ""
    clase: str = "otro"
    tipo: str = ""


@dataclass
class Rediseno:
    cambios: list = field(default_factory=list)
    eliminaciones: list = field(default_factory=list)
    impacto: list = field(default_factory=list)
    declaradas: list = field(default_factory=list)
    elementos: list = field(default_factory=list)


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


def _empieza(k: str, prefijos: tuple) -> bool:
    return any(k == p or k.startswith(p + " ") for p in prefijos)


def clase_de_decision(decision: str) -> str:
    k = clave(decision)
    if not k or _empieza(k, _SIN_DECISION):
        return "sin_decision"
    if _empieza(k, ("si",)):
        return "elimina"
    if _empieza(k, ("no", "se conserva")):
        return "conserva"
    if _empieza(k, _CAMBIA):
        return "cambia"
    # Una respuesta que no se reconoce no se fuerza a ninguna clase: contarla
    # como eliminada o como conservada seria inventar la decision del equipo.
    return "otro"


def _tipo_de_elemento(nombre: str) -> str:
    k = clave(nombre)
    primera = k.split(" ", 1)[0].rstrip("s") if k else ""
    if primera in _ES_REQUISITO:
        return "requisito"
    return "paso" if primera in _ES_PASO else ""


def _sin_negrita(celda: str) -> str:
    return celda.replace("**", "").strip()


def _elementos(lineas: list) -> list:
    """La primera tabla bajo «Analisis de eliminacion…». Exige la columna
    «¿Se elimina?»: sin ese encabezado no se adivina cual es la decision."""
    salida, dentro, columnas = [], False, None
    for linea in lineas:
        if not dentro:
            dentro = bool(_ENC_ELIMINACION.match(linea))
            continue
        if linea.startswith("#"):
            break
        m = _FILA.match(linea)
        if not m:
            if columnas is not None:
                break
            continue
        celdas = [_sin_negrita(c) for c in m.group(1).split("|")]
        if columnas is None:
            claves = [clave(c) for c in celdas]
            decision = next((i for i, k in enumerate(claves) if "se elimina" in k), None)
            if decision is None:
                return []
            fundamento = next((i for i, k in enumerate(claves) if "fundamento" in k), None)
            columnas = (decision, fundamento)
            continue
        if set(celdas[0]) <= set("-: "):
            continue
        decision, fundamento = columnas
        if not celdas[0] or decision >= len(celdas):
            continue
        salida.append(Elemento(
            nombre=celdas[0], decision=celdas[decision],
            fundamento=celdas[fundamento] if fundamento is not None
            and fundamento < len(celdas) else "",
            clase=clase_de_decision(celdas[decision]),
            tipo=_tipo_de_elemento(celdas[0])))
    return salida


def extraer(texto: str) -> Rediseno:
    lineas = (texto or "").splitlines()
    cambios = _lista_tras(lineas, _ENC_CAMBIOS)
    return Rediseno(
        cambios=cambios,
        # Solo lo que el equipo puso bajo «Principio aplicado: eliminar». Buscar
        # «elimin» en los cambios listaba como eliminado lo que se AÑADIO
        # («Autocompletado… elimina la captura»): revision del 2026-09-28.
        eliminaciones=_lista_tras(lineas, _ENC_ELIMINAR),
        impacto=_lista_tras(lineas, _ENC_IMPACTO),
        declaradas=_declaradas(lineas),
        elementos=_elementos(lineas),
    )
