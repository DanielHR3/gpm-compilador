"""Fase 3: Diccionario y TO-BE propuestos desde el AS-IS.

Todo lo que sale de aqui es un BORRADOR que una persona acepta, corrige o
declina por documento. Este modulo no escribe en la sesion: devuelve un
`Generados` y la API lo persiste. El verificador es el extractor de siempre
mas tres cruces deterministas (`verificar_fase3`): nadie opina, se mide.
"""
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from gpmc.agentes.bitacora import Interaccion, registrar
from gpmc.agentes.dic08 import ESPERAS_REINTENTO
from gpmc.agentes import prompt_fase3 as pr
from gpmc.agentes.proveedor import ErrorDeProveedor, ErrorDeRed, RespuestaInvalida
from gpmc.agentes.verificar_fase3 import verificar_cruzado
from gpmc.extractores import metadatos as ext_meta
from gpmc.extractores.expediente import extraer_expediente
from gpmc.nucleo.huecos import Hueco, HuecoOut, bloquean

log = logging.getLogger("gpmc.agentes.fase3")

# Regla de la Direccion del 2026-09-17: Gemini solo con `ejemplos/expedientes/`;
# lo real, con la licencia de Planeacion. El AS-IS completo viaja al proveedor,
# asi que el candado vive en el codigo y no en la memoria de nadie.
PROVEEDOR_CON_LICENCIA = "openai"

MOTIVO_SIN_LICENCIA = (
    "El proveedor de IA configurado no tiene licencia para expedientes reales. "
    "Las propuestas solo se generan con la licencia de Planeación; mientras "
    "tanto, sube el Diccionario y el TO-BE que tengas."
)

# Mismos nombres que `web.sesiones.INSUMOS`. Se repiten porque agentes/ no
# importa de web/; `test_nombres_de_insumo_coinciden_con_la_web` los ata.
NOMBRES_INSUMO = {
    "as_is": "Análisis AS-IS.md",
    "tobe": "Propuesta TO-BE.md",
    "diccionario": "Diccionario de Datos.md",
}

Decision = Literal["pendiente", "aceptada", "corregida", "declinada"]


class Documento(BaseModel):
    texto: str
    version_prompt: str
    ronda: int
    huecos: list = []                 # list[HuecoOut]
    decision: Decision = "pendiente"


class Generados(BaseModel):
    estado: Literal["generando", "listo", "error", "sin_licencia"]
    motivo: Optional[str] = None
    nombre: Optional[str] = None      # del AS-IS, si metadatos lo da
    diccionario: Optional[Documento] = None
    tobe: Optional[Documento] = None


def puede_generar(entorno: Optional[dict] = None) -> Optional[str]:
    """None si se puede generar; si no, el motivo en palabras."""
    e = dict(os.environ) if entorno is None else entorno
    if e.get("GPMC_IA_PROVEEDOR") == PROVEEDOR_CON_LICENCIA and e.get("GPMC_IA_LLAVE"):
        return None
    return MOTIVO_SIN_LICENCIA


# A que documento se le atribuye cada hueco: decide que borrador se mejora y
# bajo que tarjeta se muestra. Lo que no es claramente del TO-BE va al
# Diccionario, que es el documento del que sale casi todo.
_DEL_TOBE = ("MMD-", "FLU-", "INS-01")


def atribuir(h: Hueco) -> str:
    return "tobe" if h.codigo.startswith(_DEL_TOBE) else "diccionario"


def extraer_borradores(as_is: str, diccionario: str, tobe: str):
    """Corre el extractor sobre una carpeta temporal con los tres textos y
    suma la verificacion cruzada. Devuelve (manifiesto_o_None, huecos)."""
    with tempfile.TemporaryDirectory(prefix="gpmc-fase3-") as d:
        carpeta = Path(d)
        (carpeta / NOMBRES_INSUMO["as_is"]).write_text(as_is, encoding="utf-8")
        (carpeta / NOMBRES_INSUMO["diccionario"]).write_text(diccionario, encoding="utf-8")
        (carpeta / NOMBRES_INSUMO["tobe"]).write_text(tobe, encoding="utf-8")
        r = extraer_expediente(carpeta)
    return r.manifiesto, list(r.huecos) + verificar_cruzado(as_is, tobe, r.manifiesto)


