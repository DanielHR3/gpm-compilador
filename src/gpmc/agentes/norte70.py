"""Proveedor de la licencia de Planeacion a traves de la plataforma del
proveedor (Grupo Norte 70, `api-licencias.norte70.com`).

La Comision no tiene llave propia de OpenAI: la plataforma la guarda y hace de
intermediario. Lo que cambia frente a `openai_.py`, visto el 2026-10-13 con la
consola «Peticiones API» de la plataforma:

- El cuerpo es `{user_query, id_user, systemName, id_conversation}`. No hay
  rol de sistema por peticion: las instrucciones de rol viven en el campo
  «Prompt del Sistema (IA)» de cada sistema dado de alta en la plataforma, y
  sin el contesta 400 «No se ha configurado un prompt para el sistema».
  Por eso instrucciones, esquema y contexto viajan juntos en `user_query`.
- No hay `response_format`: el JSON se pide en el texto y se valida aqui.
- No devuelve tokens de entrada ni de salida, solo el saldo (`remainingUses`).
  El consumo de la llamada se obtiene por diferencia con el saldo anterior.
- El JWT dura 3 horas y se obtiene con Basic Auth en `/token/generate`.

Solo biblioteca estandar: no agrega dependencias al extra `[agentes]`.
"""
import base64
import json
import re
import time
import urllib.error
import urllib.request
from typing import Optional

from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida, Respuesta, clasificar_error

URL_POR_OMISION = "https://api-licencias.norte70.com"

# El JWT dura 3 horas; se renueva antes para no estrenar uno vencido a media
# llamada.
VIGENCIA_TOKEN_S = 2.5 * 3600


class _ErrorHttp(Exception):
    """Lleva el codigo en `status_code`, que es lo que lee `clasificar_error`."""

    def __init__(self, status_code: int, mensaje: str):
        super().__init__(f"{status_code}: {mensaje}")
        self.status_code = status_code


def _sin_cerca(texto: str) -> str:
    """GPT-4o a veces envuelve el JSON en ```json ... ``` aunque se le pida que
    no. Sin `response_format` no hay forma de impedirlo del lado del modelo."""
    t = texto.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", t, flags=re.S)
    return m.group(1) if m else t


def armar_consulta(instrucciones: str, contexto: str, esquema: dict) -> str:
    return (f"{instrucciones}\n\n"
            "Responde UNICAMENTE con un objeto JSON valido conforme a este esquema, "
            "sin texto adicional ni bloques de codigo:\n"
            f"{json.dumps(esquema, ensure_ascii=False)}\n\n"
            f"DATOS:\n{contexto}")


class ProveedorNorte70:
    nombre = "norte70"

    def __init__(self, credenciales: str, id_usuario: str, sistema: str,
                 url: str = URL_POR_OMISION, timeout_s: float = 60, modelo: str = "norte70"):
        # `credenciales` es «usuario:contrasena» de la cuenta de la plataforma,
        # tal como lo pide Basic Auth. Viaja en GPMC_IA_LLAVE.
        self._basic = base64.b64encode(credenciales.encode("utf-8")).decode("ascii")
        self._id_usuario = id_usuario
        self._sistema = sistema
        self._url = url.rstrip("/")
        self._timeout = timeout_s
        self._modelo = modelo
        self._token: Optional[str] = None
        self._token_hasta = 0.0
        self.saldo: Optional[int] = None
        self.consumo_ultima: Optional[int] = None

    def _post(self, ruta: str, cuerpo: Optional[dict], cabeceras: dict) -> dict:
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        req = urllib.request.Request(self._url + ruta, data=datos, method="POST",
                                     headers={"Accept": "application/json",
                                              "Content-Type": "application/json", **cabeceras})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            try:
                mensaje = json.loads(e.read().decode("utf-8")).get("message", "")
            except (ValueError, AttributeError):
                mensaje = ""
            raise _ErrorHttp(e.code, str(mensaje) or e.reason)
        except ValueError:
            raise ErrorDeRed("la plataforma no contesto JSON")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ErrorDeRed(str(e))

    def _jwt(self, renovar: bool = False) -> str:
        if renovar or not self._token or time.monotonic() >= self._token_hasta:
            r = self._post("/token/generate", None, {"Authorization": f"Basic {self._basic}"})
            token = r.get("token") or r.get("access_token") or (r.get("data") or {}).get("token")
            if not token:
                raise _ErrorHttp(502, "la plataforma no entrego token")
            self._token, self._token_hasta = token, time.monotonic() + VIGENCIA_TOKEN_S
        return self._token

    def _consultar(self, cuerpo: dict) -> dict:
        try:
            return self._post("/openai/query", cuerpo, {"Authorization": f"Bearer {self._jwt()}"})
        except _ErrorHttp as e:
            if e.status_code != 401:
                raise
            # Token revocado o vencido antes de lo previsto: uno nuevo, una vez.
            return self._post("/openai/query", cuerpo,
                              {"Authorization": f"Bearer {self._jwt(renovar=True)}"})

    def completar(self, instrucciones: str, contexto: str, esquema: dict) -> Respuesta:
        t0 = time.monotonic()
        cuerpo = {"user_query": armar_consulta(instrucciones, contexto, esquema),
                  "id_user": self._id_usuario, "systemName": self._sistema,
                  "id_conversation": None}
        try:
            r = self._consultar(cuerpo)
        except _ErrorHttp as e:
            raise clasificar_error(e)
        texto = _sin_cerca(str(r.get("bot_response") or ""))
        try:
            json.loads(texto)
        except ValueError:
            raise RespuestaInvalida("no es JSON")
        # La plataforma no separa entrada y salida, asi que la bitacora queda
        # sin esos dos campos. El saldo se conserva para medir el consumo por
        # diferencia entre llamadas.
        saldo = r.get("remainingUses")
        self.consumo_ultima = (self.saldo - saldo
                               if isinstance(saldo, int) and self.saldo is not None else None)
        if isinstance(saldo, int):
            self.saldo = saldo
        return Respuesta(texto=texto, tokens_entrada=None, tokens_salida=None,
                         modelo=self._modelo, duracion_ms=int((time.monotonic() - t0) * 1000))
