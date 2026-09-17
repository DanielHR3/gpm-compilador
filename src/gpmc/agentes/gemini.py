"""Proveedor para pruebas: Google AI Studio (Gemini). Import perezoso del SDK.

OJO: el nivel de estudio puede usar los datos para mejorar sus modelos. Por
decision de la Direccion (spec, punto abierto 1), las pruebas con este
proveedor usan los expedientes de ejemplo del repositorio, no los reales.
"""
import json
import time

from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida, Respuesta


def _esquema_gemini(esquema):
    """JSON Schema estandar -> el dialecto que acepta `response_schema` de Gemini.

    El SDK valida el esquema con pydantic ANTES de llamar a la red y rechaza los
    tipos union: `"type": ["string", "null"]` y `anyOf: [null, X]`. Gemini
    expresa lo mismo con `nullable: true` y un solo `type`. OpenAI si acepta el
    estandar, asi que `prompt.py` se queda con el estandar y aqui se traduce.
    Devuelve una copia; no muta el original. Lo destapo la primera llamada
    real: ProveedorFalso no podia verlo.
    """
    if isinstance(esquema, list):
        return [_esquema_gemini(e) for e in esquema]
    if not isinstance(esquema, dict):
        return esquema
    e = {k: _esquema_gemini(v) for k, v in esquema.items()}
    if isinstance(e.get("type"), list):
        tipos = [t for t in e["type"] if t != "null"]
        if len(tipos) == 1 and len(tipos) < len(e["type"]):
            e["type"], e["nullable"] = tipos[0], True
    if "anyOf" in e:
        ramas = e.pop("anyOf")
        no_nulas = [r for r in ramas if r.get("type") != "null"]
        if len(no_nulas) == 1 and len(no_nulas) < len(ramas):
            base = dict(no_nulas[0]); base["nullable"] = True
            e = {**base, **{k: v for k, v in e.items() if k not in base}}
        else:
            e["anyOf"] = ramas
    return e


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
                    response_schema=_esquema_gemini(esquema),
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
