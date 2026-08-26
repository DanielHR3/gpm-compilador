"""Proyecta cuanto tomara un lote de tramites, a partir de lo ya medido.

Existe para que quien planea no comprometa fechas imposibles. Por eso toda
salida lleva sus advertencias: una cifra sin ellas invita justo al error que
esta herramienta quiere evitar.
"""

from typing import Optional
import math
import statistics
from dataclasses import dataclass, field

from gpmc.planeacion.registro import Registro

# Medido por la DGT sobre el tramite mas sencillo del catalogo, con un recurso.
CICLO_DGT = (14, 16)
NOTA_DGT = (
    "A esto se suma el ciclo de la DGT: 14 a 16 dias habiles para convertir los "
    "insumos en un .gpm funcional. Son etapas consecutivas, no paralelas."
)


@dataclass
class Proyeccion:
    cantidad: int
    analistas: int
    mediana_dias: Optional[int]
    muestra: int
    muestra_viva: int
    parciales_excluidos: int
    dias_totales: Optional[int]
    dias_dgt: tuple = CICLO_DGT
    nota_dgt: str = NOTA_DGT
    advertencias: list[str] = field(default_factory=list)


def proyectar(reg: Registro, cantidad: int, analistas: int = 1) -> Proyeccion:
    todos_cerrados = [e for e in reg.todos() if not e.abierto]
    # Solo los expedientes que llegaron a los entregables de fondo sirven para
    # planear. Incluir los recien abiertos hunde la mediana y lleva justo al
    # error que esta herramienta existe para evitar.
    cerrados = [e for e in todos_cerrados if e.completo]
    parciales = len(todos_cerrados) - len(cerrados)
    vivos = [e for e in cerrados if e.origen == "vivo"]
    avisos: list[str] = []

    if not cerrados:
        motivo = (
            f"Ninguno de los {len(todos_cerrados)} expedientes cerrados esta completo "
            "(5 de 6 entregables o mas). Un expediente parcial no es un ciclo rapido: "
            "es un ciclo sin terminar de medir."
            if todos_cerrados else
            "Sin expedientes cerrados no hay base para proyectar."
        )
        return Proyeccion(
            cantidad=cantidad, analistas=analistas, mediana_dias=None,
            muestra=0, muestra_viva=0, parciales_excluidos=parciales,
            dias_totales=None,
            advertencias=[motivo + " Registrar el cierre de al menos tres expedientes "
                          "completos antes de comprometer fechas."],
        )

    dias = [e.dias for e in cerrados]
    mediana = int(statistics.median(dias))
    analistas = max(1, analistas)
    totales = math.ceil(cantidad / analistas) * mediana

    avisos.append(
        "Los dias son naturales transcurridos, NO esfuerzo: los analistas trabajan "
        "varios expedientes en paralelo. Un expediente de 20 dias no ocupo 20 dias "
        "de una persona."
    )
    if len(cerrados) < 5:
        avisos.append(
            f"Muestra pequena ({len(cerrados)} expediente(s) cerrado(s)). La mediana "
            "es indicativa; recalibrar conforme se cierren mas."
        )
    if not vivos:
        avisos.append(
            "Toda la muestra proviene del frontmatter del wiki, que mide cuando se "
            "guardo un archivo, no cuando empezo el trabajo. Los expedientes medidos "
            "en vivo desde el nombre daran una cifra mas fiel."
        )
    elif len(vivos) < len(cerrados):
        avisos.append(
            f"{len(cerrados) - len(vivos)} de {len(cerrados)} expedientes de la muestra "
            "vienen del wiki y no de medicion en vivo."
        )
    if cantidad > 1 and analistas == 1:
        avisos.append(
            f"La proyeccion asume {analistas} analista y ejecucion secuencial. "
            "Con mas gente en paralelo baja de forma proporcional."
        )

    if parciales:
        avisos.append(
            f"Se excluyeron {parciales} expediente(s) parcial(es) de la muestra. "
            "Incluirlos bajaria la mediana artificialmente: no son ciclos rapidos, "
            "son ciclos sin terminar."
        )

    return Proyeccion(
        cantidad=cantidad, analistas=analistas, mediana_dias=mediana,
        muestra=len(cerrados), muestra_viva=len(vivos),
        parciales_excluidos=parciales, dias_totales=totales, advertencias=avisos,
    )
