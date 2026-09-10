"""Analisis estatico del flujo y precalculo de sus transiciones.

Sin entorno de pruebas separado del productivo, la unica forma de saber hoy si
un flujo funciona es importarlo a produccion. Este modulo detecta en la laptop
lo que ahi solo se veria despues.

El precalculo de transiciones existe para que el simulador no interprete
reglas por su cuenta: la autoridad sigue siendo nucleo/reglas.
"""

import json
from dataclasses import dataclass, field

from gpmc.nucleo import reglas
from gpmc.nucleo.manifiesto import Manifiesto


@dataclass
class Analisis:
    transiciones: dict = field(default_factory=dict)
    problemas: list[str] = field(default_factory=list)
    orden_captura: dict = field(default_factory=dict)


def _alcanzables(m: Manifiesto) -> set[str]:
    inicial = next((t.id for t in m.flujo.tareas if t.inicial), None)
    if inicial is None:
        return set()
    salidas: dict[str, list[str]] = {}
    for c in m.flujo.conexiones:
        salidas.setdefault(c.de, []).append(c.a)
    vistos, pila = set(), [inicial]
    while pila:
        actual = pila.pop()
        if actual in vistos:
            continue
        vistos.add(actual)
        pila.extend(salidas.get(actual, []))
    return vistos


def analizar(m: Manifiesto) -> Analisis:
    a = Analisis()
    campos_de_pantalla = {p.id: [c.nombre for c in p.campos] for p in m.pantallas}
    catalogo_de = {
        c.nombre: {o.valor for o in c.catalogo}
        for p in m.pantallas for c in p.campos if c.catalogo
    }

    # Orden en que cada campo queda capturado, siguiendo el orden de tareas.
    paso = 0
    for t in m.flujo.tareas:
        paso += 1
        for p in t.pantallas:
            for nombre in campos_de_pantalla.get(p.id, []):
                a.orden_captura.setdefault(nombre, paso)

    orden_tarea = {t.id: i for i, t in enumerate(m.flujo.tareas)}

    salidas: dict[str, list] = {}
    for c in m.flujo.conexiones:
        salidas.setdefault(c.de, []).append(c)

    for tid, conexiones in salidas.items():
        con_regla = [c for c in conexiones if c.cuando]
        if not con_regla:
            a.transiciones[tid] = {"campo": None, "destinos": {}, "siguiente": conexiones[0].a}
            continue

        # Campos que participan en cada rama (el campo base de `cuando` MAS
        # los de sus clausulas `y`), en el mismo orden en que `reglas.emitir`
        # los concatena con '&&' -- ese orden es lo que hace reproducible la
        # clave compuesta que arma `html.py` del lado del navegador.
        campos_por_rama = {
            id(c): tuple(reglas.campos_de(reglas.emitir(c.cuando))) for c in con_regla
        }
        conjuntos = {campos_por_rama[id(c)] for c in con_regla}
        if len(conjuntos) > 1:
            vistos = sorted({campo for conjunto in conjuntos for campo in conjunto})
            a.problemas.append(
                f"la tarea '{tid}' bifurca con conjuntos de campos distintos entre "
                f"sus ramas ({', '.join(vistos)}); el simulador solo recorre "
                "bifurcaciones consistentes y usa la primera rama como referencia"
            )
        campos_tarea = campos_por_rama[id(con_regla[0])]

        destinos = {}
        for c in con_regla:
            if campos_por_rama[id(c)] != campos_tarea:
                continue  # rama con otro conjunto de campos: ya se aviso arriba

            valores = {c.cuando.campo: c.cuando.igual}
            valores.update({cl.campo: cl.igual for cl in getattr(c.cuando, "y", [])})

            # Se usa el evaluador compartido, no una comparacion propia.
            if reglas.evaluar(reglas.emitir(c.cuando), valores):
                if len(campos_tarea) == 1:
                    destinos[valores[campos_tarea[0]]] = c.a
                else:
                    clave = json.dumps(
                        [valores[campo] for campo in campos_tarea],
                        separators=(",", ":"), ensure_ascii=False,
                    )
                    destinos[clave] = c.a

            for campo, valor in valores.items():
                valores_validos = catalogo_de.get(campo)
                if valores_validos and valor not in valores_validos:
                    a.problemas.append(
                        f"la tarea '{tid}' bifurca cuando '{campo}' vale '{valor}', pero ese "
                        f"valor no esta en su catalogo ({', '.join(sorted(valores_validos))}): "
                        "esa rama nunca se cumple"
                    )

                capturado_en = a.orden_captura.get(campo)
                if capturado_en is not None and capturado_en > orden_tarea.get(tid, 0) + 1:
                    a.problemas.append(
                        f"la tarea '{tid}' usa el campo '{campo}' en una condicion, pero ese "
                        "campo se captura despues en el flujo"
                    )

        sin_salida = [c.a for c in conexiones if not c.cuando]
        if len(campos_tarea) == 1:
            # Forma identica a la de siempre -- el JS del simulador (html.py)
            # no cambia para el caso de un solo campo.
            a.transiciones[tid] = {
                "campo": campos_tarea[0],
                "destinos": destinos,
                "siguiente": sin_salida[0] if sin_salida else None,
            }
        else:
            # Bifurcacion sobre varios campos (clausulas `y`, Task 15): sin
            # "campo" singular -- el JS arma la clave compuesta desde
            # "campos" y hace JSON.stringify() de los valores en ese orden.
            a.transiciones[tid] = {
                "campo": None,
                "campos": list(campos_tarea),
                "destinos": destinos,
                "siguiente": sin_salida[0] if sin_salida else None,
            }

    alcanzables = _alcanzables(m)
    for t in m.flujo.tareas:
        if t.id not in alcanzables:
            a.problemas.append(
                f"la tarea '{t.id}' ({t.nombre}) no es alcanzable: ninguna combinacion de "
                "respuestas llega a ella"
            )

    a.problemas = list(dict.fromkeys(a.problemas))
    return a
