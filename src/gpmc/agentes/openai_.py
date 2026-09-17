"""Proveedor de la licencia de Planeacion (OpenAI API directa, GPT-4o).
Import perezoso del SDK. El nombre de modulo lleva guion bajo para no
sombrear al paquete `openai`."""
import json
import time

from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida, Respuesta


class ProveedorOpenAI:
    nombre = "openai"

    def __init__(self, llave: str, modelo: str, timeout_s: float = 60):
        from openai import OpenAI  # ImportError -> NingunProveedor
        self._cliente = OpenAI(api_key=llave, timeout=timeout_s, max_retries=0)
        self._modelo = modelo

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta:
        t0 = time.monotonic()
        try:
            r = self._cliente.chat.completions.create(
                model=self._modelo, temperature=0.1,
                messages=[{"role": "system", "content": instrucciones},
                          {"role": "user", "content": contexto}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "propuestas_dic08", "schema": esquema, "strict": False}},
            )
        except Exception as e:
            raise ErrorDeRed(str(e))
        texto = (r.choices[0].message.content or "") if r.choices else ""
        try:
            json.loads(texto)
        except ValueError:
            raise RespuestaInvalida("no es JSON")
        uso = getattr(r, "usage", None)
        return Respuesta(texto=texto,
                         tokens_entrada=getattr(uso, "prompt_tokens", None),
                         tokens_salida=getattr(uso, "completion_tokens", None),
                         modelo=self._modelo, duracion_ms=int((time.monotonic() - t0) * 1000))
