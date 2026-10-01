#!/usr/bin/env python3
"""Trazabilidad historia de usuario -> criterio de aceptacion -> prueba.

Las historias viven en la boveda de Obsidian (privada) y citan sus pruebas por
nombre dentro de cada criterio: «- [x] **CA3.** ... `test_algo`». Si una prueba
se renombra, la cita queda muerta y nadie lo nota. Este script lee esas citas,
las cruza con las pruebas que existen en tests/ y escribe una matriz.

Uso:
    scripts/trazabilidad.py --boveda "<.../02 - Historias de usuario>" [--salida matriz.md]

Sale con codigo 1 si hay citas muertas, para poder usarlo como revision.
Solo stdlib: no es parte del compilador y no debe arrastrar dependencias.
"""
import argparse
import ast
import re
import sys
from datetime import date
from pathlib import Path
from typing import List, NamedTuple, Set, Tuple

_INICIO_CA = re.compile(r"^- \[( |x|X)\] \*\*(CA\d+)\.\*\*")
_PRUEBA = re.compile(r"`(test_[A-Za-z0-9_]+)`")
_HU = re.compile(r"^HU-[A-Z]+-\d+$")
_FILA_CA = re.compile(r"^\|\s*(CA\d+)\s*\|")


class Criterio(NamedTuple):
    clave: str
    hecho: bool
    pruebas: List[str]


class Historia(NamedTuple):
    id: str
    titulo: str
    criterios: List[Criterio]


def criterios_de(texto: str) -> List[Criterio]:
    """Los criterios de la nota, con las pruebas citadas dentro de cada uno.

    Un criterio abarca su linea y las de continuacion (sangradas) hasta el
    siguiente criterio, una linea en blanco o un encabezado; lo citado fuera
    de los criterios no cuenta.
    """
    criterios = []  # type: List[Criterio]
    actual = None
    for linea in texto.splitlines():
        m = _INICIO_CA.match(linea)
        if m:
            actual = Criterio(m.group(2), m.group(1) != " ", [])
            criterios.append(actual)
        elif actual is not None and (not linea.strip() or linea.startswith(("#", "- "))):
            actual = None
            continue
        if actual is not None:
            for p in _PRUEBA.findall(linea):
                if p not in actual.pruebas:
                    actual.pruebas.append(p)
    return criterios


def pruebas_en_tablas(texto: str) -> List[Tuple[str, str]]:
    """Pares (criterio, prueba) de filas de tabla que empiezan con «| CAn |».

    Las HU de la fase 1 llevan la evidencia en la tabla de su plan, no en el
    criterio.
    """
    pares = []
    for linea in texto.splitlines():
        m = _FILA_CA.match(linea)
        if m:
            pares.extend((m.group(1), p) for p in _PRUEBA.findall(linea))
    return pares


def leer_boveda(carpeta: Path) -> List[Historia]:
    """Una historia por carpeta HU-*: los criterios salen de su nota principal
    HU-*.md; las tablas de las demas notas solo suman pruebas a esos criterios."""
    historias = []
    for sub in sorted(carpeta.iterdir()):
        nota = sub / (sub.name + ".md")
        if not (sub.is_dir() and _HU.match(sub.name) and nota.is_file()):
            continue
        texto = nota.read_text(encoding="utf-8", errors="replace")
        primera = texto.splitlines()[0] if texto else ""
        titulo = primera.lstrip("# ").split(" - ", 1)[-1].strip()
        criterios = criterios_de(texto)
        por_clave = {c.clave: c for c in criterios}
        for otra in sorted(sub.glob("*.md")):
            for clave, prueba in pruebas_en_tablas(otra.read_text(encoding="utf-8", errors="replace")):
                c = por_clave.get(clave)
                if c is not None and prueba not in c.pruebas:
                    c.pruebas.append(prueba)
        historias.append(Historia(sub.name, titulo, criterios))
    return historias


def pruebas_del_repo(carpeta: Path) -> Set[str]:
    """Nombres de funcion test_* definidos en los test_*.py (funciones y metodos)."""
    nombres = set()
    for archivo in carpeta.rglob("test_*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), str(archivo))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name.startswith("test_"):
                nombres.add(nodo.name)
    return nombres


def citas_muertas(historias: List[Historia], existentes: Set[str]) -> List[Tuple[str, str, str]]:
    return [
        (h.id, c.clave, p)
        for h in historias
        for c in h.criterios
        for p in c.pruebas
        if p not in existentes
    ]


def matriz(historias: List[Historia], existentes: Set[str]) -> str:
    lineas = [
        "---",
        "tipo: matriz-trazabilidad",
        "generado: {}".format(date.today().isoformat()),
        "---",
        "",
        "# Matriz de trazabilidad",
        "",
        "> Generado por scripts/trazabilidad.py. **No se edita a mano:** se corrige la cita en la",
        "> historia y se vuelve a generar.",
        "",
    ]
    muertas = citas_muertas(historias, existentes)
    total = sum(len(h.criterios) for h in historias)
    con_prueba = sum(1 for h in historias for c in h.criterios if c.pruebas)
    lineas.append(
        "**{}** historias · **{}** criterios · **{}** con prueba citada · **{}** citas muertas".format(
            len(historias), total, con_prueba, len(muertas)
        )
    )
    lineas.append("")
    for h in historias:
        hechos = sum(1 for c in h.criterios if c.hecho)
        lineas.append("## [[{}]] — {}".format(h.id, h.titulo))
        lineas.append("")
        lineas.append("{} de {} criterios marcados.".format(hechos, len(h.criterios)))
        lineas.append("")
        for c in h.criterios:
            # Sin casillas «- [ ]»: Obsidian Tasks las contaria como tareas pendientes.
            marca = "✅" if c.hecho else "⬜"
            if c.pruebas:
                citas = ", ".join(
                    "`{}`".format(p) if p in existentes else "`{}` ⚠️ no existe".format(p)
                    for p in c.pruebas
                )
            else:
                citas = "*sin prueba citada*"
            lineas.append("- {} **{}** — {}".format(marca, c.clave, citas))
        lineas.append("")
    return "\n".join(lineas)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--boveda", required=True, type=Path, help="carpeta «02 - Historias de usuario»")
    ap.add_argument("--pruebas", type=Path, default=Path(__file__).resolve().parent.parent / "tests")
    ap.add_argument("--salida", type=Path, help="escribe la matriz en este archivo")
    args = ap.parse_args(argv)

    historias = leer_boveda(args.boveda)
    existentes = pruebas_del_repo(args.pruebas)
    if args.salida:
        args.salida.write_text(matriz(historias, existentes) + "\n", encoding="utf-8")
    muertas = citas_muertas(historias, existentes)
    for hu, ca, prueba in muertas:
        print("{} {}: `{}` no existe en {}".format(hu, ca, prueba, args.pruebas), file=sys.stderr)
    print(
        "{} historias, {} citas, {} muertas".format(
            len(historias), sum(len(c.pruebas) for h in historias for c in h.criterios), len(muertas)
        )
    )
    return 1 if muertas else 0


if __name__ == "__main__":
    sys.exit(main())
