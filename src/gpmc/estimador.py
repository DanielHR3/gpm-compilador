"""Estima la complejidad de un tramite y su tiempo de ciclo.

La escala proviene de `medicion_tiempos_modelado_gpm.md` de la DGT, que midio
un solo tramite (ID 848, Busqueda de Disposicion Testamentaria) en 14-16 dias
habiles y proyecto los otros dos niveles a partir de esa linea base.

La tabla es AMBIGUA para un clasificador automatico: el tramite medido tiene
una integracion API. Cinco de los seis criterios lo ubican en "Bajo" (que es
lo que se midio), pero la fila "Medio" describe "1-2 integraciones API". La
fila "Bajo" habla de "sin interconexiones entre tramites", que no es lo mismo.

Por eso las metricas se reportan siempre —son conteos exactos— y el nivel solo
como sugerencia marcada como no calibrada.
"""

from dataclasses import dataclass, field

from gpmc.nucleo.manifiesto import Manifiesto

ADVERTENCIA = (
    "Escala NO calibrada: solo el nivel 'Bajo' esta respaldado por una medicion "
    "real (1 tramite). Los otros dos son proyecciones del documento de origen, y "
    "la tabla es ambigua para tramites con integraciones API."
)


@dataclass
class Metricas:
    tareas: int
    bifurcaciones: int
    vistas: int
    campos: int
    acciones: int
    integraciones: int


@dataclass
class Estimacion:
    metricas: Metricas
    nivel: str
    dias: str
    motivos: list[str] = field(default_factory=list)
    calibrado: bool = False
    advertencia: str = ADVERTENCIA


def estimar(m: Manifiesto) -> Estimacion:
    met = Metricas(
        tareas=len(m.flujo.tareas),
        bifurcaciones=sum(1 for c in m.flujo.conexiones if c.cuando),
        vistas=len(m.pantallas),
        campos=sum(len(p.campos) for p in m.pantallas),
        acciones=len(m.acciones),
        integraciones=sum(
            1 for p in m.pantallas for c in p.campos if c.origen
        ),
    )

    motivos: list[str] = []
    nivel, dias = "Bajo", "14 a 16 dias habiles"

    def subir(a, d, motivo):
        nonlocal nivel, dias
        orden = {"Bajo": 0, "Medio": 1, "Complejo": 2}
        if orden[a] > orden[nivel]:
            nivel, dias = a, d
        motivos.append(motivo)

    if met.tareas > 8:
        subir("Complejo", "40 a 50 dias habiles", f"{met.tareas} tareas (>8)")
    elif met.tareas > 5:
        subir("Medio", "25 a 30 dias habiles", f"{met.tareas} tareas (5-8)")

    if met.vistas > 12:
        subir("Complejo", "40 a 50 dias habiles", f"{met.vistas} vistas (>12)")
    elif met.vistas > 7:
        subir("Medio", "25 a 30 dias habiles", f"{met.vistas} vistas (8-12)")

    if met.campos > 60:
        subir("Complejo", "40 a 50 dias habiles", f"{met.campos} campos (>60)")
    elif met.campos > 30:
        subir("Medio", "25 a 30 dias habiles", f"{met.campos} campos (30-60)")

    if met.acciones > 6:
        subir("Complejo", "40 a 50 dias habiles", f"{met.acciones} acciones PHP (>6)")
    elif met.acciones > 3:
        subir("Medio", "25 a 30 dias habiles", f"{met.acciones} acciones PHP (4-6)")

    if met.integraciones > 2:
        subir("Complejo", "40 a 50 dias habiles",
              f"{met.integraciones} integraciones API (>2)")
    elif met.integraciones >= 1:
        motivos.append(
            f"{met.integraciones} integracion(es) API — criterio AMBIGUO en la tabla de "
            "origen: la fila 'Medio' las describe, pero el tramite medido en 14-16 dias "
            "tenia una. No se sube de nivel por este solo criterio."
        )

    if not motivos:
        motivos.append("todos los criterios dentro del nivel Bajo")

    return Estimacion(metricas=met, nivel=nivel, dias=dias, motivos=motivos)
