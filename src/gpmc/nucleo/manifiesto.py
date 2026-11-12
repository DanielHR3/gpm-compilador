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
    # Llave comun con Simplifica (ID de la ficha de RUTS); al final para no mover
    # el orden de serializacion. Vacio = el AS-IS no lo trae (hueco META-RUTS).
    ruts_id: str = ""


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


class Clausula(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campo: str
    igual: str
    operador: Literal["==", "!="] = "=="


class Condicion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campo: str
    igual: str
    operador: Literal["==", "!="] = "=="
    y: list[Clausula] = []


class Campo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    etiqueta: str = ""
    tipo: TipoCampo = "text"
    obligatorio: bool = False
    solo_lectura: bool = False
    longitud_exacta: Optional[int] = None
    # «max. 150 caracteres» NO es una longitud exacta: emitirla como tal deja un
    # campo que exige 150 justos y donde una razon social de 40 no se puede
    # capturar. La plataforma distingue las dos formas —en los exports
    # autenticos conviven `exact_length[18]`, `max_length[9]` y
    # `min_length[12]|max_length[13]`— y nosotros no. P-13, 2026-09-21.
    longitud_max: Optional[int] = None
    longitud_min: Optional[int] = None
    # Regla de formato de la plataforma, con los tres nombres que usan los
    # exports autenticos (`required|numeric|exact_length[10]`,
    # `required|valid_email`). La fabrica observo dos veces que los campos
    # salian solo con obligatoriedad y longitud (2026-11-12).
    formato: Optional[Literal["numeric", "alpha_numeric", "valid_email"]] = None
    ayuda: Optional[str] = None
    catalogo: list[OpcionCatalogo] = []
    # Condicion de visibilidad ('Visible solo si "X" = Y' en el Diccionario).
    # Viaja al .gpm como string en dependiente_campo, la forma de los exports.
    condicion_visible: Optional[Condicion] = None
    # Propiedades para Fase A: integracion de catalogos y APIs
    dependencia_tipo: Optional[Literal["api_ajax", "campo", "archivo"]] = None
    dependencia_campo: Optional[str] = None
    endpoint: Optional[str] = None
    # Solo para `tipo: api_ajax`: que campo de la vista llena cada dato de la
    # respuesta ({campo: clave}). El orden se conserva: es el de los arreglos
    # `get_value_*` del export.
    autollena: dict[str, str] = {}
    origen: Optional[str] = None
    ancho: Literal["completo", "medio", "tercio"] = "medio"


class Pantalla(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    nombre: str
    actor: str
    paso_ciudadano: Optional[int] = None
    campos: list[Campo] = []
    # Pantallas anteriores que la tarea de esta pantalla ensena primero, en
    # modo visualizacion: la fila «Vista de solo lectura (Origen → Destino)»
    # del Diccionario. Vive aqui y no en el flujo porque el flujo se rearma
    # desde el diagrama (`reensamblar_flujo`) y lo perderia.
    muestra_antes: list[str] = []


class PasoPantalla(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    modo: Literal["edicion", "visualizacion"] = "edicion"


class Tarea(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    nombre: str
    actor: Optional[str] = None
    inicial: bool = False
    terminal: bool = False
    pantallas: list[PasoPantalla] = []
    acciones_antes: list[str] = []
    acciones_despues: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _normalizar_pantallas(cls, data: dict):
        if isinstance(data, dict) and "pantallas" in data:
            norm = []
            for p in data["pantallas"]:
                if isinstance(p, str):
                    norm.append({"id": p, "modo": "edicion"})
                else:
                    norm.append(p)
            data["pantallas"] = norm
        return data


class Conexion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    de: str
    a: str
    cuando: Optional[Condicion] = None


class Flujo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tareas: list[Tarea]
    conexiones: list[Conexion] = []

    def tarea_de_pantalla(self, pantalla_id: str) -> Optional[Tarea]:
        """La tarea DUEÑA de una pantalla: la que la tiene como ultimo paso.
        Otra tarea puede ensenarla antes en visualizacion, y esa no es la suya.
        Si ninguna la tiene al final, la primera que la muestre."""
        for t in self.tareas:
            if t.pantallas and t.pantallas[-1].id == pantalla_id:
                return t
        for t in self.tareas:
            if any(p.id == pantalla_id for p in t.pantallas):
                return t
        return None


class Accion(BaseModel):
    model_config = ConfigDict(extra="allow")
    tipo: Literal["folio", "costo", "documento", "notificacion"]
    nombre: str
    firmador_nombre: Optional[str] = None
    firmador_cargo: Optional[str] = None
    titulo: Optional[str] = None
    subtitulo: Optional[str] = None


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
        nombres_accion = {a.nombre for a in self.acciones}
        ids_tarea = {t.id for t in self.flujo.tareas}
        for t in self.flujo.tareas:
            if t.actor is not None and t.actor not in ids_actor:
                raise ValueError(f"la tarea '{t.id}' usa un actor no declarado: '{t.actor}'")
            for paso in t.pantallas:
                if paso.id not in ids_pantalla:
                    raise ValueError(
                        f"la tarea '{t.id}' referencia una pantalla inexistente: '{paso.id}'"
                    )
            for acc in t.acciones_antes + t.acciones_despues:
                if acc not in nombres_accion:
                    raise ValueError(f"la tarea '{t.id}' pide una accion inexistente: '{acc}'")

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
            if cx.cuando:
                for campo in [cx.cuando.campo, *(c.campo for c in cx.cuando.y)]:
                    if campo not in nombres_campo:
                        raise ValueError(
                            f"la condicion de '{cx.de}' usa un campo no declarado: '{campo}'"
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
