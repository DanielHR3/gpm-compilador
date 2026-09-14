"""Convierte un Diccionario de Datos en Word al Markdown que lee el extractor.

El equipo que construye GPM entrega el Diccionario como `.docx`; el compilador
solo sabe leer `.md`. Hasta ahora alguien tenia que convertirlo a mano, tramite
por tramite, antes de que el compilador pudiera siquiera empezar.

La forma del documento es mecanica:

    una sola tabla
      fila de 1 celda    -> el nombre de una seccion  («Módulo de licencias»)
      fila de N celdas   -> la cabecera de columnas
      filas de N celdas  -> los campos

Esa fila de una sola celda es justo la cabecera de pantalla que al extractor le
falta y que provocaba DIC-04. Se traduce a `### Pantalla N — ACTOR — Nombre`.

No se usa ninguna dependencia nueva: un `.docx` es un zip con XML, y la
biblioteca estandar basta.
"""
import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# El Word no dice quien usa cada pantalla. Estas son de captura y se dirigen al
# ciudadano —«El ciudadano debe de elegir uno de los 11»—, que es ademas lo que
# el extractor ya asume cuando agrupa campos sin cabecera.
_ACTOR_POR_DEFECTO = "CIUDADANO"

# Hasta donde puede llegar un titulo de seccion. Por encima es prosa: el Word
# intercala filas fusionadas con aclaraciones que no titulan nada.
_LARGO_MAXIMO_TITULO = 70

_INICIO_DE_NOTA = re.compile(r"^\s*(nota|aclaraci[oó]n|importante|observaci)", re.I)


def _es_titulo_de_seccion(texto: str) -> bool:
    """Una fila fusionada titula una pantalla, o es una anotacion.

    Tratar cada anotacion como titulo partia la pantalla en dos y dejaba a la
    anterior sin sus campos: en «Permiso para conducir de menores de edad»,
    «Información personal del ciudadano» salia con cero campos porque la nota
    que venia debajo se los quedaba.
    """
    if not texto or _INICIO_DE_NOTA.match(texto):
        return False
    return len(texto) <= _LARGO_MAXIMO_TITULO


def _texto(elemento) -> str:
    """Todo el texto de un nodo, con los saltos de Word vueltos espacios."""
    partes = []
    for t in elemento.iter():
        if t.tag == f"{_W}t":
            partes.append(t.text or "")
        elif t.tag in (f"{_W}br", f"{_W}cr"):
            partes.append(" ")
    return re.sub(r"\s+", " ", "".join(partes)).strip()


def _celda(texto: str) -> str:
    """Escapa lo que romperia una tabla Markdown."""
    return texto.replace("|", "\\|")


def a_markdown(contenido: bytes) -> str:
    """El `.docx` como Markdown. `ValueError` si no es un documento de Word."""
    try:
        z = zipfile.ZipFile(BytesIO(contenido))
        xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError("el archivo no parece un .docx de Word") from e

    cuerpo = ET.fromstring(xml).find(f"{_W}body")
    if cuerpo is None:
        raise ValueError("el archivo no parece un .docx de Word: no trae cuerpo")

    lineas: list[str] = []
    pantalla = 0
    cabecera_puesta = False
    # La ultima cabecera vista, para poder reabrir la tabla tras una anotacion.
    cabecera: list[str] = []

    for tabla in cuerpo.iter(f"{_W}tbl"):
        for tr in tabla.findall(f"{_W}tr"):
            celdas = [_texto(tc) for tc in tr.findall(f"{_W}tc")]
            if not any(celdas):
                continue

            # Fila fusionada: titula una seccion, o es una anotacion.
            if len(celdas) == 1 and not _es_titulo_de_seccion(celdas[0]):
                # La anotacion no se pierde: queda como texto de la pantalla en
                # curso, fuera de la tabla para no descuadrar sus columnas.
                lineas += ["", celdas[0], ""]
                # La anotacion parte la tabla. Sin repetir la cabecera, la
                # siguiente fila de datos pasaria a ser la cabecera de la tabla
                # nueva y ese campo se perderia.
                if cabecera:
                    lineas += [
                        "| " + " | ".join(cabecera) + " |",
                        "| " + " | ".join("---" for _ in cabecera) + " |",
                    ]
                    cabecera_puesta = True
                else:
                    cabecera_puesta = False
                continue

            if len(celdas) == 1:
                pantalla += 1
                lineas += [
                    "",
                    f"### Pantalla {pantalla} — {_ACTOR_POR_DEFECTO} — {celdas[0]}",
                    "",
                ]
                cabecera_puesta = False
                cabecera = []
                continue

            fila = "| " + " | ".join(_celda(c) for c in celdas) + " |"
            lineas.append(fila)
            if not cabecera_puesta:
                # Markdown exige la separadora justo bajo la cabecera.
                lineas.append("| " + " | ".join("---" for _ in celdas) + " |")
                cabecera_puesta = True
                cabecera = [_celda(c) for c in celdas]

    return "\n".join(lineas).strip() + "\n"
