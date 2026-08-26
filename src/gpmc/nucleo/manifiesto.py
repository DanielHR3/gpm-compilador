"""Modelo del manifiesto: la representacion intermedia del tramite.

El analista corrige aqui, no en el .gpm. El principio que gobierna el formato
es que se describe QUE se quiere, nunca COMO se escribe: ninguna sintaxis de
GPM, ningun PHP, ninguna arroba.
"""

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

TipoCampo = Literal[
    "text", "textarea", "select", "radio", "file", "date", "date_time",
    "paragraph", "subtitle", "cart", "api_ajax", "documento",
]


class FichaRUTS(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = "ciudadano"
    type_of_person: Literal["fisica", "moral", "ambas"] = "ambas"
    tiempo_entrega: str = ""
    costo: str = ""
    description: str = ""
    publico: bool = False


class Tramite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    dependencia: str
    homoclave: str = ""
    expediente: str = ""
    ruts: FichaRUTS = FichaRUTS()


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    nombre: str
    tipo: Literal["autoservicio", "grupo"] = "autoservicio"
    grupos_usuarios: list[str] = []


class OpcionCatalogo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    etiqueta: str
    valor: str


class Campo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    etiqueta: str = ""
    tipo: TipoCampo = "text"
    obligatorio: bool = False
    solo_lectura: bool = False
    longitud_exacta: Optional[int] = None
    ayuda: Optional[str] = None
    catalogo: list[OpcionCatalogo] = []
    origen: Optional[str] = None
    ancho: Literal["completo", "medio", "tercio"] = "medio"


class Pantalla(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    nombre: str
    actor: str
    paso_ciudadano: Optional[int] = None
    campos: list[Campo] = []


class Tarea(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    nombre: str
    actor: Optional[str] = None
    inicial: bool = False
    terminal: bool = False
    pantallas: list[str] = []


class Condicion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campo: str
    igual: str


class Conexion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    de: str
    a: str
    cuando: Optional[Condicion] = None


class Flujo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tareas: list[Tarea]
    conexiones: list[Conexion] = []


class Accion(BaseModel):
    model_config = ConfigDict(extra="allow")
    tipo: Literal["folio", "costo", "documento", "notificacion"]
    nombre: str


class Manifiesto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    tramite: Tramite
    actores: list[Actor]
    pantallas: list[Pantalla] = []
    flujo: Flujo
    acciones: list[Accion] = []

    def campo_por_nombre(self, nombre: str) -> Optional[Campo]:
        for p in self.pantallas:
            for c in p.campos:
                if c.nombre == nombre:
                    return c
        return None

    @model_validator(mode="after")
    def _coherencia(self):
        ids_actor = {a.id for a in self.actores}
        for p in self.pantallas:
            if p.actor not in ids_actor:
                raise ValueError(f"la pantalla '{p.id}' usa un actor no declarado: '{p.actor}'")

        ids_pantalla = {p.id for p in self.pantallas}
        ids_tarea = {t.id for t in self.flujo.tareas}
        for t in self.flujo.tareas:
            if t.actor is not None and t.actor not in ids_actor:
                raise ValueError(f"la tarea '{t.id}' usa un actor no declarado: '{t.actor}'")
            for pid in t.pantallas:
                if pid not in ids_pantalla:
                    raise ValueError(
                        f"la tarea '{t.id}' referencia una pantalla inexistente: '{pid}'"
                    )

        if not any(t.inicial for t in self.flujo.tareas):
            raise ValueError("el flujo no tiene ninguna tarea inicial")
        if sum(1 for t in self.flujo.tareas if t.inicial) > 1:
            raise ValueError("el flujo tiene mas de una tarea inicial")
        if not any(t.terminal for t in self.flujo.tareas):
            raise ValueError("el flujo no tiene ninguna tarea terminal")

        nombres_campo = {c.nombre for p in self.pantallas for c in p.campos}
        for cx in self.flujo.conexiones:
            for extremo in (cx.de, cx.a):
                if extremo not in ids_tarea:
                    raise ValueError(f"la conexion apunta a una tarea inexistente: '{extremo}'")
            if cx.cuando and cx.cuando.campo not in nombres_campo:
                raise ValueError(
                    f"la condicion de '{cx.de}' usa un campo no declarado: '{cx.cuando.campo}'"
                )
        return self


def cargar(ruta: Path) -> Manifiesto:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    return Manifiesto.model_validate(datos)


def guardar(m: Manifiesto, ruta: Path) -> None:
    datos = m.model_dump(mode="json", exclude_defaults=True)
    Path(ruta).write_text(
        yaml.safe_dump(datos, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
