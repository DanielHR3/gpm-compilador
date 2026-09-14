"""Documentos que el tramite genera: oficios, acuses, constancias.

El compilador ya sabia emitir un Documento PDF de GPM (acciones.py), pero nada
del expediente lo alimentaba: el extractor nunca creaba una accion. Casi todo
tramite devuelve un documento al ciudadano, asi que la plantilla entra al
expediente como un .md con {{variables}} en la carpeta `documentos/`.
"""
from pathlib import Path

from fastapi.testclient import TestClient

from gpmc.compilador.acciones import construir_acciones
from gpmc.extractores.expediente import extraer_expediente
from gpmc.web.app import crear_app


_DICC = (
    "### Pantalla 1 — CIUDADANO — Solicitud\n\n"
    "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
    "| CURP | Texto | Input | Sí | La CURP `@@curp` |\n"
    "| Nombre | Texto | Input | Sí | El nombre `@@nombre` |\n"
)


def _expediente(tmp_path: Path, plantillas: dict[str, str]) -> Path:
    (tmp_path / "Diccionario de Datos.md").write_text(_DICC, encoding="utf-8")
    d = tmp_path / "documentos"
    d.mkdir()
    for nombre, cuerpo in plantillas.items():
        (d / nombre).write_text(cuerpo, encoding="utf-8")
    return tmp_path


def test_una_plantilla_con_variables_declaradas_se_vuelve_una_accion_documento(tmp_path):
    r = extraer_expediente(_expediente(tmp_path, {
        "oficio-respuesta.md": "Estimado {{nombre}}, su CURP {{curp}} fue registrada.",
    }))

    docs = [a for a in r.manifiesto.acciones if a.tipo == "documento"]
    assert len(docs) == 1
    a = docs[0]
    assert a.nombre == "oficio-respuesta"
    datos = a.model_dump()
    assert datos["plantilla"] == "Estimado {{nombre}}, su CURP {{curp}} fue registrada."
    assert sorted(datos["variables"]) == ["curp", "nombre"]
    assert not [h for h in r.huecos if h.codigo.startswith("DOC-")]


def test_una_variable_que_no_es_campo_del_diccionario_se_reporta_y_no_se_emite(tmp_path):
    """Emitirla reventaria php_documento (variable no declarada). Mejor un hueco
    que diga cual, y la plantilla se queda fuera hasta que se corrija."""
    r = extraer_expediente(_expediente(tmp_path, {
        "oficio.md": "Folio {{folio_inexistente}} para {{nombre}}.",
    }))

    assert not [a for a in r.manifiesto.acciones if a.tipo == "documento"]
    h = [x for x in r.huecos if x.codigo == "DOC-02"]
    assert len(h) == 1
    assert h[0].nivel == "falta_dato"
    assert "folio_inexistente" in h[0].mensaje
    assert "oficio" in h[0].mensaje


def test_la_cabecera_de_la_plantilla_fija_firmante_y_titulo(tmp_path):
    r = extraer_expediente(_expediente(tmp_path, {
        "constancia.md": (
            "---\n"
            "titulo: Constancia de registro\n"
            "firmador_nombre: Mtro. M. Pedro Velázquez Bárcena\n"
            "firmador_cargo: Director General\n"
            "---\n"
            "Se hace constar que {{nombre}} quedó registrado."
        ),
    }))

    a = next(x for x in r.manifiesto.acciones if x.tipo == "documento")
    assert a.titulo == "Constancia de registro"
    assert a.firmador_nombre == "Mtro. M. Pedro Velázquez Bárcena"
    assert a.firmador_cargo == "Director General"
    # La cabecera no forma parte del texto del documento.
    assert "firmador" not in a.model_dump()["plantilla"]


def test_un_archivo_que_no_es_md_en_documentos_se_reporta_en_vez_de_ignorarse(tmp_path):
    """Un oficio escaneado en .docx no se puede leer como plantilla. Si se
    ignora en silencio, el analista cree que su documento entro."""
    r = extraer_expediente(_expediente(tmp_path, {"Oficio.docx": "no importa"}))

    h = [x for x in r.huecos if x.codigo == "DOC-03"]
    assert len(h) == 1
    assert "Oficio.docx" in h[0].mensaje


def test_sin_carpeta_documentos_no_hay_acciones_ni_huecos_de_documento(tmp_path):
    (tmp_path / "Diccionario de Datos.md").write_text(_DICC, encoding="utf-8")

    r = extraer_expediente(tmp_path)

    assert r.manifiesto.acciones == []
    assert not [x for x in r.huecos if x.codigo.startswith("DOC-")]


def test_la_accion_extraida_produce_un_documento_pdf_en_el_gpm(tmp_path):
    """De punta a punta: plantilla del expediente -> entidad Documento de GPM."""
    r = extraer_expediente(_expediente(tmp_path, {
        "acuse.md": "---\ntitulo: Acuse\n---\nAcuse para {{nombre}}.",
    }))

    _, documentos, *_ = construir_acciones(r.manifiesto.acciones, proceso_id="1", ids=iter(range(100, 200)))

    assert len(documentos) == 1
    assert documentos[0]["output"] == "pdf"
    assert documentos[0]["titulo"] == "Acuse"


def test_las_plantillas_se_suben_con_el_expediente_y_se_guardan_en_documentos(tmp_path):
    c = TestClient(crear_app(tmp_path))

    r = c.post("/api/v1/expedientes", files=[
        ("diccionario", ("dd.md", _DICC.encode("utf-8"), "text/markdown")),
        ("documentos", ("oficio.md", "Hola {{nombre}}".encode("utf-8"), "text/markdown")),
    ])

    assert r.status_code == 201, r.text
    acciones = r.json()["manifiesto"]["acciones"]
    assert [a["nombre"] for a in acciones if a["tipo"] == "documento"] == ["oficio"]
