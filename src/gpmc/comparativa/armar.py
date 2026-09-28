"""Cruza el AS-IS con el TO-BE y el manifiesto: la comparativa de antes y despues.

La pidio Simplificacion el 2026-09-28 para comprobar que un tramite si tuvo
reingenieria. Es una funcion pura y determinista: no hay un modelo opinando.
Cada valor dice de donde salio (contado, leido, declarado o sin dato), porque
una cifra sin origen no sirve de evidencia.
"""
import dataclasses
import re
from dataclasses import dataclass, field
from typing import Optional

from gpmc.extractores.as_is import EstadoActual, casa
from gpmc.extractores.rediseno import Rediseno
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.planeacion.registro import clave

METRICAS = (
    ("requisitos", "Requisitos documentales"),
    ("pasos", "Pasos del proceso"),
    ("actores", "Actores que intervienen"),
    ("sistemas", "Sistemas externos"),
    ("tiempo", "Tiempo de respuesta"),
    ("visitas", "Visitas presenciales"),
    ("capturas", "Capturas manuales del mismo dato"),
)
_NOMBRES = dict(METRICAS)
# Como nombra el equipo cada metrica en su «Presentacion Antes y Despues».
_RAICES = (("requisit", "requisitos"), ("paso", "pasos"), ("actor", "actores"),
           ("sistema", "sistemas"), ("tiempo", "tiempo"), ("visita", "visitas"),
           ("captura", "capturas"))
_CANTIDAD = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(.*?)\s*$")
# Mismas dos reglas del tablero (`web/tablero.py`): el prefijo no es parte del
# requisito y la fila de solo lectura no es un documento que entregue nadie.
_PREFIJO_DOC = "documento:"
_NO_ES_REQUISITO = "vista de solo lectura"


@dataclass
class Valor:
    texto: str = ""
    numero: Optional[float] = None
    unidad: str = ""
    origen: str = "sin_dato"


@dataclass
class Metrica:
    clave: str
    nombre: str
    antes: Valor
    despues: Valor
    diferencia: Optional[float] = None
    porcentaje: Optional[float] = None


@dataclass
class Requisito:
    nombre: str
    destino: str
    fundamento: str = ""


@dataclass
class Comparativa:
    disponible: bool = True
    motivo: str = ""
    tramite: str = ""
    metricas: list = field(default_factory=list)
    requisitos: list = field(default_factory=list)
    pasos_antes: list = field(default_factory=list)
    tareas_despues: list = field(default_factory=list)
    fricciones: list = field(default_factory=list)
    cambios: list = field(default_factory=list)
    eliminaciones: list = field(default_factory=list)
    impacto: list = field(default_factory=list)
    autollenados: int = 0
    porcentaje_global: Optional[float] = None
    base_global: int = 0
    total_metricas: int = len(METRICAS)
    veredicto: str = "sin_medida"
    frase: str = ""
    huecos: list = field(default_factory=list)


def clave_de_metrica(nombre: str) -> Optional[str]:
    k = clave(nombre)
    for raiz, c in _RAICES:
        if raiz in k:
            return c
    return None


def _valor(texto: str, origen: str) -> Valor:
    t = (texto or "").strip()
    if not t:
        return Valor()
    m = _CANTIDAD.match(t)
    if not m:
        return Valor(texto=t, origen=origen)
    return Valor(texto=t, numero=float(m.group(1).replace(",", ".")),
                 unidad=clave(m.group(2)), origen=origen)


def _contado(n: int) -> Valor:
    return Valor(texto=str(n), numero=float(n), origen="contado")


def _contado_si_hay(lista: list) -> Valor:
    # Una lista vacia es «no se leyo», no «hay cero»: el AS-IS pudo traerla en
    # una forma que el extractor no entiende.
    return _contado(len(lista)) if lista else Valor()


def _archivos(m: Manifiesto) -> list:
    salida, vistos = [], set()
    for p in m.pantallas:
        for c in p.campos:
            if c.tipo != "file":
                continue
            t = (c.etiqueta or c.nombre).strip()
            if t.lower().startswith(_PREFIJO_DOC):
                t = t[len(_PREFIJO_DOC):].strip()
            if not t or t.lower().startswith(_NO_ES_REQUISITO) or clave(t) in vistos:
                continue
            vistos.add(clave(t))
            salida.append(t)
    return salida


def _mezclar(rediseno: Rediseno, pantalla: Optional[dict]) -> dict:
    """Lo declarado, por clave y por lado. Gana la pantalla sobre el TO-BE:
    es lo ultimo que decidio una persona."""
    d = {}
    for nombre, antes, despues in rediseno.declaradas:
        k = clave_de_metrica(nombre)
        if k:
            d[k] = {"antes": antes.strip(), "despues": despues.strip()}
    for k, v in (pantalla or {}).items():
        if k not in _NOMBRES or not isinstance(v, dict):
            continue
        previo = d.get(k, {"antes": "", "despues": ""})
        d[k] = {lado: str(v.get(lado) or "").strip() or previo[lado]
                for lado in ("antes", "despues")}
    return d


def _metrica(k: str, antes: Valor, despues: Valor, declarado: dict) -> Metrica:
    if declarado.get("antes"):
        antes = _valor(declarado["antes"], "declarado")
    if declarado.get("despues"):
        despues = _valor(declarado["despues"], "declarado")
    dif = pct = None
    if (antes.numero is not None and despues.numero is not None
            and antes.unidad == despues.unidad):
        dif = antes.numero - despues.numero
        if antes.numero > 0:
            pct = round(dif / antes.numero * 100, 1)
    return Metrica(k, _NOMBRES[k], antes, despues, dif, pct)


