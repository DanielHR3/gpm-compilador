"""Mide el generador de la Fase 3 contra expedientes con respuesta humana.

Sin segundo modelo: se generan los dos documentos desde el AS-IS y se comparan
con el Diccionario y el TO-BE que escribio el equipo, por `clave()`. La semilla
es el script de usar y tirar del 2026-09-23.
"""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from gpmc.agentes.fase3 import extraer_borradores, generar
from gpmc.agentes.prompt_fase3 import NOMBRE_EJEMPLO
from gpmc.extractores.expediente import _buscar_insumo, _leer, extraer_expediente
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.planeacion.registro import clave

_CLAVES_INSUMO = (["Análisis AS-IS", "AS IS"], ["Propuesta TO-BE", "TO BE"],
                  ["Diccionario de Datos", "Diccionario"])


class Medida(BaseModel):
    expediente: str
    estado: str
    campos_humano: int = 0
    campos_casan: int = 0
    requisitos_humano: int = 0
    requisitos_casan: int = 0
    tareas_humano: int = 0
    tareas_casan: int = 0
    compuertas_con_regla: int = 0
    # Medida estructural (2026-09-25): «tareas que casan» compara por nombre y
    # el modelo bautiza distinto que el equipo; esto dice si la FORMA es la
    # misma aunque los nombres no.
    pantallas_humano: int = 0
    pantallas_generadas: int = 0
    compuertas_humano: int = 0
    compuertas_generadas: int = 0
    ciclo_humano: bool = False
    ciclo_generado: bool = False
    huecos: dict = {}


def _compuertas(m: Optional[Manifiesto]) -> int:
    """Tareas de las que sale mas de una conexion con condicion."""
    if m is None:
        return 0
    origenes = {}
    for c in m.flujo.conexiones:
        if c.cuando is not None:
            origenes[c.de] = origenes.get(c.de, 0) + 1
    return sum(1 for n in origenes.values() if n >= 1)


def _tiene_ciclo(m: Optional[Manifiesto]) -> bool:
    """Alguna conexion desde cuyo destino se vuelve a su origen (la vuelta
    correccion -> revision)."""
    if m is None:
        return False
    salientes = {}
    for c in m.flujo.conexiones:
        salientes.setdefault(c.de, set()).add(c.a)

    def alcanza(desde, hasta):
        vistos, pila = set(), [desde]
        while pila:
            n = pila.pop()
            if n == hasta:
                return True
            if n not in vistos:
                vistos.add(n)
                pila += salientes.get(n, ())
        return False

    return any(alcanza(c.a, c.de) for c in m.flujo.conexiones)


def _etiquetas(m: Optional[Manifiesto], solo_archivo: bool = False) -> set:
    if m is None:
        return set()
    return {clave(c.etiqueta or c.nombre) for p in m.pantallas for c in p.campos
            if not solo_archivo or c.tipo == "file"}


def _tareas(m: Optional[Manifiesto]) -> set:
    # Las que tienen pantalla: la sintetica «Tramite concluido» no cuenta, pero
    # en un flujo ramificado la ultima tarea real tambien es terminal.
    return set() if m is None else {clave(t.nombre) for t in m.flujo.tareas if t.pantallas}


def _casan(humano: set, generado: set) -> int:
    return sum(1 for h in humano if any(h == g or h in g or g in h for g in generado))


def medir_expediente(carpeta: Path, proveedor, raiz: Path) -> Medida:
    ruta_as_is, _ = _buscar_insumo(carpeta, _CLAVES_INSUMO[0])
    as_is = _leer(ruta_as_is)
    humano = extraer_expediente(carpeta).manifiesto
    med = Medida(expediente=carpeta.name, estado="",
                 campos_humano=len(_etiquetas(humano)),
                 requisitos_humano=len(_etiquetas(humano, solo_archivo=True)),
                 tareas_humano=len(_tareas(humano)),
                 pantallas_humano=0 if humano is None else len(humano.pantallas),
                 compuertas_humano=_compuertas(humano), ciclo_humano=_tiene_ciclo(humano))
    if clave(carpeta.name) == clave(NOMBRE_EJEMPLO):
        med.estado = "ejemplo del prompt"      # se mediria contra si mismo
        return med
    g = generar(as_is, proveedor, raiz, "medir" + "0" * 11)
    med.estado = g.estado
    if g.estado != "listo":
        return med
    gen, huecos = extraer_borradores(as_is, g.diccionario.texto, g.tobe.texto)
    med.pantallas_generadas = 0 if gen is None else len(gen.pantallas)
    med.compuertas_generadas = _compuertas(gen)
    med.ciclo_generado = _tiene_ciclo(gen)
    med.campos_casan = _casan(_etiquetas(humano), _etiquetas(gen))
    med.requisitos_casan = _casan(_etiquetas(humano, True), _etiquetas(gen, True))
    med.tareas_casan = _casan(_tareas(humano), _tareas(gen))
    med.compuertas_con_regla = (0 if gen is None
                                else sum(1 for c in gen.flujo.conexiones if c.cuando is not None))
    for h in huecos:
        med.huecos[h.nivel] = med.huecos.get(h.nivel, 0) + 1
    return med


def medir_carpeta(carpeta: Path, proveedor, raiz: Path) -> list:
    """Recorre recursivamente: la boveda de Simplificacion guarda cada tramite
    en `<analista>/<dependencia>/<tramite>/`. Solo entra un tramite con los
    tres documentos resueltos sin ambiguedad (una copia «- copia.md» al lado
    hace que `_buscar_insumo` no elija, y aqui tampoco se elige)."""
    raiz.mkdir(parents=True, exist_ok=True)
    medidas = []
    for d in sorted(p for p in Path(carpeta).rglob("*") if p.is_dir() and not p.name.startswith(".")):
        if not all(_buscar_insumo(d, k)[0] is not None for k in _CLAVES_INSUMO):
            continue      # sin respuesta humana (o con dos candidatos) no hay contra que medir
        medidas.append(medir_expediente(d, proveedor, raiz))
    return medidas


def imprimir(medidas: list) -> str:
    # gen/humano en pant., comp. y ciclo: la forma, aparte de los nombres.
    filas = [f"{'expediente':40} {'campos':>8} {'requis.':>8} {'tareas':>8} "
             f"{'pant.':>7} {'comp.':>6} {'ciclo':>6} "
             f"{'reglas':>7} {'bloq.':>6} {'falta':>6} {'conf.':>6}"]
    for m in medidas:
        if m.estado != "listo":
            filas.append(f"{m.expediente[:40]:40} {m.estado}")
            continue
        filas.append(
            f"{m.expediente[:40]:40} "
            f"{f'{m.campos_casan}/{m.campos_humano}':>8} "
            f"{f'{m.requisitos_casan}/{m.requisitos_humano}':>8} "
            f"{f'{m.tareas_casan}/{m.tareas_humano}':>8} "
            f"{f'{m.pantallas_generadas}/{m.pantallas_humano}':>7} "
            f"{f'{m.compuertas_generadas}/{m.compuertas_humano}':>6} "
            f"{('S' if m.ciclo_generado else 'N') + '/' + ('S' if m.ciclo_humano else 'N'):>6} "
            f"{m.compuertas_con_regla:>7} {m.huecos.get('bloqueante', 0):>6} "
            f"{m.huecos.get('falta_dato', 0):>6} {m.huecos.get('por_confirmar', 0):>6}")
    return "\n".join(filas)
