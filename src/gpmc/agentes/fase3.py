"""Fase 3: Diccionario y TO-BE propuestos desde el AS-IS.

Todo lo que sale de aqui es un BORRADOR que una persona acepta, corrige o
declina por documento. Este modulo no escribe en la sesion: devuelve un
`Generados` y la API lo persiste. El verificador es el extractor de siempre
mas tres cruces deterministas (`verificar_fase3`): nadie opina, se mide.
"""
import json
import logging
import os
import re
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
    # Pantallas y campos ya leidos por el extractor (solo el Diccionario). La
    # SPA los pinta como tarjetas; el Markdown sigue a un clic.
    vista: list = []


class Generados(BaseModel):
    estado: Literal["generando", "listo", "error", "sin_licencia"]
    motivo: Optional[str] = None
    nombre: Optional[str] = None      # del AS-IS, si metadatos lo da
    diccionario: Optional[Documento] = None
    tobe: Optional[Documento] = None
    # Lo que el agente fue haciendo, en palabras y en orden (2026-09-25): la
    # SPA lo pinta mientras espera. Viaja con el resultado para no perderse.
    pasos: list = []


def _sin_aviso(_: str) -> None:
    pass


def modo_pruebas(entorno: Optional[dict] = None) -> bool:
    """El candado abierto a proposito para probar sin la licencia.

    Decision del usuario del 2026-09-24: Simplificacion prueba el camino del
    AS-IS con Gemini mientras Planeacion entrega las credenciales de OpenAI.
    Se enciende SOLO con `GPMC_FASE3_PRUEBAS=1` en el entorno (en el servidor,
    `~/.config/gpmc/entorno`) y con llave del proveedor. Con el proveedor
    de la licencia no es modo de pruebas: es el funcionamiento normal. La SPA
    lo avisa en pantalla mientras este activo: el AS-IS viaja a Gemini.
    """
    e = dict(os.environ) if entorno is None else entorno
    return (e.get("GPMC_FASE3_PRUEBAS") == "1"
            and e.get("GPMC_IA_PROVEEDOR") != PROVEEDOR_CON_LICENCIA
            and bool(e.get("GPMC_IA_PROVEEDOR")) and bool(e.get("GPMC_IA_LLAVE")))


def puede_generar(entorno: Optional[dict] = None) -> Optional[str]:
    """None si se puede generar; si no, el motivo en palabras."""
    e = dict(os.environ) if entorno is None else entorno
    if e.get("GPMC_IA_PROVEEDOR") == PROVEEDOR_CON_LICENCIA and e.get("GPMC_IA_LLAVE"):
        return None
    if modo_pruebas(e):
        return None
    return MOTIVO_SIN_LICENCIA


# A que documento se le atribuye cada hueco: decide que borrador se mejora y
# bajo que tarjeta se muestra. Lo que no es claramente del TO-BE va al
# Diccionario, que es el documento del que sale casi todo.
_DEL_TOBE = ("MMD-", "FLU-", "INS-01", "GEN-02", "GEN-03")


def _condicion_en_palabras(cond, etiquetas: dict, opciones: dict) -> Optional[str]:
    if cond is None:
        return None

    def trozo(c):
        verbo = "es" if c.operador == "==" else "no es"
        valor = opciones.get((c.campo, c.igual), c.igual)
        return f"«{etiquetas.get(c.campo, c.campo)}» {verbo} «{valor}»"
    return " y ".join([trozo(cond), *(trozo(c) for c in cond.y)])


def vista_de(m) -> list:
    """Las pantallas del manifiesto como las ve una persona: actor con su
    nombre, campo con su etiqueta, opciones por etiqueta y la condicion en
    palabras. Sin manifiesto (el extractor no leyo pantallas), lista vacia."""
    if m is None:
        return []
    actores = {a.id: a.nombre for a in m.actores}
    salida = []
    # Una condicion de visibilidad solo puede mirar un campo de la misma
    # pantalla o de una anterior (invariante del proyecto). Con un nombre
    # tecnico repetido (CLAUDE.md §8), el que gana es el mas cercano hacia
    # atras: se recorren las pantallas en orden y cada una sobreescribe.
    etiquetas: dict = {}
    opciones: dict = {}
    for p in m.pantallas:
        for c in p.campos:
            etiquetas[c.nombre] = c.etiqueta or c.nombre
            for o in c.catalogo:
                opciones[(c.nombre, o.valor)] = o.etiqueta
        salida.append({
            "id": p.id, "nombre": p.nombre, "actor": actores.get(p.actor, p.actor),
            "campos": [{"etiqueta": c.etiqueta or c.nombre, "tipo": c.tipo,
                        "obligatorio": c.obligatorio,
                        "opciones": [o.etiqueta for o in c.catalogo],
                        "condicion": _condicion_en_palabras(c.condicion_visible, etiquetas, opciones)}
                       for c in p.campos],
        })
    return salida


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