def _requisitos(estado: EstadoActual, archivos: list, eliminaciones: list) -> list:
    if not estado.requisitos:
        return []
    salida, usados = [], set()
    for req in estado.requisitos:
        casados = [a for a in archivos if casa(req, a)]
        if casados:
            usados.update(casados)
            salida.append(Requisito(req, "conservado", casados[0]))
            continue
        k = clave(req)
        fundamento = next((p.texto for p in eliminaciones if k and k in clave(p.texto)), "")
        # Sin una linea del equipo que lo nombre, el compilador no sabe si se
        # elimino o se olvido: «sin destino», nunca «eliminado» por omision.
        salida.append(Requisito(req, "eliminado" if fundamento else "sin_destino", fundamento))
    salida += [Requisito(a, "nuevo") for a in archivos if a not in usados]
    return salida


def _cifra(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n).replace(".", ",")


def texto_cambio(pct: float) -> str:
    return f"{'−' if pct >= 0 else '+'}{_cifra(abs(pct))} %"


_CABEZA = {
    "reduce": "La reingeniería reduce",
    "mixto": "La reingeniería reduce unas métricas y aumenta otras",
    "no_reduce": "La reingeniería no reduce ninguna métrica medida",
}


def _veredicto(metricas: list) -> tuple:
    comparables = [m for m in metricas if m.porcentaje is not None]
    total = len(METRICAS)
    if len(comparables) < 2:
        return ("sin_medida", None, len(comparables),
                f"No se puede medir: solo {len(comparables)} de {total} métricas tienen "
                f"número en los dos lados. Declara las que faltan.")
    pct = round(sum(m.porcentaje for m in comparables) / len(comparables), 1)
    bajan = any(m.porcentaje > 0 for m in comparables)
    suben = any(m.porcentaje < 0 for m in comparables)
    veredicto = "mixto" if bajan and suben else "reduce" if bajan else "no_reduce"
    partes = "; ".join(
        f"{m.nombre.lower()} de {m.antes.texto} a {m.despues.texto} ({texto_cambio(m.porcentaje)})"
        for m in comparables)
    frase = (f"{_CABEZA[veredicto]}: {partes}. Simplificación global: "
             f"{_cifra(pct)} % sobre {len(comparables)} de {total} métricas.")
    return veredicto, pct, len(comparables), frase


def _huecos(estado: EstadoActual, metricas: list, requisitos: list, veredicto: str) -> list:
    huecos = []
    if not estado.pasos:
        huecos.append(Hueco("por_confirmar", "CMP-01", "as_is",
                            "El AS-IS no trae una lista de pasos que se pueda leer: "
                            "los pasos de antes no se cuentan."))
    faltan = [m.nombre for m in metricas if m.despues.origen == "sin_dato"]
    if faltan:
        huecos.append(Hueco("por_confirmar", "CMP-02", "to_be",
                            "Falta el dato del después para: " + ", ".join(faltan) + "."))
    if veredicto == "no_reduce":
        huecos.append(Hueco("por_confirmar", "CMP-03", "to_be",
                            "La reingeniería no reduce ninguna de las métricas medidas."))
    sueltos = [r.nombre for r in requisitos if r.destino == "sin_destino"]
    if sueltos:
        huecos.append(Hueco("por_confirmar", "CMP-04", "to_be",
                            "Requisitos del AS-IS que el TO-BE no conserva ni dice que "
                            "elimina: " + ", ".join(f"«{s}»" for s in sueltos) + "."))
    return huecos


def no_disponible(motivo: str) -> Comparativa:
    return Comparativa(disponible=False, motivo=motivo)


def comparar(estado: EstadoActual, rediseno: Rediseno, m: Manifiesto,
             declaradas: Optional[dict] = None) -> Comparativa:
    d = _mezclar(rediseno, declaradas)
    archivos = _archivos(m)
    actores = {t.actor for t in m.flujo.tareas if t.actor} or {p.actor for p in m.pantallas}
    base = {
        "requisitos": (_contado_si_hay(estado.requisitos), _contado(len(archivos))),
        "pasos": (_contado_si_hay(estado.pasos), _contado(len(m.flujo.tareas))),
        "actores": (Valor(), _contado(len(actores))),
        "sistemas": (_contado_si_hay(estado.sistemas), Valor()),
        "tiempo": (_valor(estado.tiempo, "leido"), Valor()),
        "visitas": (Valor(), Valor()),
        "capturas": (Valor(), Valor()),
    }
    metricas = [_metrica(k, base[k][0], base[k][1], d.get(k, {})) for k, _ in METRICAS]
    requisitos = _requisitos(estado, archivos, rediseno.eliminaciones)
    veredicto, pct, n, frase = _veredicto(metricas)
    return Comparativa(
        tramite=m.tramite.nombre,
        metricas=metricas,
        requisitos=requisitos,
        pasos_antes=list(estado.pasos),
        tareas_despues=[{"nombre": t.nombre, "actor": t.actor or ""} for t in m.flujo.tareas],
        fricciones=list(estado.fricciones),
        cambios=[p.titulo for p in rediseno.cambios],
        eliminaciones=[p.titulo for p in rediseno.eliminaciones],
        impacto=[p.titulo for p in rediseno.impacto],
        autollenados=sum(len(c.autollena) for p in m.pantallas for c in p.campos),
        porcentaje_global=pct,
        base_global=n,
        veredicto=veredicto,
        frase=frase,
        huecos=_huecos(estado, metricas, requisitos, veredicto),
    )


def a_dict(c: Comparativa) -> dict:
    return dataclasses.asdict(c)
