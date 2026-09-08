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
        Catalogo(
            clave="consultacurpn", proveedor="SIPUBEH",
            url="https://sipubeh.hidalgo.gob.mx/api/consultacurpn/@@{padre}",
            nodo="data", etiqueta="nombres", valor="nombres",
            requiere_padre=True,
        ),
    )
}

# Sinonimos: los Diccionarios del equipo de Simplificacion escriben el nombre
# del proveedor ("INEGI", "SEPOMEX") en vez de la clave tecnica del endpoint.
# Sin este mapeo, el compilador no los reconoce y emite huecos API-01 falsos.
# Cada sinonimo apunta a la clave por omision del proveedor: si un proveedor
# tiene mas de un endpoint, el Diccionario debe usar la clave tecnica exacta
# ("mgee" o "mgem"), no el nombre del proveedor, o aclarar cual.
SINONIMOS = {
    "inegi": "mgee",          # estados; "mgem" requiere padre, se resuelve aparte
    "sepomex": "zip_codes",
    "sipubeh": "consultacurpn",
}


def resolver(clave: Optional[str]) -> Optional[Catalogo]:
    """Un endpoint no registrado devuelve None: el compilador lo reporta como
    hueco API-01 en vez de inventar una URL."""
    normalizada = (clave or "").strip().lower()
    return CATALOGOS.get(normalizada) or CATALOGOS.get(SINONIMOS.get(normalizada, ""))
