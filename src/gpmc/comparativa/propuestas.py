"""La forma de lo que el agente propone para la comparativa, ya verificado.

Aqui no hay modelo ni verificacion: son los datos que `agentes/` entrega y que
`armar.comparar` recibe. Vive en `comparativa/` para que `comparar` siga siendo
una funcion pura que no importa de `agentes` (spec 2026-10-01).

Una `Propuesta` no trae cifra: trae evidencia. La cifra es cuantas evidencias
hay, y por eso siempre se puede abrir y leer de donde salio.
"""
import dataclasses
import hashlib
from dataclasses import dataclass, field

from gpmc.planeacion.registro import clave

LADOS = ("antes", "despues")
TIPOS_DE_MEJORA = ("documento", "paso", "captura", "visita", "friccion", "tiempo")
# Lo que hace falta para llevar a cabo un punto de mejora. «convenio» es «a
# futuro»: el sistema no se conecta con sistemas internos de la dependencia.
REQUIERE = ("", "servicio_publico", "convenio")
# Cual de las cuatro preguntas del metodo de Simplificacion contesta la mejora,
# en el orden en que se hacen: quitar vale mas que automatizar, y automatizar
# mas que hacerlo a distancia (2026-10-01).
ACCIONES = ("eliminar", "automatizar", "a_distancia")


@dataclass
class Evidencia:
    nombre: str
    cita: str


@dataclass
class Propuesta:
    metrica: str
    lado: str
    evidencias: list = field(default_factory=list)
    # El documento dice expresamente que ya no hay: la cifra es cero y la unica
    # evidencia es la frase que lo dice.
    ninguno: bool = False
    # Solo el tiempo: el plazo tal como esta escrito («3 a 5 dias habiles»).
    texto: str = ""
    motivo: str = ""


@dataclass
class Mejora:
    id: str
    titulo: str
    tipo: str
    propuesta: str
    beneficio: str
    cita: str = ""
    fuente: str = ""
    campo: str = ""
    etiqueta_campo: str = ""
    servicio: str = ""
    requiere: str = ""
    accion: str = ""
    descartada: bool = False


def id_de_mejora(tipo: str, campo: str, cita: str, titulo: str) -> str:
    """Estable entre dos analisis mientras apunte a lo mismo: el campo si lo
    hay, si no la frase. El titulo lo redacta el modelo y cambia de una corrida
    a otra, asi que solo se usa cuando no hay nada mas firme."""
    ancla = campo or clave(cita) or clave(titulo)
    return hashlib.sha256(f"{tipo}|{ancla}".encode("utf-8")).hexdigest()[:12]


def propuestas_a_dicts(propuestas: list) -> list:
    return [dataclasses.asdict(p) for p in propuestas]


def _texto(d: dict, k: str) -> str:
    v = d.get(k)
    return v if isinstance(v, str) else ""


def propuestas_desde(filas) -> list:
    """Tolerante: `comparativa.json` pudo escribirlo una version anterior."""
    salida = []
    for f in filas if isinstance(filas, list) else []:
        if not isinstance(f, dict) or f.get("lado") not in LADOS or not _texto(f, "metrica"):
            continue
        evidencias = [Evidencia(_texto(e, "nombre"), _texto(e, "cita"))
                      for e in f.get("evidencias") or [] if isinstance(e, dict)]
        salida.append(Propuesta(f["metrica"], f["lado"], evidencias, bool(f.get("ninguno")),
                                _texto(f, "texto"), _texto(f, "motivo")))
    return salida


def mejoras_a_dicts(mejoras: list) -> list:
    return [dataclasses.asdict(m) for m in mejoras]


def mejoras_desde(filas) -> list:
    campos = [c.name for c in dataclasses.fields(Mejora) if c.name != "descartada"]
    salida = []
    for f in filas if isinstance(filas, list) else []:
        if not isinstance(f, dict) or not _texto(f, "id") or not _texto(f, "titulo"):
            continue
        salida.append(Mejora(**{k: _texto(f, k) for k in campos},
                             descartada=bool(f.get("descartada"))))
    return salida


def conservar_descartes(nuevas: list, previas: list) -> list:
    """Volver a analizar no resucita lo que una persona descarto. Se reencuentra
    por id, por campo o por frase, porque el id sale de texto que el modelo
    redacta (misma leccion que `documentos.conservar_decisiones`)."""
    descartadas = [p for p in previas if p.descartada]
    ids = {p.id for p in descartadas}
    campos = {(p.tipo, p.campo) for p in descartadas if p.campo}
    citas = {clave(p.cita) for p in descartadas if clave(p.cita)}
    for n in nuevas:
        if n.id in ids or (n.campo and (n.tipo, n.campo) in campos) \
                or (clave(n.cita) and clave(n.cita) in citas):
            n.descartada = True
    return nuevas
