"""Contrato con el modelo de lenguaje, y los proveedores que no tocan la red.

Dos implementaciones reales viven aparte (`gemini.py` para pruebas, `openai_.py`
para la licencia de Planeacion) y se importan de forma perezosa: sin el extra
`[agentes]` instalado, este modulo sigue importando y `hay_proveedor()` es False.
"""
import os
import time
from typing import Optional, Protocol

from pydantic import BaseModel


class Respuesta(BaseModel):
    texto: str
    tokens_entrada: Optional[int] = None
    tokens_salida: Optional[int] = None
    modelo: str
    duracion_ms: int


class ProveedorNoDisponible(Exception):
    """No hay proveedor configurado. Nunca es un error para el usuario."""


class RespuestaInvalida(Exception):
    """El modelo devolvio algo que no es JSON conforme al esquema. No se reintenta."""


class ErrorDeRed(Exception):
    """Timeout, red o 5xx del proveedor. Se reintenta una vez."""


class Proveedor(Protocol):
    nombre: str

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta: ...


class NingunProveedor:
    nombre = "ninguno"

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta:
        raise ProveedorNoDisponible("no hay proveedor de IA configurado")


class ProveedorFalso:
    """Devuelve textos de guion, en orden. Es el unico proveedor que ven las
    pruebas. Un guion agotado se comporta como un fallo de red, para probar
    reintentos sin red."""
    nombre = "falso"

    def __init__(self, respuestas: list, modelo: str = "falso"):
        self._respuestas = list(respuestas)
        self._modelo = modelo
        self.llamadas = 0
        self.ultimo_contexto: Optional[str] = None
        self.ultimas_instrucciones: Optional[str] = None

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta:
        self.llamadas += 1
        self.ultimo_contexto = contexto
        self.ultimas_instrucciones = instrucciones
        if not self._respuestas:
            raise ErrorDeRed("guion agotado")
        t0 = time.monotonic()
        texto = self._respuestas.pop(0)
        return Respuesta(texto=texto, tokens_entrada=len(contexto) // 4,
                         tokens_salida=len(texto) // 4, modelo=self._modelo,
                         duracion_ms=int((time.monotonic() - t0) * 1000))


# Alias, no versiones fijas: `gemini-2.5-flash` dejo de ofrecerse a usuarios
# nuevos y el generador murio con 404 la primera vez que se llamo de verdad.
# La version exacta que contesta se registra en la bitacora (ver dic08.py).
MODELO_POR_OMISION = {"gemini": "gemini-flash-latest", "openai": "gpt-4o"}


def _entorno(entorno: Optional[dict]) -> dict:
    return dict(os.environ) if entorno is None else entorno


def hay_proveedor(entorno: Optional[dict] = None) -> bool:
    e = _entorno(entorno)
    if e.get("GPMC_IA_PROVEEDOR") not in MODELO_POR_OMISION or not e.get("GPMC_IA_LLAVE"):
        return False
    return not isinstance(crear_proveedor(entorno=e), NingunProveedor)


def crear_proveedor(entorno: Optional[dict] = None) -> Proveedor:
    """Lee GPMC_IA_PROVEEDOR / GPMC_IA_LLAVE / GPMC_IA_MODELO / GPMC_IA_TIMEOUT_S.
    Sin variables, proveedor desconocido o extra sin instalar -> NingunProveedor."""
    e = _entorno(entorno)
    nombre = e.get("GPMC_IA_PROVEEDOR", "")
    llave = e.get("GPMC_IA_LLAVE", "")
    if nombre not in MODELO_POR_OMISION or not llave:
        return NingunProveedor()
    modelo = e.get("GPMC_IA_MODELO") or MODELO_POR_OMISION[nombre]
    timeout = float(e.get("GPMC_IA_TIMEOUT_S", "60"))
    try:
        if nombre == "gemini":
            from gpmc.agentes.gemini import ProveedorGemini
            return ProveedorGemini(llave=llave, modelo=modelo, timeout_s=timeout)
        from gpmc.agentes.openai_ import ProveedorOpenAI
        return ProveedorOpenAI(llave=llave, modelo=modelo, timeout_s=timeout)
    except ImportError:
        return NingunProveedor()