_ALERTA = {ErrorDeRed: "error_de_red", ErrorDeProveedor: "error_de_proveedor",
           RespuestaInvalida: "respuesta_invalida"}


_NOMBRE_DOC = {"diccionario": "el Diccionario de Datos", "tobe": "la Propuesta TO-BE"}
_DOC_CORTO = {"diccionario": "Diccionario", "tobe": "TO-BE"}


def _pedir(proveedor, raiz: Path, sid: str, documento: str, ronda: int,
           instruccion: str, version: str, contexto: str, avisar=_sin_aviso,
           usuario: str = "anonimo") -> str:
    """Una llamada al modelo —hasta tres intentos, SOLO ante ErrorDeRed, mismo
    criterio que dic08— con UNA linea en la bitacora por intento: cada peticion
    puede cobrarse, y la Licencia AI pide registrar cada interaccion. Devuelve el
    texto del documento (el unico campo del esquema)."""
    def linea() -> Interaccion:
        return Interaccion(sid=sid, proveedor=proveedor.nombre, modelo="", version_prompt=version, usuario=usuario,
                           solicitud={"n_caracteres": len(contexto)},
                           instruccion_hash=pr.hash_de(instruccion), estado="procesada",
                           documento=documento, ronda=ronda)

    resp = None
    esperas = (0.0, *ESPERAS_REINTENTO)
    avisar(f"Redactando {_NOMBRE_DOC[documento]}…" if ronda == 1
           else f"Pidiendo la mejora de {_NOMBRE_DOC[documento]}…")
    for intento, espera in enumerate(esperas):
        if espera:
            avisar(f"Sin respuesta de la red; se reintenta en {espera:.0f} s")
            time.sleep(espera)
        it = linea()
        try:
            resp = proveedor.completar(instruccion, contexto, pr.esquema_de(documento))
            break
        except (ErrorDeRed, ErrorDeProveedor, RespuestaInvalida) as e:
            # RespuestaInvalida la lanza tambien el proveedor mismo (OpenAI con
            # un JSON truncado por el tope de tokens): esa llamada se cobro.
            it.estado, it.respuesta, it.alertas = "error", str(e), [_ALERTA[type(e)]]
            registrar(raiz, it)
            if not isinstance(e, ErrorDeRed) or intento == len(esperas) - 1:
                raise
    it.modelo, it.respuesta = resp.modelo, resp.texto
    it.tokens_entrada, it.tokens_salida, it.duracion_ms = resp.tokens_entrada, resp.tokens_salida, resp.duracion_ms
    segundos = f" en {resp.duracion_ms / 1000:.0f} s" if resp.duracion_ms else ""
    avisar((f"Mejora del {_DOC_CORTO[documento]} recibida" if ronda > 1
            else f"{_DOC_CORTO[documento]} recibido") + f" de {resp.modelo}{segundos}")
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


def generar(as_is: str, proveedor, raiz: Path, sid: str, mejorar: bool = True,
            avisar=None, usuario: str = "anonimo") -> Generados:
    """AS-IS -> Generados. Nunca propaga: cualquier fallo es `estado: error`
    con el tipo de la excepcion en el motivo (y en el log con traza).
    `avisar(mensaje)` recibe cada paso en cuanto ocurre; los pasos tambien
    vuelven en `Generados.pasos`."""
    pasos = []

    def _avisar(mensaje: str) -> None:
        pasos.append(mensaje)
        if avisar is not None:
            avisar(mensaje)

    try:
        g = _generar(as_is, proveedor, raiz, sid, mejorar, _avisar, usuario)
    except Exception as exc:  # ErrorDeRed, RespuestaInvalida, o un defecto nuestro
        log.error("fase3 sid=%s fallo: %s", sid, type(exc).__name__, exc_info=exc)
        _avisar(f"Falló la generación ({type(exc).__name__})")
        return Generados(estado="error", nombre=_nombre(as_is), pasos=pasos,
                         motivo=f"No se pudieron generar las propuestas. ({type(exc).__name__})")
    g.pasos = pasos
    return g


