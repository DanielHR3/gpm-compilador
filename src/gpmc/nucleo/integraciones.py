"""Endpoints de catalogo conocidos del gobierno de Hidalgo.

Datos puros: este modulo SABE urls, nunca las llama. La red vive en el
navegador, que es donde la plataforma tambien la hace. Asi el nucleo conserva
su invariante de no tener dependencias de red.

Cada entrada esta verificada dos veces: su forma sale del export autentico
'acceso-informacion-publica.gpm', y su respuesta se comprobo contra la API viva
el 2026-08-28.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Catalogo:
    clave: str            # como lo nombra el Diccionario: "mgem"
    proveedor: str        # informativo: "INEGI"
    url: str              # con {padre} si es en cascada
    nodo: str             # donde vive el arreglo en la respuesta
    etiqueta: str         # la clave que se MUESTRA
    valor: str            # la clave que se GUARDA
    requiere_padre: bool = False
    # Para un autollenado (`api_ajax`): que claves de la respuesta se escriben
    # en campos del formulario. Vacio para un catalogo normal, que solo pinta
    # una lista. SIPUBEH devuelve nombre y apellidos por separado, y quedarse
    # solo con `nombres` deja el tramite a medias.
    campos_respuesta: tuple = ()
    # Dos cosas distintas que el catalogo de la Direccion (2026-08-11) mezcla:
    # "catalogo" devuelve una LISTA para poblar un select; "consulta" recibe
    # un dato y devuelve otros para autollenar (un `api_ajax`). Solo la
    # segunda usa `campos_respuesta`.
    tipo: str = "catalogo"

    def url_para(self, padre: Optional[str]) -> str:
        """La URL lista para el .gpm. La plataforma interpola @@campo en tiempo
        de ejecucion, asi que aqui solo se sustituye el nombre del campo."""
        if not self.requiere_padre:
            return self.url
        return self.url.replace("{padre}", padre or "")


# La distincion etiqueta/valor es la que hace funcionar la cascada: estado_sol
# muestra "Hidalgo" pero guarda "13", y mgem/13 devuelve sus 84 municipios.
CATALOGOS = {
    c.clave: c
    for c in (
        Catalogo(
            clave="mgee", proveedor="INEGI",
            url="https://gaia.inegi.org.mx/wscatgeo/v2/mgee",
            nodo="datos", etiqueta="nomgeo", valor="cvegeo",
        ),
        Catalogo(
            clave="mgem", proveedor="INEGI",
            url="https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@{padre}",
            nodo="datos", etiqueta="nomgeo", valor="cvegeo",
            requiere_padre=True,
        ),
        Catalogo(
            clave="zip_codes", proveedor="SEPOMEX",
            url="https://sepomex.kurenn.dev/api/v1/zip_codes?zip_code=@@{padre}",
            nodo="zip_codes", etiqueta="d_asenta", valor="d_asenta",
            requiere_padre=True,
        ),
        # La CURP viaja como PARAMETRO, no dentro de la ruta, y el camino es
        # `/efirma/api/`. Lo dicen dos fuentes independientes: el `extra` del
        # `api_curp_trigger` de `acceso-informacion-publica.gpm`, y el «Catalogo
        # Maestro de APIs» de la Direccion (2026-08-11), que ademas documenta la
        # respuesta completa. La version anterior —`/api/consultacurpn/@@{padre}`—
        # no coincidia con ninguna de las dos.
        Catalogo(
            clave="consultacurpn", proveedor="SIPUBEH",
            url="https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn?curp=@@{padre}",
            nodo="data", etiqueta="nombres", valor="nombres",
            requiere_padre=True,
            campos_respuesta=("nombres", "apePat", "apeMat"),
            tipo="consulta",
        ),
    )
}

# Sinonimos: lo que un Diccionario escribe de verdad, no la clave tecnica.
# Se resuelven sin acentos ni mayusculas. Un proveedor con dos endpoints
# (INEGI) cae al que no requiere padre; "municipio" y "mgem" van al que si.
SINONIMOS = {
    "inegi": "mgee", "estado": "mgee", "entidad": "mgee",
    "municipio": "mgem",
    "sepomex": "zip_codes", "codigo postal": "zip_codes", "cp": "zip_codes",
    "colonia": "zip_codes",
    "sipubeh": "consultacurpn", "curp": "consultacurpn",
}


def _normalizar(texto: str) -> str:
    import unicodedata
    sin_acentos = "".join(
        ch for ch in unicodedata.normalize("NFD", texto) if unicodedata.category(ch) != "Mn"
    )
    return " ".join(sin_acentos.lower().split())


def clave_de(texto: Optional[str]) -> Optional[str]:
    """Clave tecnica a partir de una clave o de una frase del Diccionario.

    Acepta «mgem», «`mgem` (INEGI)», «Código Postal» o «CURP». Devuelve None
    para lo que no conoce: el compilador lo reporta como API-01 en vez de
    inventar una URL.
    """
    if not texto:
        return None
    limpio = _normalizar(texto.replace("`", ""))
    # Primero la clave tecnica sola o seguida de su proveedor entre parentesis.
    primera = limpio.split("(")[0].strip()
    if primera in CATALOGOS:
        return primera
    if primera in SINONIMOS:
        return SINONIMOS[primera]
    return None


# Propuestas: servicios del «Catalogo Maestro de APIs» de la Direccion
# (2026-08-11) que piden llave, pago o convenio. NO se emiten en cliente
# (SEG-04: la llave quedaria a la vista) y NO aparecen en la seccion de
# catalogos. Se registran para que un Diccionario que los nombre produzca
# API-05 con su nombre, en vez de silencio. Quedan como propuesta pendiente
# de convenio; el dia que uno tenga via publica, pasa a CATALOGOS con prueba.
PROPUESTAS = {
    "sat": "SAT (validacion de RFC y CFDI)",
    "rfc": "SAT (validacion de RFC)",
    "tlaloc": "Tlaloc (CURP con estatus de defuncion, RFC) — de pago",
    "tlaloc_curp": "Tlaloc (CURP con estatus de defuncion) — de pago",
    "renapo_directo": "RENAPO directo — requiere convenio",
    "repuve": "REPUVE via ApiMarket — de pago",
    "ine": "INE (verificacion de credencial) — requiere convenio",
    "codigos.zip": "codigos.zip (codigos postales) — requiere API Key",
}
APIS_CON_TOKEN = frozenset(PROPUESTAS)


def nombre_propuesta(texto: Optional[str]) -> Optional[str]:
    """El nombre legible de un servicio de pago o convenio, o None."""
    if not texto:
        return None
    return PROPUESTAS.get(_normalizar(texto.replace("`", "")).split("(")[0].strip())


def resolver(clave: Optional[str]) -> Optional[Catalogo]:
    """Un endpoint no registrado devuelve None: el compilador lo reporta como
    hueco API-01 en vez de inventar una URL."""
    resuelta = clave_de(clave)
    return CATALOGOS.get(resuelta) if resuelta else None


def requiere_token(clave: Optional[str]) -> bool:
    """El endpoint es uno conocido que necesita credencial. El compilador no lo
    emite en cliente (SEG-04); se reporta como hueco API-05 → Acción PHP a mano."""
    return nombre_propuesta(clave) is not None
