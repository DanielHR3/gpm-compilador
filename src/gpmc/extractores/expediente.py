"""Orquesta los tres extractores sobre la carpeta de un expediente.

Cada extractor es independiente: si uno falla, lo suyo se convierte en hueco y
los demas siguen. La herramienta siempre produce algo revisable.
"""

from typing import Optional
import re
from dataclasses import dataclass, field
from pathlib import Path

from gpmc.extractores import diccionario as ext_dicc
from gpmc.extractores import mermaid as ext_mmd
from gpmc.extractores import metadatos as ext_meta
from gpmc.nucleo.manifiesto import (
    Actor, Conexion, Flujo, Manifiesto, Pantalla, Tarea,
)

_BLOQUE_MERMAID = re.compile(r"```mermaid(.*?)```", re.S)


@dataclass
class Resultado:
    manifiesto: Optional[Manifiesto] = None
    huecos: list[str] = field(default_factory=list)


class SinPermiso(Exception):
    """macOS niega el acceso a ~/Documents y ~/Desktop salvo autorizacion
    expresa. El archivo existe, exists() dice True, y la lectura revienta con
    un error que a un analista no le dice nada."""


def _leer(carpeta: Path, nombre: str) -> str:
    ruta = carpeta / nombre
    if not ruta.exists():
        return ""
    try:
        return ruta.read_text(encoding="utf-8")
    except PermissionError as exc:
        raise SinPermiso(
            f"macOS no permite leer '{ruta}'.\n\n"
            "El archivo existe, pero el sistema bloquea el acceso a las carpetas "
            "Documentos, Escritorio y Descargas.\n\n"
            "Solucion: Ajustes del Sistema > Privacidad y seguridad > Acceso total al "
            "disco, y autorizar la aplicacion desde la que se ejecuta (Terminal, o el "
            "navegador si se usa el asistente web).\n\n"
            "Alternativa: mover el expediente a una carpeta fuera de esas tres."
        ) from exc


def extraer_expediente(carpeta: Path) -> Resultado:
    carpeta = Path(carpeta)
    r = Resultado()

    as_is = _leer(carpeta, "Análisis AS-IS.md") or _leer(carpeta, "AS-IS.md")
    to_be = _leer(carpeta, "Propuesta TO-BE.md") or _leer(carpeta, "TO-BE.md")
    dicc = _leer(carpeta, "Diccionario de Datos.md")

    if not dicc:
        r.huecos.append("no se encontro 'Diccionario de Datos.md': sin el no hay pantallas")
        return r
    if not to_be:
        r.huecos.append("no se encontro 'Propuesta TO-BE.md': sin el no hay flujo")

    meta = ext_meta.extraer(as_is, to_be, nombre_carpeta=carpeta.name)
    r.huecos += [f"[metadatos] {h}" for h in meta.huecos]
    tramite = meta.tramite
    if tramite is None:
        from gpmc.nucleo.manifiesto import Tramite
        tramite = Tramite(nombre=carpeta.name, dependencia="[por confirmar]")

    rd = ext_dicc.extraer(dicc)
    r.huecos += [f"[diccionario] {h}" for h in rd.huecos]
    if not rd.pantallas:
        r.huecos.append("[diccionario] no se extrajo ninguna pantalla")
        return r

    actores_vistos: dict[str, Actor] = {}
    pantallas: list[Pantalla] = []
    for p in rd.pantallas:
        aid = re.sub(r"[^a-z0-9]+", "_", p.actor).strip("_")[:30] or "actor"
        if aid not in actores_vistos:
            es_ciudadano = ext_mmd.normalizar_actor(aid) == "ciudadano"
            actores_vistos[aid] = Actor(
                id=aid,
                nombre=p.actor.title(),
                tipo="autoservicio" if es_ciudadano else "grupo",
                grupos_usuarios=[] if es_ciudadano else [p.actor.title()],
            )
        pantallas.append(Pantalla(
            id=p.id, nombre=p.nombre, actor=aid,
            paso_ciudadano=p.paso_ciudadano, campos=p.campos,
        ))

    # Flujo: una tarea por pantalla, en orden, mas una terminal. El diagrama
    # Mermaid se usa para reportar cuanto se aparta esta linealizacion del
    # flujo real, no para construirla: eso exige la revision de una persona.
    tareas = [
        Tarea(id=f"t_{p.id}", nombre=p.nombre[:60], actor=p.actor,
              inicial=(i == 0), pantallas=[p.id])
        for i, p in enumerate(pantallas)
    ]
    tareas.append(Tarea(id="t_fin", nombre="Trámite concluido", terminal=True))
    conexiones = [
        Conexion(de=tareas[i].id, a=tareas[i + 1].id) for i in range(len(tareas) - 1)
    ]

    if to_be:
        bloques = _BLOQUE_MERMAID.findall(to_be)
        if bloques:
            rm = ext_mmd.extraer(bloques[0])
            r.huecos += [f"[mermaid] {h}" for h in rm.huecos]
            compuertas = [n for n in rm.nodos if n.clase_nodo == "compuerta"]
            if compuertas:
                r.huecos.append(
                    f"[flujo] el diagrama TO-BE tiene {len(compuertas)} compuertas que este "
                    f"manifiesto NO reproduce: el flujo propuesto es lineal, pantalla por "
                    f"pantalla. Revisar y ramificar a mano antes de compilar."
                )
            tareas_mmd = [n for n in rm.nodos if n.clase_nodo == "tarea"]
            if len(tareas_mmd) != len(pantallas):
                r.huecos.append(
                    f"[flujo] el diagrama tiene {len(tareas_mmd)} tareas y el Diccionario "
                    f"{len(pantallas)} pantallas; confirmar la correspondencia"
                )
        else:
            r.huecos.append("[mermaid] la Propuesta TO-BE no trae bloque ```mermaid```")

    r.manifiesto = Manifiesto(
        tramite=tramite,
        actores=list(actores_vistos.values()),
        pantallas=pantallas,
        flujo=Flujo(tareas=tareas, conexiones=conexiones),
        acciones=[],
    )
    return r
