"""Proveedor para pruebas: Google AI Studio (Gemini). Import perezoso del SDK.

OJO: el nivel de estudio puede usar los datos para mejorar sus modelos. Por
decision de la Direccion (spec, punto abierto 1), las pruebas con este
proveedor usan los expedientes de ejemplo del repositorio, no los reales.
"""
import json
import logging
import time

from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida, Respuesta, clasificar_error


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


log = logging.getLogger(__name__)


class ProveedorGemini:
    nombre = "gemini"

    def __init__(self, llave: str, modelo: str, timeout_s: float = 60):
        from google import genai  # ImportError -> NingunProveedor
        from google.genai import types
        self._types = types
        self._cliente = genai.Client(api_key=llave, http_options={"timeout": int(timeout_s * 1000)})
        # `modelo` puede ser una lista separada por comas: el primero es el
        # principal y los demas, el respaldo en ese orden (ver `completar`).
        self._modelos = [m.strip() for m in modelo.split(",") if m.strip()] or [modelo]
        self._modelo = self._modelos[0]

    def _generar(self, modelo: str, instrucciones: str, contexto: str, esquema: dict):
        return self._cliente.models.generate_content(
            model=modelo,
            contents=contexto,
            config=self._types.GenerateContentConfig(
                system_instruction=instrucciones,
                response_mime_type="application/json",
                response_schema=_esquema_gemini(esquema),
                temperature=0.1,
            ),
        )

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta:
        t0 = time.monotonic()
        # Respaldo entre modelos. La tarde del 2026-09-24, con la cuenta
        # gratuita, 3.8 y 3.7 daban 503 por saturacion, 3.5 se quedo sin cuota
        # del dia y 3.6 contestaba; a los cinco minutos era al reves. Ante un
        # error PASAJERO (503, 429...) se prueba el siguiente de la lista en la
        # misma llamada: un 503 no consume cuota, y esperar 2 y 8 s contra un
        # modelo saturado era pedirle otro 503. Un error de configuracion
        # (llave invalida, modelo inexistente) no va a mejorar con otro modelo:
        # se corta ahi. Solo si TODOS fallan se propaga el ErrorDeRed, y ahi
        # aplican los reintentos de siempre.
        ultimo = None
        r = None
        for i, modelo in enumerate(self._modelos):
            try:
                r = self._generar(modelo, instrucciones, contexto, esquema)
                break
            except Exception as e:  # el SDK no expone una jerarquia estable, pero si el codigo
                ultimo = clasificar_error(e)
                if not isinstance(ultimo, ErrorDeRed):
                    raise ultimo
                # Sin esto solo la bitacora sabe quien contesto, y no por que.
                siguiente = self._modelos[i + 1] if i + 1 < len(self._modelos) else None
                log.warning("gemini %s fallo (%s); %s", modelo, str(ultimo)[:120],
                            f"se pasa a {siguiente}" if siguiente else "no queda respaldo")
        if r is None:
            raise ultimo
        texto = r.text or ""
        try:
            json.loads(texto)
        except ValueError:
            raise RespuestaInvalida("no es JSON")
        uso = getattr(r, "usage_metadata", None)
        # `modelVersion` es la version que de verdad contesto. Con un alias como
        # `gemini-flash-latest`, es lo unico que permite saber despues que modelo
        # produjo una propuesta: la demostrabilidad que pide la Licencia AI.
        return Respuesta(texto=texto,
                         tokens_entrada=getattr(uso, "prompt_token_count", None),
                         tokens_salida=getattr(uso, "candidates_token_count", None),
                         modelo=getattr(r, "model_version", None) or self._modelo,
                         duracion_ms=int((time.monotonic() - t0) * 1000))
