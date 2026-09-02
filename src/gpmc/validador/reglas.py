"""Reglas de revision sobre un .gpm.

Los codigos SEG-* son propios de esta herramienta
de 2026. Los EST-* y FMT-* son propios de esta herramienta.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from gpmc.nucleo import reglas as nreglas
from gpmc.nucleo.formato import leer


@dataclass(frozen=True)
class Hallazgo:
    codigo: str
    gravedad: str  # "bloqueante" | "aviso"
    mensaje: str
    ubicacion: str


def _expresion_de(accion: dict) -> str:
    try:
        return json.loads(accion.get("extra") or "{}").get("expresion", "") or ""
    except (json.JSONDecodeError, AttributeError, TypeError):
        return ""


def _es_de_folio(accion: dict, expresion: str) -> bool:
    texto = (accion.get("nombre") or "") + " " + str(accion.get("extra") or "")
    return "folio" in texto.lower()


def _revisar_estructura(g: dict) -> list[Hallazgo]:
    hallazgos = []
    tareas = g.get("Tareas", [])
    ids = {str(t.get("id")) for t in tareas}

    for c in g.get("Conexiones", []):
        for extremo in ("tarea_id_origen", "tarea_id_destino"):
            destino = c.get(extremo)
            if destino is not None and str(destino) not in ids:
                hallazgos.append(Hallazgo(
                    "EST-01", "bloqueante",
                    f"la conexion {c.get('id')} apunta a una tarea inexistente: {destino}",
                    f"Conexiones[{c.get('id')}]",
                ))

    if tareas and not any(str(t.get("terminal")) == "1" for t in tareas):
        hallazgos.append(Hallazgo(
            "EST-02", "bloqueante", "el proceso no tiene ninguna tarea terminal", "Tareas"))

    iniciales = [t for t in tareas if str(t.get("inicial")) == "1"]
    if tareas and not iniciales:
        hallazgos.append(Hallazgo(
            "EST-03", "bloqueante",
            "el proceso no tiene ninguna tarea inicial: nadie puede iniciarlo",
            "Tareas",
        ))
    elif len(iniciales) > 1:
        # Varias tareas iniciales NO son un defecto: son puntos de entrada de un
        # tramite omnicanal. El export autentico del un export de referencia tiene dos
        # ("Datos generales (ciudadano)" y "Registro en oficina (Funcionario)").
        # Se informa para que quede visible, sin bloquear.
        nombres = ", ".join(repr(t.get("nombre")) for t in iniciales)
        hallazgos.append(Hallazgo(
            "EST-04", "aviso",
            f"el proceso tiene {len(iniciales)} puntos de entrada ({nombres}); "
            "confirmar que la omnicanalidad es intencional",
            "Tareas",
        ))
    return hallazgos


# La columna 'campo.nombre' de la plataforma corta en este limite y el import
# entero falla con "Data too long for column 'nombre'" (verificado 2026-09-02,
# expediente de Prorroga). El extractor ya capa el nombre; esta regla es la red
# de seguridad para un manifiesto escrito a mano.
_LIMITE_NOMBRE_CAMPO = 30


def _catalog_type_de(campo: dict) -> str:
    try:
        return json.loads(campo.get("extra") or "{}").get("catalog_type", "") or ""
    except (json.JSONDecodeError, AttributeError, TypeError):
        return ""


def _revisar_campos(g: dict) -> list[Hallazgo]:
    hallazgos = []
    for f in g.get("Formularios", []):
        for c in f.get("Campos", []):
            nombre = str(c.get("nombre") or "")
            ubic = f"Formularios/{f.get('id')}/{nombre}"
            if len(nombre) > _LIMITE_NOMBRE_CAMPO:
                hallazgos.append(Hallazgo(
                    "EST-05", "bloqueante",
                    f"el nombre tecnico '{nombre}' tiene {len(nombre)} caracteres; la "
                    f"columna 'campo.nombre' corta en {_LIMITE_NOMBRE_CAMPO} y el import "
                    f"falla con 'Data too long for column nombre'",
                    ubic,
                ))

            # La plataforma hace foreach($datos) al renderizar un select/radio
            # (radio/display.php:4, models/CampoSelect.php:375). Un catalogo
            # remoto (catalog_type 'url') se puebla por AJAX y datos=null es
            # correcto; en cualquier otro caso null revienta la vista con
            # "Invalid argument supplied for foreach()" (verificado 2026-09-02).
            if c.get("tipo") in ("select", "radio") and _catalog_type_de(c) != "url":
                datos = c.get("datos")
                if datos is None:
                    hallazgos.append(Hallazgo(
                        "EST-06", "bloqueante",
                        f"el campo {c.get('tipo')} '{nombre}' no lleva 'datos' (null); la "
                        f"vista revienta con 'Invalid argument supplied for foreach()'",
                        ubic,
                    ))
                elif datos in ("[]", "", "null"):
                    hallazgos.append(Hallazgo(
                        "EST-06", "aviso",
                        f"el campo {c.get('tipo')} '{nombre}' no tiene opciones; la "
                        f"plataforma lo renderiza como lista vacia",
                        ubic,
                    ))
    return hallazgos


def _revisar_acciones(g: dict) -> list[Hallazgo]:
    hallazgos = []
    for a in g.get("Acciones", []):
        expr = _expresion_de(a)
        if not expr:
            continue
        ubic = f"Acciones/{a.get('nombre')}"

        if _es_de_folio(a, expr):
            if "->count()" in expr:
                hallazgos.append(Hallazgo(
                    "FOLIO-01", "bloqueante",
                    "el folio se calcula con count() sin bloqueo: dos tramites simultaneos "
                    "pueden recibir el mismo folio",
                    ubic,
                ))
            if re.search(r"\brand\s*\(", expr):
                hallazgos.append(Hallazgo(
                    "FOLIO-01", "bloqueante",
                    "el folio se genera con rand(): no es consecutivo y puede colisionar",
                    ubic,
                ))
            if "lockForUpdate()" in expr and "dato_seguimiento" not in expr:
                # El contador autentico vive en 'dato_seguimiento' (columna
                # 'valor'), llaveado por el nombre de la variable: asi lo traen
                # los dos exports que funcionan. El viejo esquema por
                # proceso_folio/proceso_id se rompe al importar porque la
                # plataforma reasigna el proceso_id (PLAT-4, acta 2026-08-30).
                hallazgos.append(Hallazgo(
                    "FOLIO-02", "bloqueante",
                    "el folio bloquea una tabla distinta de 'dato_seguimiento'; "
                    "el contador autentico vive ahi (columna 'valor') y no lleva proceso_id",
                    ubic,
                ))

        arma_html = "<" in expr and ("$data[" in expr or "@@" in expr)
        if arma_html and "htmlspecialchars" not in expr:
            hallazgos.append(Hallazgo(
                "DOC-01", "bloqueante",
                "se arma un documento con datos del usuario sin escapar (htmlspecialchars)",
                ubic,
            ))
    return hallazgos


def _revisar_credenciales(g: dict) -> list[Hallazgo]:
    """CRED-01. Se reporta como aviso, no bloquea: decision del area, spec seccion 7."""
    hallazgos = []
    for f in g.get("Formularios", []):
        for c in f.get("Campos", []):
            if "Authorization" in str(c.get("extra") or ""):
                hallazgos.append(Hallazgo(
                    "CRED-01", "aviso",
                    f"el campo '{c.get('nombre')}' expone una credencial al navegador del "
                    "ciudadano (decision documentada del area)",
                    f"Formularios/{f.get('id')}/{c.get('nombre')}",
                ))
    return hallazgos


def _revisar_sintaxis(g: dict) -> list[Hallazgo]:
    """Apagada por omision. Spec seccion 9.bis: cuestion sin resolver."""
    if not nreglas.SINTAXIS_ESTRICTA:
        return []
    hallazgos = []
    for c in g.get("Conexiones", []):
        regla = c.get("regla") or ""
        if regla and "->value" not in regla:
            hallazgos.append(Hallazgo(
                "FMT-01", "bloqueante",
                f"la regla {regla!r} no usa la forma ->value ===",
                f"Conexiones[{c.get('id')}]",
            ))
    return hallazgos


def revisar(gpm: dict) -> list[Hallazgo]:
    return (
        _revisar_estructura(gpm)
        + _revisar_campos(gpm)
        + _revisar_acciones(gpm)
        + _revisar_credenciales(gpm)
        + _revisar_sintaxis(gpm)
    )


def revisar_archivo(ruta: Path) -> list[Hallazgo]:
    return revisar(leer(ruta))
