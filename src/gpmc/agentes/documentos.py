"""El agente que propone que paso con cada documento del tramite.

Una llamada por tramite, a peticion. Propone; no decide ni escribe en la
sesion: devuelve un `Analisis` y la API lo persiste. Nunca propaga: si algo
falla, el resultado trae el inventario del lector para que la persona siga a
mano.
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from gpmc.agentes import prompt_documentos as prompt
from gpmc.agentes.bitacora import Interaccion, registrar
from gpmc.agentes.dic08 import ESPERAS_REINTENTO
from gpmc.agentes.proveedor import ErrorDeProveedor, ErrorDeRed, RespuestaInvalida
from gpmc.agentes.verificar_documentos import verificar
from gpmc.comparativa.documentos import a_dicts, inventario_determinista, referencias
from gpmc.nucleo.manifiesto import Manifiesto

log = logging.getLogger("gpmc.agentes.documentos")

MOTIVO_RED = ("No se pudo consultar al modelo (red o cuota). Puedes asignar el destino de "
              "cada documento a mano, o volver a intentarlo.")
MOTIVO_INVALIDA = ("El modelo contestó algo que no se pudo leer. Puedes asignar el destino "
                   "de cada documento a mano.")
MOTIVO_INESPERADO = "El análisis falló. Puedes asignar el destino de cada documento a mano."


class Analisis(BaseModel):
    estado: str
    motivo: Optional[str] = None
    documentos: list = []
    origen: str = "agente"
    alertas: list = []


def _llamar(proveedor, datos: str):
    """Hasta tres intentos, SOLO ante ErrorDeRed (ver `dic08._llamar`)."""
    ultimo: Optional[Exception] = None
    for espera in (0.0, *ESPERAS_REINTENTO):
        if espera:
            time.sleep(espera)
        try:
            return proveedor.completar(prompt.INSTRUCCION, datos, prompt.ESQUEMA)
        except ErrorDeRed as exc:
            ultimo = exc
    raise ultimo


def _parsear(texto: str) -> list:
    try:
        d = json.loads(texto)
    except (TypeError, ValueError) as e:
        raise RespuestaInvalida(str(e))
    if not isinstance(d, dict) or not isinstance(d.get("documentos"), list):
        raise RespuestaInvalida("sin lista 'documentos'")
    return d["documentos"]


def _a_mano(as_is: str, m: Manifiesto, motivo: str, alertas: list) -> Analisis:
    return Analisis(estado="error", motivo=motivo, origen="lector", alertas=alertas,
                    documentos=a_dicts(inventario_determinista(as_is, m)))


def analizar(as_is: str, to_be: str, m: Manifiesto, proveedor, raiz: Path, sid: str,
             avisar=None, usuario: str = "anonimo") -> Analisis:
    avisar = avisar or (lambda _: None)
    try:
        return _analizar(as_is, to_be, m, proveedor, Path(raiz), sid, avisar, usuario)
    except Exception as exc:  # noqa: BLE001 — corre en segundo plano: nada debe escapar
        log.error("documentos sid=%s fallo: %s", sid, type(exc).__name__, exc_info=exc)
        return _a_mano(as_is, m, MOTIVO_INESPERADO, [type(exc).__name__])


def _analizar(as_is, to_be, m, proveedor, raiz, sid, avisar, usuario) -> Analisis:
    refs = referencias(m)
    datos, recortado = prompt.contexto(as_is, to_be, refs)
    alertas = ["contexto_recortado"] if recortado else []
    it = Interaccion(
        sid=sid, usuario=usuario, proveedor=proveedor.nombre, modelo="",
        version_prompt=prompt.VERSION_PROMPT, documento="documentos",
        solicitud={"n_referencias": len(refs), "n_caracteres": len(datos)},
        instruccion_hash=prompt.hash_instruccion(), estado="procesada", alertas=list(alertas))

    avisar("Leyendo el AS-IS y el TO-BE")
    try:
        resp = _llamar(proveedor, datos)
    except (ErrorDeRed, ErrorDeProveedor) as e:
        it.estado, it.respuesta = "error", str(e)
        it.alertas.append("error_de_red" if isinstance(e, ErrorDeRed) else "error_de_proveedor")
        registrar(raiz, it)
        return _a_mano(as_is, m, MOTIVO_RED, it.alertas)
    it.modelo, it.respuesta = resp.modelo, resp.texto
    it.tokens_entrada, it.tokens_salida, it.duracion_ms = (
        resp.tokens_entrada, resp.tokens_salida, resp.duracion_ms)

    try:
        items = _parsear(resp.texto)
    except RespuestaInvalida:
        it.estado = "error"
        it.alertas.append("respuesta_invalida")
        registrar(raiz, it)
        return _a_mano(as_is, m, MOTIVO_INVALIDA, it.alertas)

    avisar(f"Comprobando {len(items)} documentos contra el expediente")
    docs, de_verificar = verificar(items, as_is, to_be, refs)
    it.alertas += de_verificar
    if de_verificar:
        it.estado = "sujeta_a_validacion"
    registrar(raiz, it)
    return Analisis(estado="lista", documentos=a_dicts(docs), alertas=it.alertas)
