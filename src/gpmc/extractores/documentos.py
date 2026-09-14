"""Documentos que el tramite genera: oficios, acuses, constancias.

El compilador ya sabia emitir un Documento PDF de GPM (`compilador/acciones.py`)
pero nada del expediente lo alimentaba: el extractor nunca creaba una accion.
Casi todo tramite devuelve un documento al ciudadano, asi que la plantilla
entra al expediente como un `.md` en la carpeta `documentos/`:

    ---
    titulo: Constancia de registro
    firmador_nombre: Mtro. M. Pedro Velázquez Bárcena
    firmador_cargo: Director General
    ---
    Se hace constar que {{nombre}} quedó registrado con la CURP {{curp}}.

La plantilla puede venir tambien en Word (`.docx`) o en PDF con texto: se
lee su texto corrido y se trata igual. Un PDF escaneado no se lee: el
compilador lee, nunca adivina.

Cada `{{variable}}` tiene que ser un campo del Diccionario: es de ahi de donde
GPM saca el valor al generar el PDF. Una variable que no existe no se emite —
reventaria al compilar— y se reporta con el nombre exacto para corregirla.
"""
import re
from pathlib import Path

from gpmc.extractores import docx as ext_docx
from gpmc.extractores import pdf as ext_pdf
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Accion, Pantalla, Tarea

CARPETA = "documentos"

# Como se saca el texto de cada formato de plantilla. Cualquier otro archivo
# —una foto del oficio— no es una plantilla y se reporta.
_LECTORES = {
    ".md": lambda datos: datos.decode("utf-8"),
    ".docx": ext_docx.a_texto,
    ".pdf": ext_pdf.a_texto,
}
FORMATOS = tuple(_LECTORES)

# Misma sintaxis que `compilador/acciones.php_documento`.
_VARIABLE = re.compile(r"\{\{(\w+)\}\}")
_CABECERA = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
_CLAVES_CABECERA = ("titulo", "subtitulo", "firmador_nombre", "firmador_cargo")


def _partir_cabecera(texto: str) -> "tuple[dict, str]":
    """La cabecera `--- clave: valor ---` y el cuerpo. Sin cabecera, {} y todo."""
    m = _CABECERA.match(texto)
    if not m:
        return {}, texto
    datos = {}
    for linea in m.group(1).splitlines():
        if ":" not in linea:
            continue
        clave, valor = linea.split(":", 1)
        clave = clave.strip().lower()
        if clave in _CLAVES_CABECERA:
            datos[clave] = valor.strip()
    return datos, texto[m.end():]


def _slug(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_") or "documento"


def extraer_documentos(carpeta: Path, campos_declarados: "set[str]") -> "tuple[list[Accion], list[Hueco]]":
    """Las plantillas de `documentos/` como acciones `documento`, mas sus huecos."""
    d = Path(carpeta) / CARPETA
    if not d.is_dir():
        return [], []

    acciones, huecos = [], []
    for archivo in sorted(p for p in d.iterdir() if p.is_file()):
        leer = _LECTORES.get(archivo.suffix.lower())
        if leer is None:
            # Una foto del oficio no se puede leer como plantilla. Si se ignora
            # en silencio, el analista cree que su documento entro.
            huecos.append(Hueco(
                "falta_dato", "DOC-03", f"documentos/{archivo.name}",
                f"el documento «{archivo.name}» no se puede usar como plantilla: "
                f"solo se leen {', '.join(FORMATOS)} con {{{{variables}}}}. Si es un "
                f"oficio escaneado, adjúntalo como documento de apoyo y escribe la plantilla",
            ))
            continue
        try:
            texto = leer(archivo.read_bytes())
        except (ValueError, UnicodeDecodeError) as e:
            huecos.append(Hueco(
                "falta_dato", "DOC-03", f"documentos/{archivo.name}",
                f"no se pudo leer la plantilla «{archivo.name}»: {e}",
            ))
            continue

        cabecera, cuerpo = _partir_cabecera(texto)
        cuerpo = cuerpo.strip()
        usadas = sorted(set(_VARIABLE.findall(cuerpo)))
        desconocidas = [v for v in usadas if v not in campos_declarados]
        if desconocidas:
            huecos.append(Hueco(
                "falta_dato", "DOC-02", f"documentos/{archivo.name}",
                f"la plantilla «{archivo.stem}» usa {', '.join('{{' + v + '}}' for v in desconocidas)}, "
                f"que no {'es un campo' if len(desconocidas) == 1 else 'son campos'} del Diccionario; "
                f"GPM no tendría de dónde sacar el valor",
            ))
            continue

        acciones.append(Accion(
            tipo="documento",
            nombre=archivo.stem,
            variable=f"{_slug(archivo.stem)}_contenido",
            plantilla=cuerpo,
            variables=usadas,
            **cabecera,
        ))
    return acciones, huecos


def atar_a_tareas(acciones: "list[Accion]", tareas: "list[Tarea]", pantallas: "list[Pantalla]") -> "list[Hueco]":
    """Cuelga cada documento de la tarea que lo puede generar, y lo reporta.

    Un Documento con su Accion pero sin Evento en ninguna tarea es un PDF que
    nunca se produce: eso salio en el primer .gpm con documento. La tarea no
    se adivina, se lee de los datos: la primera del flujo en la que ya se
    capturaron todas las variables de la plantilla. Se ata «despues» de esa
    tarea, y queda un DOC-04 por confirmar porque el analista puede preferir
    otra (una de firma, por ejemplo).
    """
    campos_de = {p.id: {c.nombre for c in p.campos} for p in pantallas}
    huecos = []
    for accion in acciones:
        if accion.tipo != "documento":
            continue
        necesarias = set(getattr(accion, "variables", []) or [])
        capturados: set = set()
        destino = None
        for tarea in tareas:
            for paso in tarea.pantallas:
                capturados |= campos_de.get(paso.id, set())
            if necesarias <= capturados:
                destino = tarea
                break
        if destino is None:
            huecos.append(Hueco(
                "falta_dato", "DOC-04", f"documentos/{accion.nombre}",
                f"el documento «{accion.nombre}» no se genera en ninguna tarea: "
                f"ninguna del flujo llega a tener todos sus datos "
                f"({', '.join(sorted(necesarias))}). Revisa que esas pantallas "
                f"estén en el flujo",
            ))
            continue
        destino.acciones_despues.append(accion.nombre)
        huecos.append(Hueco(
            "por_confirmar", "DOC-04", f"documentos/{accion.nombre}",
            f"el documento «{accion.nombre}» se genera al terminar la tarea "
            f"«{destino.nombre}», la primera en la que ya están todos sus datos. "
            f"Si debe salir en otra tarea (por ejemplo tras una firma), cámbialo a mano",
        ))
    return huecos
