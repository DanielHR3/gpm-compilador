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


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _parrafo(*runs: str) -> str:
    """Un parrafo de Word; cada argumento es un run (Word parte el texto asi)."""
    return "<w:p>" + "".join(f"<w:r><w:t xml:space=\"preserve\">{r}</w:t></w:r>" for r in runs) + "</w:p>"


def _docx(*parrafos: str) -> bytes:
    import io
    import zipfile
    doc = (f'<?xml version="1.0"?><w:document xmlns:w="{_W}"><w:body>'
           + "".join(parrafos) + "</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def _pdf(texto: str) -> bytes:
    """Un PDF de una pagina con texto real (fuente + operador Tj)."""
    contenido = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n" + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    desplazamientos = []
    for i, obj in enumerate(objetos, 1):
        desplazamientos.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for d in desplazamientos:
        salida += f"{d:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(salida)


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
    assert not [h for h in r.huecos if h.codigo.startswith("DOC-") and h.nivel == "falta_dato"]


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


def test_un_archivo_que_no_es_plantilla_en_documentos_se_reporta_en_vez_de_ignorarse(tmp_path):
    """Una foto del oficio no se puede leer como plantilla. Si se ignora en
    silencio, el analista cree que su documento entro."""
    r = extraer_expediente(_expediente(tmp_path, {"Oficio.png": "no importa"}))

    h = [x for x in r.huecos if x.codigo == "DOC-03"]
    assert len(h) == 1
    assert "Oficio.png" in h[0].mensaje
    assert not r.manifiesto.acciones


def test_una_plantilla_en_word_se_lee_igual_que_una_en_markdown(tmp_path):
    """Simplificacion escribe los oficios en Word; no deberia tener que pasarlos
    a mano a .md. Word ademas parte «{{curp}}» en varios runs al teclearlo."""
    r = extraer_expediente(_expediente(tmp_path, {}))  # solo para el Diccionario
    (tmp_path / "documentos" / "Constancia.docx").write_bytes(_docx(
        _parrafo("Se hace constar que ", "{{", "nombre", "}}", " quedó registrado."),
        _parrafo(),
        _parrafo("CURP: {{curp}}"),
    ))
    r = extraer_expediente(tmp_path)

    assert not [x for x in r.huecos if x.codigo.startswith("DOC-") and x.nivel == "falta_dato"]
    [a] = r.manifiesto.acciones
    assert a.nombre == "Constancia"
    assert a.variables == ["curp", "nombre"]
    assert a.plantilla == "Se hace constar que {{nombre}} quedó registrado.\n\nCURP: {{curp}}"


def test_un_word_corrupto_en_documentos_se_reporta_como_ilegible(tmp_path):
    r = extraer_expediente(_expediente(tmp_path, {"Oficio.docx": "esto no es un zip"}))

    h = [x for x in r.huecos if x.codigo == "DOC-03"]
    assert len(h) == 1
    assert "Oficio.docx" in h[0].mensaje
    assert "Word" in h[0].mensaje


def test_una_plantilla_en_pdf_con_texto_se_lee(tmp_path):
    _expediente(tmp_path, {})
    (tmp_path / "documentos" / "Acuse.pdf").write_bytes(_pdf("Acuse para {{nombre}}"))
    r = extraer_expediente(tmp_path)

    assert not [x for x in r.huecos if x.codigo.startswith("DOC-") and x.nivel == "falta_dato"]
    [a] = r.manifiesto.acciones
    assert a.nombre == "Acuse"
    assert a.variables == ["nombre"]
    assert "Acuse para {{nombre}}" in a.plantilla


def test_un_pdf_escaneado_en_documentos_se_reporta_y_pide_el_texto(tmp_path):
    """Sin OCR a proposito: el compilador lee, nunca adivina."""
    _expediente(tmp_path, {})
    (tmp_path / "documentos" / "Oficio.pdf").write_bytes(b"%PDF-1.4\n1 0 obj << /Type /XObject /Subtype /Image >> endobj\n%%EOF")
    r = extraer_expediente(tmp_path)

    h = [x for x in r.huecos if x.codigo == "DOC-03"]
    assert len(h) == 1
    assert "escaneado" in h[0].mensaje
    assert not r.manifiesto.acciones


def test_sin_carpeta_documentos_no_hay_acciones_ni_huecos_de_documento(tmp_path):
    (tmp_path / "Diccionario de Datos.md").write_text(_DICC, encoding="utf-8")

    r = extraer_expediente(tmp_path)

    assert r.manifiesto.acciones == []
    assert not [x for x in r.huecos if x.codigo.startswith("DOC-") and x.nivel == "falta_dato"]


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


# --- El documento tiene que dispararse desde una tarea -----------------------

_DICC_DOS_PANTALLAS = (
    "### Pantalla 1 — CIUDADANO — Solicitud\n\n"
    "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
    "| CURP | Texto | Input | Sí | La CURP `@@curp` |\n\n"
    "### Pantalla 2 — CIUDADANO — Vehículo\n\n"
    "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
    "| Placa | Texto | Input | Sí | La placa `@@placa` |\n"
)


def test_el_documento_se_genera_al_terminar_la_primera_tarea_que_ya_tiene_todos_sus_datos(tmp_path):
    """Un Documento con su Accion pero sin Evento en ninguna tarea es un PDF que
    nunca se produce. La tarea correcta se lee de los datos: la primera en la
    que ya se capturaron todas las variables de la plantilla."""
    (tmp_path / "Diccionario de Datos.md").write_text(_DICC_DOS_PANTALLAS, encoding="utf-8")
    (tmp_path / "documentos").mkdir()
    (tmp_path / "documentos" / "Constancia.md").write_text(
        "Constancia de {{curp}} con placa {{placa}}.", encoding="utf-8")
    r = extraer_expediente(tmp_path)

    con_accion = [t for t in r.manifiesto.flujo.tareas if "Constancia" in t.acciones_despues]
    assert [t.nombre for t in con_accion] == ["Vehículo"]
    assert not any("Constancia" in t.acciones_antes for t in r.manifiesto.flujo.tareas)

    [h] = [x for x in r.huecos if x.codigo == "DOC-04"]
    assert h.nivel == "por_confirmar"
    assert "Constancia" in h.mensaje and "Vehículo" in h.mensaje


def test_si_el_documento_solo_usa_datos_de_la_primera_pantalla_se_genera_ahi(tmp_path):
    (tmp_path / "Diccionario de Datos.md").write_text(_DICC_DOS_PANTALLAS, encoding="utf-8")
    (tmp_path / "documentos").mkdir()
    (tmp_path / "documentos" / "Acuse.md").write_text("Acuse de {{curp}}.", encoding="utf-8")
    r = extraer_expediente(tmp_path)

    con_accion = [t.nombre for t in r.manifiesto.flujo.tareas if "Acuse" in t.acciones_despues]
    assert con_accion == ["Solicitud"]


def test_el_gpm_lleva_el_evento_que_dispara_el_documento(tmp_path):
    from gpmc.compilador.a_gpm import compilar

    r = extraer_expediente(_expediente(tmp_path, {"oficio.md": "Hola {{nombre}}"}))
    g = compilar(r.manifiesto, proceso_id="1")

    [accion] = [a for a in g["Acciones"] if a["nombre"] == "oficio"]
    eventos = [e for t in g["Tareas"] for e in t["Eventos"] if e["accion_id"] == str(accion["id"])]
    assert len(eventos) == 1
    assert eventos[0]["instante"] == "despues"
