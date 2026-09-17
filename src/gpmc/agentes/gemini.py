"""Proveedor para pruebas: Google AI Studio (Gemini). Import perezoso del SDK.

OJO: el nivel de estudio puede usar los datos para mejorar sus modelos. Por
decision de la Direccion (spec, punto abierto 1), las pruebas con este
proveedor usan los expedientes de ejemplo del repositorio, no los reales.
"""
import json
import time

from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida, Respuesta


class ProveedorGemini:
    nombre = "gemini"

    def __init__(self, llave: str, modelo: str, timeout_s: float = 60):
        from google import genai  # ImportError -> NingunProveedor
        from google.genai import types
        self._types = types
        self._cliente = genai.Client(api_key=llave, http_options={"timeout": int(timeout_s * 1000)})
        self._modelo = modelo

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta:
        t0 = time.monotonic()
        try:
            r = self._cliente.models.generate_content(
                model=self._modelo,
                contents=contexto,
                config=self._types.GenerateContentConfig(
                    system_instruction=instrucciones,
                    response_mime_type="application/json",
                    response_schema=esquema,
                    temperature=0.1,
                ),
            )
        except Exception as e:  # red, timeout, 5xx: el SDK no expone una jerarquia estable
            raise ErrorDeRed(str(e))
        texto = r.text or ""
        try:
            json.loads(texto)
        except ValueError:
            raise RespuestaInvalida("no es JSON")
        uso = getattr(r, "usage_metadata", None)
        return Respuesta(texto=texto,
                         tokens_entrada=getattr(uso, "prompt_token_count", None),
                         tokens_salida=getattr(uso, "candidates_token_count", None),
                         modelo=self._modelo, duracion_ms=int((time.monotonic() - t0) * 1000))
