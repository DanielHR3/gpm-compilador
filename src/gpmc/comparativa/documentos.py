"""Los documentos que pedia el tramite y que paso con cada uno.

La dependencia entrega el AS-IS; de la evaluacion de los documentos que se le
piden al ciudadano sale el TO-BE. Este modulo guarda ese analisis: un
`Documento` por cada uno que pedia el AS-IS, con su destino y lo que lo
respalda. Aqui no hay modelo: el agente propone en `agentes/documentos.py`, y
lo que llega a este modulo ya paso por la verificacion.
"""
import dataclasses
import hashlib
from dataclasses import dataclass
from typing import Optional

from gpmc.extractores.as_is import casa, requisitos_del_as_is
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.planeacion.registro import clave

DESTINOS = ("elimina", "conserva", "consulta", "sistema")
# Lo que el ciudadano deja de traer: no lo pide nadie, lo consulta el sistema
# o lo genera el tramite.
YA_NO_SE_PIDE = ("elimina", "consulta", "sistema")
SIN_DESTINO = "sin_destino"
# Mismas dos reglas del tablero (`web/tablero.py`).
_PREFIJO_DOC = "documento:"
_NO_ES_REQUISITO = "vista de solo lectura"
MAX_MOTIVO = 300


@dataclass
class Referencia:
    nombre: str
    etiqueta: str
    pantalla: str
    actor: str
    clase: str


@dataclass
class Documento:
    id: str
    nombre: str
    cita_as_is: str
    destino: str = SIN_DESTINO
    campo: str = ""
    cita_to_be: str = ""
    motivo: str = ""
    motivo_de: str = ""
    confianza: str = ""
    veredicto: str = ""
    origen: str = "lector"
    estado: str = "propuesto"


def id_de(nombre: str, cita: str) -> str:
    """Estable entre analisis: con el se reencuentra lo que ya decidio la
    persona aunque el modelo cambie una mayuscula."""
    return hashlib.sha1(f"{clave(nombre)}|{clave(cita)}".encode("utf-8")).hexdigest()[:12]


def _etiqueta(c) -> str:
    t = (c.etiqueta or c.nombre).strip()
    if t.lower().startswith(_PREFIJO_DOC):
        t = t[len(_PREFIJO_DOC):].strip()
    return t


def referencias(m: Manifiesto) -> list:
    """Lo que el manifiesto ofrece para respaldar un destino. Un archivo cuenta
    como «lo entrega el solicitante» (clase `archivo_ciudadano`) si su pantalla
    es de un actor de autoservicio o de quien inicia el tramite: en Periodico
    Oficial quien solicita es una dependencia, actor de tipo grupo. El archivo
    que sube cualquier otro actor es un producto del tramite."""
    actores = {a.id: a for a in m.actores}
    inician = {t.actor for t in m.flujo.tareas if t.inicial and t.actor}
    salida = []
    for p in m.pantallas:
        actor = actores.get(p.actor)
        nombre_actor = actor.nombre if actor else p.actor
        ciudadano = p.actor in inician or (actor is not None and actor.tipo == "autoservicio")
        for c in p.campos:
            etiqueta = _etiqueta(c)
            if c.tipo == "file":
                if etiqueta.lower().startswith(_NO_ES_REQUISITO):
                    continue
                clase = "archivo_ciudadano" if ciudadano else "archivo_otro"
            elif c.autollena or c.endpoint or c.dependencia_tipo == "api_ajax" or c.tipo == "api_ajax":
                clase = "consulta"
            else:
                continue
            salida.append(Referencia(c.nombre, etiqueta, p.nombre, nombre_actor, clase))
    for a in m.acciones:
        if a.tipo == "documento":
            salida.append(Referencia(a.nombre, a.titulo or a.nombre, "", "", "accion_documento"))
    return salida


def inventario_determinista(as_is: str, m: Manifiesto) -> list:
    """El inventario sin modelo: los requisitos que lee el extractor, y
    «se conserva» solo cuando casan con un archivo del ciudadano. Es el camino
    cuando no hay proveedor y el piso cuando el modelo falla."""
    archivos = [r for r in referencias(m) if r.clase == "archivo_ciudadano"]
    salida, usados = [], set()
    for req in requisitos_del_as_is(as_is):
        doc = Documento(id=id_de(req, req), nombre=req, cita_as_is=req)
        ref = next((r for r in archivos if r.nombre not in usados and casa(req, r.etiqueta)), None)
        if ref is not None:
            usados.add(ref.nombre)
            doc.destino, doc.campo = "conserva", ref.nombre
        salida.append(doc)
    return salida


def agregados(docs: list, m: Manifiesto) -> list:
    """Archivos que el TO-BE le pide al ciudadano y que ningun documento del
    AS-IS ocupa. Una reingenieria que pide algo nuevo se enseña."""
    ocupados = {d.campo for d in docs if d.destino == "conserva" and d.campo}
    return [r.etiqueta for r in referencias(m)
            if r.clase == "archivo_ciudadano" and r.nombre not in ocupados]