def _resumen_flujo(m) -> str:
    if m is None:
        return "sin pantallas legibles"
    compuertas = len({c.de for c in m.flujo.conexiones if c.cuando is not None})
    return f"{len(m.pantallas)} pantallas, {compuertas} compuerta{'s' if compuertas != 1 else ''}"


def _generar(as_is: str, proveedor, raiz: Path, sid: str, mejorar: bool, avisar=_sin_aviso,
             usuario: str = "anonimo") -> Generados:
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is
    n_req = len(requisitos_del_as_is(as_is))
    avisar(f"Leyendo el AS-IS: {n_req} requisitos encontrados" if n_req
           else "Leyendo el AS-IS: no trae lista de requisitos")
    dicc = _pedir(proveedor, raiz, sid, "diccionario", 1, pr.INSTRUCCION_DICC,
                  pr.VERSION_PROMPT_DICC, pr.contexto_dicc(as_is), avisar, usuario)
    tobe = _pedir(proveedor, raiz, sid, "tobe", 1, pr.INSTRUCCION_TOBE,
                  pr.VERSION_PROMPT_TOBE, pr.contexto_tobe(as_is, dicc), avisar, usuario)
    m_1, huecos = extraer_borradores(as_is, dicc, tobe)
    n_pend = len(bloquean(huecos))
    avisar(f"Verificando contra el AS-IS: {_resumen_flujo(m_1)}, "
           f"{n_pend} pendiente{'s' if n_pend != 1 else ''}")
    elegido = {"diccionario": (dicc, 1, pr.VERSION_PROMPT_DICC), "tobe": (tobe, 1, pr.VERSION_PROMPT_TOBE)}
    m_final = m_1
    if mejorar:
        elegido, huecos, m_final = _ronda_de_mejora(as_is, proveedor, raiz, sid, elegido, huecos, m_1, avisar, usuario)
    reparto = _por_documento(huecos)
    docs = {}
    for clave, (texto, ronda, version) in elegido.items():
        docs[clave] = Documento(texto=texto, version_prompt=version, ronda=ronda,
                                huecos=[HuecoOut.desde(h) for h in reparto[clave]])
    docs["diccionario"].vista = vista_de(m_final)
    n_pend = len(bloquean(huecos))
    avisar(f"Propuesta lista: {_resumen_flujo(m_final)}, "
           f"{n_pend} pendiente{'s' if n_pend != 1 else ''} por resolver")
    return Generados(estado="listo", nombre=_nombre(as_is),
                     diccionario=docs["diccionario"], tobe=docs["tobe"])


def _cuenta(manifiesto, huecos: list, clave: str) -> tuple:
    """Que tan mal esta un documento, comparable con `<=`: primero si la
    pareja ni siquiera dio manifiesto (un Diccionario sin pantallas produce
    UN solo DIC-00 y corta la extraccion, asi que contar huecos lo haria
    parecer mejor que uno con dos datos que faltan), luego los bloqueantes,
    luego los `falta_dato` — lo que la persona tendria que resolver a mano."""
    mios = [h for h in bloquean(huecos) if atribuir(h) == clave]
    return (manifiesto is None,
            sum(1 for h in mios if h.nivel == "bloqueante"),
            sum(1 for h in mios if h.nivel == "falta_dato"))


def _tamano(manifiesto, texto: str, clave: str) -> int:
    """Cuanto documento hay: pantallas del Diccionario o tareas del diagrama
    compilable del TO-BE. Se mide sobre el texto (no sobre el manifiesto) para
    que un TO-BE sin bloque mermaid cuente 0 aunque el Diccionario de la pareja
    este entero."""
    if clave == "diccionario":
        return 0 if manifiesto is None else len(manifiesto.pantallas)
    bloques = re.findall(r"```mermaid(.*?)```", texto or "", re.S)
    if not bloques:
        return 0
    return len(re.findall(r"^\s*[A-Za-z_][\w]*\s*[\[(]", bloques[0], re.M))