def _llamar(proveedor, instruccion: str, contexto: str, esquema: dict):
    """Hasta tres intentos, SOLO ante ErrorDeRed (mismo criterio que dic08)."""
    ultimo: Optional[Exception] = None
    for espera in (0.0, *ESPERAS_REINTENTO):
        if espera:
            time.sleep(espera)
        try:
            return proveedor.completar(instruccion, contexto, esquema)
        except ErrorDeRed as exc:
            ultimo = exc
    raise ultimo


def _pedir(proveedor, raiz: Path, sid: str, documento: str, ronda: int,
           instruccion: str, version: str, contexto: str) -> str:
    """Una llamada al modelo con su linea en la bitacora. Devuelve el texto
    del documento (el unico campo del esquema)."""
    it = Interaccion(sid=sid, proveedor=proveedor.nombre, modelo="", version_prompt=version,
                     solicitud={"n_caracteres": len(contexto)}, instruccion_hash=pr.hash_de(instruccion),
                     estado="procesada", documento=documento, ronda=ronda)
    try:
        resp = _llamar(proveedor, instruccion, contexto, pr.esquema_de(documento))
    except (ErrorDeRed, ErrorDeProveedor) as e:
        it.estado, it.respuesta = "error", str(e)
        it.alertas = ["error_de_red" if isinstance(e, ErrorDeRed) else "error_de_proveedor"]
        registrar(raiz, it)
        raise
    it.modelo, it.respuesta = resp.modelo, resp.texto
    it.tokens_entrada, it.tokens_salida, it.duracion_ms = resp.tokens_entrada, resp.tokens_salida, resp.duracion_ms
    try:
        cuerpo = json.loads(resp.texto)
        texto = cuerpo[documento]
        if not isinstance(texto, str):
            raise TypeError("no es texto")
    except (TypeError, ValueError, KeyError) as e:
        it.estado, it.alertas = "error", ["respuesta_invalida"]
        registrar(raiz, it)
        raise RespuestaInvalida(str(e))
    registrar(raiz, it)
    return texto


def _por_documento(huecos: list) -> dict:
    salida = {"diccionario": [], "tobe": []}
    for h in huecos:
        salida[atribuir(h)].append(h)
    return salida


def _nombre(as_is: str) -> Optional[str]:
    t = ext_meta.extraer(as_is).tramite
    return t.nombre if t is not None and t.nombre != "[por confirmar]" else None


def generar(as_is: str, proveedor, raiz: Path, sid: str, mejorar: bool = True) -> Generados:
    """AS-IS -> Generados. Nunca propaga: cualquier fallo es `estado: error`
    con el tipo de la excepcion en el motivo (y en el log con traza)."""
    try:
        return _generar(as_is, proveedor, raiz, sid, mejorar)
    except Exception as exc:  # ErrorDeRed, RespuestaInvalida, o un defecto nuestro
        log.error("fase3 sid=%s fallo: %s", sid, type(exc).__name__, exc_info=exc)
        return Generados(estado="error", nombre=_nombre(as_is),
                         motivo=f"No se pudieron generar las propuestas. ({type(exc).__name__})")


def _generar(as_is: str, proveedor, raiz: Path, sid: str, mejorar: bool) -> Generados:
    dicc = _pedir(proveedor, raiz, sid, "diccionario", 1, pr.INSTRUCCION_DICC,
                  pr.VERSION_PROMPT_DICC, pr.contexto_dicc(as_is))
    tobe = _pedir(proveedor, raiz, sid, "tobe", 1, pr.INSTRUCCION_TOBE,
                  pr.VERSION_PROMPT_TOBE, pr.contexto_tobe(as_is, dicc))
    _, huecos = extraer_borradores(as_is, dicc, tobe)
    elegido = {"diccionario": (dicc, 1, pr.VERSION_PROMPT_DICC), "tobe": (tobe, 1, pr.VERSION_PROMPT_TOBE)}
    if mejorar:
        elegido, huecos = _ronda_de_mejora(as_is, proveedor, raiz, sid, elegido, huecos)
    reparto = _por_documento(huecos)
    docs = {}
    for clave, (texto, ronda, version) in elegido.items():
        docs[clave] = Documento(texto=texto, version_prompt=version, ronda=ronda,
                                huecos=[HuecoOut.desde(h) for h in reparto[clave]])
    return Generados(estado="listo", nombre=_nombre(as_is),
                     diccionario=docs["diccionario"], tobe=docs["tobe"])


def _ronda_de_mejora(as_is, proveedor, raiz, sid, elegido, huecos):
    """Se implementa en la Task 4. Por ahora: sin mejora."""
    return elegido, huecos
