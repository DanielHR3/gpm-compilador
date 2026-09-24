"""Fase 3: Diccionario y TO-BE propuestos desde el AS-IS.

Todo lo que sale de aqui es un BORRADOR que una persona acepta, corrige o
declina por documento. Este modulo no escribe en la sesion: devuelve un
`Generados` y la API lo persiste.
"""
import os
from typing import Optional

# Regla de la Direccion del 2026-09-17: Gemini solo con `ejemplos/expedientes/`;
# lo real, con la licencia de Planeacion. El AS-IS completo viaja al proveedor,
# asi que el candado vive en el codigo y no en la memoria de nadie.
PROVEEDOR_CON_LICENCIA = "openai"

MOTIVO_SIN_LICENCIA = (
    "El proveedor de IA configurado no tiene licencia para expedientes reales. "
    "Las propuestas solo se generan con la licencia de Planeación; mientras "
    "tanto, sube el Diccionario y el TO-BE que tengas."
)


def puede_generar(entorno: Optional[dict] = None) -> Optional[str]:
    """None si se puede generar; si no, el motivo en palabras."""
    e = dict(os.environ) if entorno is None else entorno
    if e.get("GPMC_IA_PROVEEDOR") == PROVEEDOR_CON_LICENCIA and e.get("GPMC_IA_LLAVE"):
        return None
    return MOTIVO_SIN_LICENCIA
