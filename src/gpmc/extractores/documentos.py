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

Cada `{{variable}}` tiene que ser un campo del Diccionario: es de ahi de donde
GPM saca el valor al generar el PDF. Una variable que no existe no se emite —
reventaria al compilar— y se reporta con el nombre exacto para corregirla.
"""
import re
from pathlib import Path

from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Accion

CARPETA = "documentos"

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
        if archivo.suffix.lower() != ".md":
            # Un oficio escaneado en .docx no se puede leer como plantilla. Si
            # se ignora en silencio, el analista cree que su documento entro.
            huecos.append(Hueco(
                "falta_dato", "DOC-03", f"documentos/{archivo.name}",
                f"el documento «{archivo.name}» no se puede usar como plantilla: "
                f"solo se leen archivos .md con {{{{variables}}}}. Si es un oficio "
                f"escaneado, adjúntalo como documento de apoyo y escribe la plantilla",
            ))
            continue

        cabecera, cuerpo = _partir_cabecera(archivo.read_text(encoding="utf-8"))
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
