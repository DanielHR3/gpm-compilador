"""El equipo que construye GPM entrega el Diccionario en Word, no en Markdown.

Hasta ahora alguien tenia que convertirlo a mano, tramite por tramite, antes de
que el compilador pudiera siquiera empezar.
"""
import io
import zipfile

import pytest

from gpmc.extractores.docx import a_markdown

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(cuerpo: str) -> bytes:
    """Un .docx minimo: solo la parte que el conversor lee."""
    doc = (
        f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{cuerpo}'
        f"</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def _fila(*celdas: str) -> str:
    tcs = "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in celdas)
    return f"<w:tr>{tcs}</w:tr>"


def _tabla(*filas: str) -> str:
    return f"<w:tbl>{''.join(filas)}</w:tbl>"


def test_una_fila_de_una_sola_celda_es_el_nombre_de_una_pantalla():
    """El Word usa una fila fusionada como titulo de seccion. Es justo la
    cabecera que al compilador le falta y que provocaba DIC-04."""
    md = a_markdown(_docx(_tabla(
        _fila("Módulo de licencias"),
        _fila("Nombre del campo", "Tipo de dato", "Descripción"),
        _fila("Municipio", "Select", "Elige el municipio"),
    )))

    assert "### Pantalla 1 — CIUDADANO — Módulo de licencias" in md


def test_las_filas_de_datos_salen_como_tabla_markdown():
    md = a_markdown(_docx(_tabla(
        _fila("Módulo de licencias"),
        _fila("Nombre del campo", "Tipo de dato", "Descripción"),
        _fila("Municipio", "Select", "Elige el municipio"),
    )))

    assert "| Nombre del campo | Tipo de dato | Descripción |" in md
    assert "| Municipio | Select | Elige el municipio |" in md
    # La fila separadora que Markdown exige entre cabecera y datos.
    assert "| --- | --- | --- |" in md


def test_cada_seccion_nueva_numera_su_pantalla():
    md = a_markdown(_docx(_tabla(
        _fila("Módulo de licencias"),
        _fila("Nombre del campo", "Tipo de dato"),
        _fila("Municipio", "Select"),
        _fila("Información personal del ciudadano"),
        _fila("Nombre del campo", "Tipo de dato"),
        _fila("CURP", "Text"),
    )))

    assert "### Pantalla 1 — CIUDADANO — Módulo de licencias" in md
    assert "### Pantalla 2 — CIUDADANO — Información personal del ciudadano" in md


def test_una_barra_dentro_de_una_celda_no_rompe_la_tabla():
    """Un '|' en el texto partiria la fila en dos columnas al leerla."""
    md = a_markdown(_docx(_tabla(
        _fila("Sección"),
        _fila("Nombre del campo", "Descripción"),
        _fila("Tipo", "Permiso | Licencia"),
    )))

    assert "Permiso \\| Licencia" in md


def test_un_archivo_que_no_es_docx_se_rechaza_con_un_mensaje_claro():
    with pytest.raises(ValueError, match="no parece un .docx"):
        a_markdown(b"esto no es un zip")


# ── La subida acepta Word ────────────────────────────────────────────────────

def _cli(tmp_path):
    from fastapi.testclient import TestClient
    from gpmc.web.app import crear_app
    return TestClient(crear_app(tmp_path))


_DOCX_MINIMO = _docx(_tabla(
    _fila("Módulo de licencias"),
    _fila("Nombre del campo", "Tipo de dato", "Descripción"),
    _fila("Municipio", "Select", "Elige el municipio `@@municipio`"),
))


def test_subir_el_diccionario_en_word_no_obliga_a_convertirlo_a_mano(tmp_path):
    """El equipo que construye GPM entrega .docx. Antes habia que pasarlo a
    Markdown a mano antes de poder compilar."""
    c = _cli(tmp_path)

    r = c.post("/api/v1/expedientes", files={"diccionario": (
        "Diccionario de datos.docx", _DOCX_MINIMO,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )})

    assert r.status_code == 201, r.text
    est = r.json()
    assert len(est["manifiesto"]["pantallas"]) == 1
    assert est["manifiesto"]["pantallas"][0]["nombre"] == "Módulo de licencias"
    # Y el aviso de "no hay cabeceras de pantalla" ya no aplica.
    assert not [h for h in est["huecos"] if h["codigo"] == "DIC-04"]


def test_un_word_ilegible_se_reporta_en_vez_de_guardarse_como_basura(tmp_path):
    c = _cli(tmp_path)

    r = c.post("/api/v1/expedientes", files={"diccionario": (
        "roto.docx", b"esto no es un zip", "application/octet-stream",
    )})

    assert r.status_code == 422, r.text
    assert "no se pudo leer" in r.json()["error"].lower()


def test_una_nota_no_es_una_pantalla():
    """El Word intercala filas fusionadas con aclaraciones —«Nota: el menor debe
    ser mayor de 16»—. Tratarlas como titulo de seccion partia la pantalla en
    dos y dejaba la anterior sin sus campos."""
    md = a_markdown(_docx(_tabla(
        _fila("Información personal del ciudadano"),
        _fila("Nombre del campo", "Tipo de dato"),
        _fila("Nota: El menor debe de ser mayor de 16 y menor de 18 años"),
        _fila("CURP", "Text"),
    )))

    assert md.count("### Pantalla") == 1
    assert "### Pantalla 1 — CIUDADANO — Información personal del ciudadano" in md
    # La nota no se pierde: queda como texto de la pantalla.
    assert "El menor debe de ser mayor de 16" in md


def test_un_parrafo_largo_tampoco_es_un_titulo_de_pantalla():
    largo = ("Para la documentación se indica si es para permiso de menor de "
             "edad o para extranjero, y en cada caso cambian los requisitos "
             "que el ciudadano debe adjuntar al expediente")
    md = a_markdown(_docx(_tabla(
        _fila("Documentación requerida"),
        _fila("Nombre del campo", "Tipo de dato"),
        _fila(largo),
        _fila("Acta", "File"),
    )))

    assert md.count("### Pantalla") == 1


def test_el_campo_que_sigue_a_una_nota_no_se_convierte_en_cabecera():
    """Al partir la tabla con la nota, la siguiente fila de datos pasaba a ser
    la cabecera de la tabla nueva y el campo se perdia. En el Diccionario de
    «Permiso para conducir de menores de edad» eso se comia el campo 'Nombre'."""
    md = a_markdown(_docx(_tabla(
        _fila("Información personal"),
        _fila("Nombre del campo", "Tipo de dato"),
        _fila("Nota: el menor debe tener entre 16 y 18 años"),
        _fila("Nombre", "String"),
        _fila("Apellido Paterno", "String"),
    )))

    # La cabecera se repite para que la tabla siga siendo una tabla...
    assert md.count("| Nombre del campo | Tipo de dato |") == 2
    # ...y el campo sigue siendo un campo.
    assert "| Nombre | String |" in md
