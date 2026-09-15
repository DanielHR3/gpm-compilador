"""Reparte los archivos de una carpeta de expediente en las zonas del asistente.

Trabaja SOLO con nombres: no abre ningun archivo. Asi el navegador manda la
lista de rutas relativas de la carpeta y recibe el reparto sin subir los bytes
dos veces (una para clasificar y otra para extraer).

El criterio sale de los 24 expedientes del wiki de reingenieria, no de una
convencion inventada:

- El AS-IS, el TO-BE y el Diccionario llegan en `.md`, y el AS-IS y el TO-BE
  traen ademas un gemelo en PDF que esta escaneado. Por eso, ante dos
  candidatos para la misma zona, gana la extension que el extractor lee mejor
  (`.md` > `.docx` > `.pdf`) y el perdedor cae a apoyo.
- Todos los expedientes traen una carpeta `Documentos/` con los oficios que el
  tramite produce. **Los 21 PDF que hay en esas carpetas estan escaneados**, o
  sea que ninguno sirve de plantilla: solo un `.md` o un `.docx` de ahi se
  toma como documento de salida; el resto es apoyo.
- Ante un empate real no se adivina: la zona queda vacia y se dice por que,
  mismo criterio que el hueco `INS-02` del extractor.
"""

from dataclasses import dataclass, field
from typing import Optional
import posixpath
import re

from gpmc.extractores.expediente import _normalizar

# Lo que el extractor lee, de mejor a peor. El orden decide los empates.
_PREFERENCIA = {".md": 0, ".markdown": 0, ".docx": 1, ".pdf": 2}

# Archivos de trabajo del propio compilador o del sistema: no son insumo ni
# apoyo. Se listan igual, para que nadie crea que se perdieron.
_IGNORAR_EXT = {".gpm", ".py", ".pyc", ".json", ".yaml", ".yml", ".lock",
                ".ini", ".cfg", ".toml", ".db", ".sqlite"}
_IGNORAR_NOMBRE = {".ds_store", "thumbs.db", "desktop.ini", "__pycache__"}

# Claves de cada insumo, en el mismo orden que usa `extraer_expediente`.
_INSUMOS = (
    ("as_is", ("analisis as is", "as is")),
    ("to_be", ("propuesta to be", "to be")),
    ("diccionario", ("diccionario de datos", "diccionario")),
)

_ETIQUETA = {"as_is": "As Is", "to_be": "To Be", "diccionario": "Diccionario"}


@dataclass
class Asignacion:
    """A que zona del asistente va cada archivo de la carpeta."""
    as_is: Optional[str] = None
    to_be: Optional[str] = None
    diccionario: Optional[str] = None
    vistas: Optional[str] = None
    adjuntos: list = field(default_factory=list)      # documentos de apoyo
    documentos: list = field(default_factory=list)    # plantillas de salida
    ignorados: list = field(default_factory=list)
    avisos: list = field(default_factory=list)        # por que una zona quedo vacia


def _partes(ruta):
    """(carpeta_raiz, nombre, extension_en_minusculas) de una ruta relativa."""
    ruta = ruta.replace("\\", "/")
    carpeta, _, nombre = ruta.rpartition("/")
    raiz = carpeta.split("/")[0] if carpeta else ""
    _, ext = posixpath.splitext(nombre)
    return raiz, nombre, ext.lower()


def _clave(nombre):
    """Nombre de archivo -> forma comparable, sin extension ni prefijo de orden.

    `_normalizar` solo recorta `.md`; aqui llegan tambien `.pdf` y `.docx`, y
    nombres con doble punto ("Expediente..md") que salen de los expedientes
    reales.
    """
    base = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", nombre).rstrip(".")
    return _normalizar(base)


def _es_carpeta_de_documentos(raiz):
    """`Documentos/`, `01 Documentos/`, `1.- Documentos/` — todas valen."""
    if not raiz:
        return False
    # `_normalizar` solo recorta el prefijo de orden si trae puntuacion
    # ("1.- Documentos"); "01 Documentos" conserva el numero.
    return re.sub(r"^\d+\s*", "", _normalizar(raiz)) == "documentos"


def clasificar(nombres):
    """Reparte `nombres` (rutas relativas a la carpeta) y devuelve una `Asignacion`.

    Funcion pura: no toca el disco ni la red.
    """
    a = Asignacion()
    candidatos = {zona: [] for zona, _ in _INSUMOS}
    sobrantes = []

    for ruta in nombres:
        raiz, nombre, ext = _partes(ruta)

        if nombre.lower() in _IGNORAR_NOMBRE or nombre.startswith(".") \
                or ext in _IGNORAR_EXT:
            a.ignorados.append(ruta)
            continue

        if _es_carpeta_de_documentos(raiz):
            # Plantilla del tramite solo si el extractor puede leerla. Un PDF
            # de esta carpeta esta escaneado en los seis expedientes reales.
            (a.documentos if ext in (".md", ".markdown", ".docx")
             else a.adjuntos).append(ruta)
            continue

        if raiz:                      # cualquier otra subcarpeta: apoyo
            sobrantes.append(ruta)
            continue

        if ext in (".html", ".htm") and "vista" in _clave(nombre):
            if a.vistas is None:
                a.vistas = ruta
            else:
                sobrantes.append(ruta)
            continue

        clave = _clave(nombre)
        for zona, llaves in _INSUMOS:
            if any(k in clave for k in llaves):
                candidatos[zona].append(ruta)
                break
        else:
            sobrantes.append(ruta)

    # Un archivo puede casar con varias zonas ("As Is" tambien casa dentro de
    # "Analisis AS-IS"): el bucle de arriba se queda con la primera, que es la
    # mas especifica por el orden de `_INSUMOS`.
    for zona, _ in _INSUMOS:
        elegido, resto, aviso = _elegir(zona, candidatos[zona])
        setattr(a, zona, elegido)
        sobrantes.extend(resto)
        if aviso:
            a.avisos.append(aviso)

    a.adjuntos.extend(sobrantes)
    a.adjuntos.sort()
    a.documentos.sort()
    a.ignorados.sort()
    return a


def _elegir(zona, rutas):
    """(elegido, no_elegidos, aviso). Gana la extension que mejor se lee; si
    empatan dos con la misma, no se adivina."""
    etiqueta = _ETIQUETA[zona]
    if not rutas:
        return None, [], f"No encontré el {etiqueta} en la carpeta."

    rango = {r: _PREFERENCIA.get(_partes(r)[2], 9) for r in rutas}
    mejor = min(rango.values())
    empatados = [r for r in rutas if rango[r] == mejor]

    if len(empatados) > 1:
        cuales = ", ".join(sorted(empatados))
        return None, list(rutas), (
            f"Hay {len(empatados)} candidatos para el {etiqueta} y no puedo "
            f"elegir por ti: {cuales}. Ponlo tú en su zona."
        )

    elegido = empatados[0]
    return elegido, [r for r in rutas if r != elegido], None