def _decidido(d: Documento) -> bool:
    return d.estado in ("aceptado", "corregido") and d.destino in DESTINOS


def _n(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _titular(total: int, decididos: int, fuera: int) -> str:
    if total == 0:
        return "El AS-IS no trae documentos que se puedan leer."
    piden = "ya no se pide" if fuera == 1 else "ya no se piden"
    faltan = total - decididos
    if decididos == 0:
        return f"{'Falta' if faltan == 1 else 'Faltan'} {_n(faltan, 'documento', 'documentos')} por revisar."
    if faltan == 0:
        return (f"De {_n(total, 'documento', 'documentos')} que pedía el trámite, "
                f"{fuera} {piden}.")
    return (f"De {_n(decididos, 'documento revisado', 'documentos revisados')}, "
            f"{fuera} {piden}. {'Falta' if faltan == 1 else 'Faltan'} {faltan} por revisar.")


# Como se dice, en singular y en plural, lo que paso con los documentos.
_FRASE = {
    "elimina": ("Se eliminó", "Se eliminaron"),
    "consulta": ("Se sustituyó por consulta en línea", "Se sustituyeron por consulta en línea"),
    "sistema": ("Lo genera el sistema", "Los genera el sistema"),
    "conserva": ("Se conserva", "Se conservan"),
}
# Orden de lectura: primero lo que el ciudadano dejo de traer.
_ORDEN_SIMPLIFICACION = ("elimina", "consulta", "sistema", "conserva")


def _simplificacion(decididos: list) -> list:
    """«Como se simplifico el tramite», con los documentos por su nombre. Solo
    lo decidido por una persona: lo propuesto y sin revisar no se afirma."""
    salida = []
    for destino in _ORDEN_SIMPLIFICACION:
        nombres = [d.nombre for d in decididos if d.destino == destino]
        if nombres:
            salida.append({"destino": destino, "frase": _FRASE[destino][len(nombres) > 1],
                           "documentos": nombres})
    return salida


def resumen(docs: list, m: Manifiesto) -> dict:
    decididos = [d for d in docs if _decidido(d)]
    fuera = sum(1 for d in decididos if d.destino in YA_NO_SE_PIDE)
    por_destino = {k: 0 for k in (*DESTINOS, SIN_DESTINO)}
    for d in docs:
        por_destino[d.destino if d.destino in por_destino else SIN_DESTINO] += 1
    return {
        "total": len(docs),
        "decididos": len(decididos),
        "ya_no_se_piden": fuera,
        "por_destino": por_destino,
        "agregados": agregados(docs, m),
        "completo": bool(docs) and len(decididos) == len(docs),
        "titular": _titular(len(docs), len(decididos), fuera),
        "simplificacion": _simplificacion(decididos),
    }


def decidir(doc: Documento, destino: str, motivo: str = "") -> Documento:
    if destino not in DESTINOS:
        raise ValueError(f"«{destino}» no es un destino")
    motivo = (motivo or "").strip()[:MAX_MOTIVO]
    doc.estado = "corregido" if (destino != doc.destino or motivo) else "aceptado"
    doc.destino = destino
    # El veredicto era de la propuesta; lo que decide la persona no lo hereda.
    doc.veredicto = ""
    if motivo:
        doc.motivo, doc.motivo_de = motivo, "persona"
    return doc


def reconciliar(docs: list, m: Manifiesto) -> list:
    """Tras un `/resolver` el manifiesto pudo perder un campo. La tarjeta que
    se apoyaba en el vuelve a «sin destino»; las demas no se tocan."""
    vivos = {r.nombre for r in referencias(m)}
    for d in docs:
        if d.campo and d.campo not in vivos:
            d.destino, d.estado, d.veredicto, d.campo = SIN_DESTINO, "propuesto", "campo_desaparecido", ""
    return docs


def conservar_decisiones(nuevos: list, previos: list) -> list:
    """Volver a analizar no pisa lo que ya decidio una persona."""
    decididos = {d.id: d for d in previos if _decidido(d)}
    return [decididos.get(d.id, d) for d in nuevos]


def avisos(docs: list) -> list:
    return [Hueco("por_confirmar", "CMP-05", "to_be",
                  f"El TO-BE ya no pide «{d.nombre}» y no dice por qué.")
            for d in docs if _decidido(d) and d.destino == "elimina" and not d.cita_to_be]


def a_dicts(docs: list) -> list:
    return [dataclasses.asdict(d) for d in docs]


def desde_dicts(filas) -> list:
    campos = {f.name for f in dataclasses.fields(Documento)}
    salida = []
    for f in filas or []:
        if not isinstance(f, dict) or not all(k in f for k in ("id", "nombre", "cita_as_is")):
            continue
        salida.append(Documento(**{k: v for k, v in f.items() if k in campos}))
    return salida