def _ronda_de_mejora(as_is: str, proveedor, raiz: Path, sid: str, elegido: dict, huecos: list,
                     m_1=None, avisar=_sin_aviso, usuario: str = "anonimo"):
    """Una sola vez por documento, y solo si ese documento tiene huecos que
    bloquean. Primero el Diccionario; el TO-BE se mejora contra el Diccionario
    ya elegido. Por documento se conserva la ronda con menos bloqueantes
    (empate: la 2, que vio los pendientes). Si la mejora falla, se conserva la
    ronda 1: sus tokens ya estan gastados y su resultado es util."""
    reparto = {clave: [str(h) for h in bloquean(huecos) if atribuir(h) == clave]
               for clave in ("diccionario", "tobe")}
    # El ciclo de correccion exige una pantalla nueva del ciudadano, y eso
    # vive en el Diccionario: si solo lo viera la mejora del TO-BE (que no
    # puede inventar pantallas) nunca se cerraria — paso el 2026-09-25.
    reparto["diccionario"] += [str(h) for h in bloquean(huecos) if h.codigo == "GEN-02"]
    if not reparto["diccionario"] and not reparto["tobe"]:
        return elegido, huecos, m_1
    candidatos = {"diccionario": elegido["diccionario"][0], "tobe": elegido["tobe"][0]}

    def _codigos(lineas: list) -> str:
        return ", ".join(sorted({re.match(r"\[([^\]]+)\]", l).group(1) for l in lineas if re.match(r"\[([^\]]+)\]", l)}))

    try:
        if reparto["diccionario"]:
            avisar(f"El verificador pide una mejora del Diccionario por: {_codigos(reparto['diccionario'])}")
            candidatos["diccionario"] = _pedir(
                proveedor, raiz, sid, "diccionario", 2, pr.INSTRUCCION_MEJORA, pr.VERSION_PROMPT_MEJORA,
                pr.contexto_mejora(as_is, candidatos["diccionario"], reparto["diccionario"], "diccionario"), avisar, usuario)
        if reparto["tobe"]:
            avisar(f"El verificador pide una mejora del TO-BE por: {_codigos(reparto['tobe'])}")
            candidatos["tobe"] = _pedir(
                proveedor, raiz, sid, "tobe", 2, pr.INSTRUCCION_MEJORA, pr.VERSION_PROMPT_MEJORA,
                pr.contexto_mejora(as_is, candidatos["tobe"], reparto["tobe"], "tobe",
                                   diccionario=candidatos["diccionario"]), avisar, usuario)
    except (ErrorDeRed, ErrorDeProveedor, RespuestaInvalida) as exc:
        log.warning("fase3 sid=%s la mejora fallo (%s); se conserva la ronda 1", sid, type(exc).__name__)
        avisar("La mejora falló; se conserva la primera versión")
        return elegido, huecos, m_1
    m_2, huecos_2 = extraer_borradores(as_is, candidatos["diccionario"], candidatos["tobe"])
    final = dict(elegido)
    for clave in ("diccionario", "tobe"):
        if not reparto[clave]:
            continue
        # Corregir no es recortar: una ronda 2 truncada (Reposicion, 2026-09-25:
        # el JSON se cerro a media linea del diagrama) tenia menos huecos que la
        # 1 solo porque ya no habia nada que revisar. Si pierde pantallas o
        # tareas, se queda la 1.
        if _tamano(m_2, candidatos[clave], clave) < _tamano(m_1, elegido[clave][0], clave):
            log.warning("fase3 sid=%s la mejora del %s recorta el documento; se conserva la ronda 1",
                        sid, clave)
            avisar(f"La mejora recortaba el {_DOC_CORTO[clave]}; se conserva la ronda 1")
            continue
        if _cuenta(m_2, huecos_2, clave) <= _cuenta(m_1, huecos, clave):
            final[clave] = (candidatos[clave], 2, pr.VERSION_PROMPT_MEJORA)
            avisar(f"Se conserva la ronda 2 del {_DOC_CORTO[clave]}")
        else:
            avisar(f"La mejora no ayudó; se conserva la ronda 1 del {_DOC_CORTO[clave]}")
    # Si la pareja final es exactamente la de la ronda 2, sus huecos ya estan
    # medidos. Si se mezclan rondas (Diccionario 2, TO-BE 1), se vuelven a
    # medir sobre la pareja elegida: es una extraccion local, sin llamadas.
    if all(final[c][0] == candidatos[c] for c in ("diccionario", "tobe")):
        return final, huecos_2, m_2
    m_f, huecos_f = extraer_borradores(as_is, final["diccionario"][0], final["tobe"][0])
    return final, huecos_f, m_f
