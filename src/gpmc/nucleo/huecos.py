"""Hueco: lo que el extractor no pudo derivar de los insumos, dicho en voz alta.

Distinto de validador.reglas.Hallazgo: aquel describe defectos estructurales de
un .gpm ya compilado; este describe faltantes en la materia prima (AS-IS, TO-BE,
Diccionario) que una persona debe resolver antes de compilar.
"""

from dataclasses import dataclass
from typing import Optional

# El orden es deliberado: de lo que impide compilar a lo que solo conviene mirar.
NIVELES = ("bloqueante", "falta_dato", "por_confirmar")
ORDEN_NIVEL = {nivel: i for i, nivel in enumerate(NIVELES)}


@dataclass
class Hueco:
    nivel: str            # uno de NIVELES
    codigo: str           # estable: INS-01, DIC-01, META-01, FLU-01, MMD-01, ...
    ubicacion: str        # "p1", "flujo", "metadatos", "" (vacío = general)
    mensaje: str          # texto para una persona, con acentos
    propuesta: Optional[str] = None   # valor que el extractor sugirió (DIC-01)

    def __str__(self) -> str:
        pre = f"[{self.codigo}] " if self.codigo else ""
        loc = f"{self.ubicacion}: " if self.ubicacion else ""
        return f"{pre}{loc}{self.mensaje}"
