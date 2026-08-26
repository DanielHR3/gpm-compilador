"""Registro de tiempos de los expedientes de Simplificacion.

El ciclo de la DGT esta medido (14-16 dias habiles para el tramite mas
sencillo). El de Simplificacion —producir el AS-IS, el TO-BE, el Diccionario y
los Wireframes— nunca se midio: el documento de tiempos lo dice expresamente.

Este registro lo mide, y arranca donde el trabajo arranca de verdad: cuando el
analista teclea el nombre del tramite. Las fechas del frontmatter solo dicen
cuando se guardo un archivo por primera vez, que puede ser dias despues.
"""

from typing import Optional
import re
import statistics
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

ENTREGABLES = (
    "as-is", "to-be", "bpmn", "diccionario", "wireframes", "control-acciones",
)


def clave(nombre: str) -> str:
    """Normaliza un nombre para poder reencontrarlo aunque varie."""
    sin = "".join(
        c for c in unicodedata.normalize("NFD", nombre or "")
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", sin.lower()).strip()


@dataclass
class Expediente:
    nombre: str
    analista: str
    inicio: date
    cierre: Optional[date] = None
    hitos: dict = field(default_factory=dict)
    origen: str = "vivo"          # "vivo" (medido) | "wiki" (sembrado)

    @property
    def dias(self) -> int:
        return ((self.cierre or date.today()) - self.inicio).days

    @property
    def abierto(self) -> bool:
        return self.cierre is None

    @property
    def completo(self) -> bool:
        """Un expediente cuenta para planear solo si llego a los entregables
        de fondo. Uno recien abierto no es un ciclo rapido: es uno sin medir."""
        return len(self.hitos) >= 5


class Registro:
    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)
        self._datos: dict[str, Expediente] = {}
        self._cargar()

    def _cargar(self):
        if not self.ruta.exists():
            return
        crudo = yaml.safe_load(self.ruta.read_text(encoding="utf-8")) or {}
        for k, v in (crudo.get("expedientes") or {}).items():
            self._datos[k] = Expediente(
                nombre=v["nombre"],
                analista=v.get("analista", ""),
                inicio=date.fromisoformat(v["inicio"]),
                cierre=date.fromisoformat(v["cierre"]) if v.get("cierre") else None,
                hitos={h: date.fromisoformat(f) for h, f in (v.get("hitos") or {}).items()},
                origen=v.get("origen", "vivo"),
            )

    def _guardar(self):
        salida = {
            "expedientes": {
                k: {
                    "nombre": e.nombre,
                    "analista": e.analista,
                    "inicio": e.inicio.isoformat(),
                    **({"cierre": e.cierre.isoformat()} if e.cierre else {}),
                    **({"hitos": {h: f.isoformat() for h, f in e.hitos.items()}}
                       if e.hitos else {}),
                    "origen": e.origen,
                }
                for k, e in sorted(self._datos.items())
            }
        }
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(
            yaml.safe_dump(salida, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    def iniciar(self, nombre: str, analista: str = "", cuando: Optional[date] = None,
                origen: str = "vivo") -> Expediente:
        """Arranca el reloj. Llamarla dos veces NO reinicia el inicio."""
        k = clave(nombre)
        if k in self._datos:
            return self._datos[k]
        self._datos[k] = Expediente(
            nombre=nombre.strip(), analista=analista,
            inicio=cuando or date.today(), origen=origen,
        )
        self._guardar()
        return self._datos[k]

    def buscar(self, nombre: str) -> Optional[Expediente]:
        return self._datos.get(clave(nombre))

    def todos(self) -> list[Expediente]:
        return list(self._datos.values())

    def hito(self, nombre: str, entregable: str, cuando: Optional[date] = None):
        if entregable not in ENTREGABLES:
            raise ValueError(
                f"entregable desconocido: '{entregable}'. Validos: {', '.join(ENTREGABLES)}"
            )
        e = self.buscar(nombre)
        if e is None:
            raise KeyError(f"no hay expediente registrado con el nombre '{nombre}'")
        e.hitos[entregable] = cuando or date.today()
        self._guardar()

    def cerrar(self, nombre: str, cuando: Optional[date] = None):
        e = self.buscar(nombre)
        if e is None:
            raise KeyError(f"no hay expediente registrado con el nombre '{nombre}'")
        e.cierre = cuando or date.today()
        self._guardar()


@dataclass
class Estado:
    abiertos: list[Expediente]
    cerrados: list[Expediente]


def estado(reg: Registro) -> Estado:
    todos = sorted(reg.todos(), key=lambda e: e.inicio)
    return Estado(
        abiertos=[e for e in todos if e.abierto],
        cerrados=[e for e in todos if not e.abierto],
    )


@dataclass
class Capacidad:
    analista: str
    abiertos: int
    cerrados: int
    completos: int
    mediana_dias: Optional[int]      # solo de expedientes completos


def capacidad(reg: Registro) -> dict[str, Capacidad]:
    por: dict[str, list[Expediente]] = {}
    for e in reg.todos():
        por.setdefault(e.analista or "(sin analista)", []).append(e)

    salida = {}
    for nombre, exps in sorted(por.items()):
        cerrados = [e for e in exps if not e.abierto]
        # Misma regla que la proyeccion: solo los completos cuentan. Mezclar
        # expedientes recien abiertos hunde la mediana y desorienta a quien planea.
        dias = [e.dias for e in cerrados if e.completo]
        salida[nombre] = Capacidad(
            analista=nombre,
            abiertos=sum(1 for e in exps if e.abierto),
            cerrados=len(cerrados),
            completos=len(dias),
            mediana_dias=int(statistics.median(dias)) if dias else None,
        )
    return salida


_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
_FECHA = re.compile(r"^(creado|actualizado):\s*(\d{4}-\d{2}-\d{2})", re.M)

# Que archivo del expediente acredita cada entregable.
ARCHIVOS_DE_ENTREGABLE = {
    "as-is": ["Análisis AS-IS.md", "AS-IS.md"],
    "to-be": ["Propuesta TO-BE.md", "TO-BE.md"],
    "bpmn": ["*.bpmn"],
    "diccionario": ["Diccionario de Datos.md", "Diccionario de Datos.xlsx"],
    "wireframes": ["Wireframes.pdf", "Wireframes.md"],
    "control-acciones": ["Control de Acciones*.md"],
}


def sembrar_desde_wiki(reg: Registro, raiz: Path) -> int:
    """Siembra el registro con los expedientes ya trabajados.

    Las fechas salen del frontmatter, que mide cuando se guardo un archivo, no
    cuando empezo el trabajo: por eso quedan marcadas con origen 'wiki' y se
    distinguen de lo medido en vivo.
    """
    raiz = Path(raiz)
    sembrados = 0
    for carpeta in sorted(p for p in raiz.glob("*/*") if p.is_dir()):
        fechas = []
        for md in carpeta.glob("*.md"):
            m = _FRONTMATTER.search(md.read_text(encoding="utf-8", errors="ignore"))
            if m:
                fechas += [date.fromisoformat(f) for _, f in _FECHA.findall(m.group(1))]
        if not fechas:
            continue
        reg.iniciar(
            carpeta.name, analista=carpeta.parent.name,
            cuando=min(fechas), origen="wiki",
        )
        e = reg.buscar(carpeta.name)
        if e.origen == "wiki" and e.cierre is None:
            e.cierre = max(fechas)
        for etiqueta, patrones in ARCHIVOS_DE_ENTREGABLE.items():
            if any(list(carpeta.glob(pat)) for pat in patrones):
                e.hitos.setdefault(etiqueta, e.cierre or max(fechas))
        sembrados += 1
    reg._guardar()
    return sembrados
