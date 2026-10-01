"""El agente que completa la comparativa de antes y despues.

Dos llamadas por tramite: la evidencia de los lados que el compilador no supo
contar, y los puntos de mejora. Propone; no decide ni escribe en la sesion:
devuelve un `Analisis` y la API lo persiste. Nunca propaga: si algo falla, la
comparativa se queda con lo que ya contaba el compilador.
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from gpmc.agentes import prompt_comparativa as prompt
from gpmc.agentes.bitacora import Interaccion, registrar
from gpmc.agentes.dic08 import ESPERAS_REINTENTO
from gpmc.agentes.proveedor import ErrorDeProveedor, ErrorDeRed, RespuestaInvalida
from gpmc.agentes.verificar_comparativa import verificar_evidencia, verificar_mejoras
from gpmc.comparativa.documentos import referencias
from gpmc.comparativa.propuestas import mejoras_a_dicts, propuestas_a_dicts
from gpmc.nucleo import integraciones
from gpmc.nucleo.manifiesto import Manifiesto

log = logging.getLogger("gpmc.agentes.comparativa")

MOTIVO_RED = ("No se pudo consultar al modelo (red o cuota). La comparativa muestra lo que "
              "contó el compilador; puedes volver a intentarlo o escribir los datos a mano.")
MOTIVO_INVALIDA = ("El modelo contestó algo que no se pudo leer. La comparativa muestra lo "
                   "que contó el compilador; puedes volver a intentarlo.")
MOTIVO_INESPERADO = ("El análisis falló. La comparativa muestra lo que contó el compilador; "
                     "puedes volver a intentarlo.")
MOTIVO_SIN_MEJORAS = ("Las cifras se completaron, pero no se pudieron obtener los puntos de "
                      "mejora. Vuelve a analizar para intentarlo de nuevo.")


class Analisis(BaseModel):
    estado: str
    motivo: Optional[str] = None
    propuestas: list = []
    mejoras: list = []
    alertas: list = []
    modelo: str = ""


class _SinRespuesta(Exception):
    """La llamada no dio nada que verificar. `de_red` dice si vale la pena
    seguir gastando cuota en la siguiente."""

    def __init__(self, de_red: bool):
        super().__init__()
        self.de_red = de_red


def _servicios() -> list:
    """Solo el catalogo publico: lo de pago o convenio (`PROPUESTAS`) no se le
    ofrece al modelo como si la plataforma pudiera consultarlo hoy."""
    return [(k, c.descripcion or c.proveedor) for k, c in integraciones.CATALOGOS.items()]


def _llamar(proveedor, instruccion: str, datos: str, esquema: dict):
    """Hasta tres intentos, SOLO ante ErrorDeRed (ver `dic08._llamar`)."""
    ultimo: Optional[Exception] = None
    for espera in (0.0, *ESPERAS_REINTENTO):
        if espera:
            time.sleep(espera)
        try:
            return proveedor.completar(instruccion, datos, esquema)
        except ErrorDeRed as exc:
            ultimo = exc
    raise ultimo


def _lista(texto: str, llave: str) -> list:
    try:
        d = json.loads(texto)
    except (TypeError, ValueError) as e:
        raise RespuestaInvalida(str(e))
    if not isinstance(d, dict) or not isinstance(d.get(llave), list):
        raise RespuestaInvalida(f"sin lista '{llave}'")
    return d[llave]


def _consultar(proveedor, raiz: Path, it: Interaccion, instruccion: str, datos: str,
               esquema: dict, llave: str) -> tuple:
    """(items, modelo). Deja la interaccion lista para registrar; si la
    llamada no sirve, la registra como error y lanza `_SinRespuesta`."""
    try:
        resp = _llamar(proveedor, instruccion, datos, esquema)
    except (ErrorDeRed, ErrorDeProveedor) as e:
        it.estado, it.respuesta = "error", str(e)
        it.alertas.append("error_de_red" if isinstance(e, ErrorDeRed) else "error_de_proveedor")
        registrar(raiz, it)
        raise _SinRespuesta(de_red=True)
    it.modelo, it.respuesta = resp.modelo, resp.texto
    it.tokens_entrada, it.tokens_salida, it.duracion_ms = (
        resp.tokens_entrada, resp.tokens_salida, resp.duracion_ms)
    try:
        return _lista(resp.texto, llave), resp.modelo
    except RespuestaInvalida:
        it.estado = "error"
        it.alertas.append("respuesta_invalida")
        registrar(raiz, it)
        raise _SinRespuesta(de_red=False)


def _cerrar(raiz: Path, it: Interaccion, de_verificar: list) -> None:
    it.alertas += de_verificar
    if de_verificar:
        it.estado = "sujeta_a_validacion"
    registrar(raiz, it)


def analizar(as_is: str, to_be: str, m: Manifiesto, faltan: list, proveedor, raiz: Path,
             sid: str, avisar=None, usuario: str = "anonimo") -> Analisis:
    """`faltan` son los (metrica, lado) que la comparativa no pudo llenar
    (`armar.lados_sin_dato`)."""
    avisar = avisar or (lambda _: None)
    try:
        return _analizar(as_is, to_be, m, list(faltan or []), proveedor, Path(raiz), sid,
                         avisar, usuario)
    except Exception as exc:  # noqa: BLE001 — corre en segundo plano: nada debe escapar
        log.error("comparativa sid=%s fallo: %s", sid, type(exc).__name__, exc_info=exc)
        return Analisis(estado="error", motivo=MOTIVO_INESPERADO, alertas=[type(exc).__name__])


def _interaccion(proveedor, sid: str, usuario: str, version: str, documento: str,
                 instruccion: str, solicitud: dict, recortado: bool) -> Interaccion:
    return Interaccion(
        sid=sid, usuario=usuario, proveedor=proveedor.nombre, modelo="",
        version_prompt=version, documento=documento, solicitud=solicitud,
        instruccion_hash=prompt.hash_de(instruccion), estado="procesada",
        alertas=["contexto_recortado"] if recortado else [])


def _analizar(as_is, to_be, m, faltan, proveedor, raiz, sid, avisar, usuario) -> Analisis:
    a = Analisis(estado="lista")
    contestaron = 0

    if faltan:
        datos, recortado = prompt.contexto_evidencia(as_is, to_be, faltan)
        it = _interaccion(proveedor, sid, usuario, prompt.VERSION_EVIDENCIA, "comparativa",
                          prompt.INSTRUCCION_EVIDENCIA,
                          {"n_lados": len(faltan), "n_caracteres": len(datos)}, recortado)
        avisar("Leyendo el AS-IS y el TO-BE para completar las cifras que faltan")
        try:
            items, a.modelo = _consultar(proveedor, raiz, it, prompt.INSTRUCCION_EVIDENCIA,
                                         datos, prompt.ESQUEMA_EVIDENCIA, "lados")
        except _SinRespuesta as e:
            a.alertas += it.alertas
            if e.de_red:
                # Con la red o la cuota caidas, la segunda llamada fallaria igual.
                return Analisis(estado="error", motivo=MOTIVO_RED, alertas=a.alertas)
        else:
            contestaron += 1
            avisar("Comprobando cada frase contra el expediente")
            propuestas, de_verificar = verificar_evidencia(items, as_is, to_be, faltan)
            _cerrar(raiz, it, de_verificar)
            a.propuestas = propuestas_a_dicts(propuestas)
            a.alertas += it.alertas

    refs = referencias(m)
    datos, recortado = prompt.contexto_mejoras(as_is, to_be, refs, _servicios())
    it = _interaccion(proveedor, sid, usuario, prompt.VERSION_MEJORAS, "mejoras",
                      prompt.INSTRUCCION_MEJORAS,
                      {"n_referencias": len(refs), "n_caracteres": len(datos)}, recortado)
    avisar("Buscando qué más se puede simplificar")
    try:
        items, modelo = _consultar(proveedor, raiz, it, prompt.INSTRUCCION_MEJORAS, datos,
                                   prompt.ESQUEMA_MEJORAS, "mejoras")
    except _SinRespuesta as e:
        a.alertas += it.alertas
        if not contestaron:
            return Analisis(estado="error", motivo=MOTIVO_RED if e.de_red else MOTIVO_INVALIDA,
                            alertas=a.alertas)
        a.alertas.append("mejoras_no_disponibles")
        a.motivo = MOTIVO_SIN_MEJORAS
        return a
    a.modelo = a.modelo or modelo
    mejoras, de_verificar = verificar_mejoras(items, as_is, to_be, refs,
                                              integraciones.CATALOGOS.keys())
    _cerrar(raiz, it, de_verificar)
    a.mejoras = mejoras_a_dicts(mejoras)
    a.alertas += it.alertas
    return a
