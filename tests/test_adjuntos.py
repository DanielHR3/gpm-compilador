"""Documentos de apoyo del expediente: diagramas en PNG, PDF escaneados.

No alimentan al extractor —igual que `Vistas.html`— pero el analista los
necesita a la vista mientras resuelve: el diagrama que dice quien hace cada
tarea vivia en un PNG fuera de la herramienta.
"""
import pytest
from fastapi.testclient import TestClient

from gpmc.web.app import crear_app
from gpmc.web.sesiones import nombre_seguro


_DICC = (
    "### Pantalla 1 — CIUDADANO — Solicitud\n\n"
    "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
    "| CURP | Texto | Input | Sí | La CURP `@@curp` |\n"
)


def _cli(tmp_path):
    return TestClient(crear_app(tmp_path))


@pytest.mark.parametrize("entrada,esperado", [
    ("diagrama.png", "diagrama.png"),
    ("../../etc/passwd", "etc_passwd"),
    ("/absoluto/x.pdf", "absoluto_x.pdf"),
    ("con espacios y ñ.PNG", "con espacios y ñ.PNG"),
    ("", "adjunto"),
])
def test_el_nombre_del_adjunto_no_puede_salirse_de_su_carpeta(entrada, esperado):
    """Un nombre lo escribe quien sube el archivo: no puede escribir fuera."""
    assert nombre_seguro(entrada) == esperado


def test_los_adjuntos_se_guardan_y_se_listan_con_el_expediente(tmp_path):
    c = _cli(tmp_path)

    r = c.post("/api/v1/expedientes", files=[
        ("diccionario", ("dd.md", _DICC.encode("utf-8"), "text/markdown")),
        ("adjuntos", ("TO BE.png", b"\x89PNG\r\n\x1a\n falso", "image/png")),
        ("adjuntos", ("Requisitos.pdf", b"%PDF-1.4 falso", "application/pdf")),
    ])

    assert r.status_code == 201, r.text
    adjuntos = r.json()["adjuntos"]
    assert [a["nombre"] for a in adjuntos] == ["TO BE.png", "Requisitos.pdf"]
    assert adjuntos[0]["tipo"] == "imagen"
    assert adjuntos[1]["tipo"] == "pdf"


def test_un_adjunto_se_puede_descargar_despues(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files=[
        ("diccionario", ("dd.md", _DICC.encode("utf-8"), "text/markdown")),
        ("adjuntos", ("TO BE.png", b"\x89PNG\r\n\x1a\n falso", "image/png")),
    ]).json()["sid"]

    r = c.get(f"/api/v1/expedientes/{sid}/adjuntos/TO BE.png")

    assert r.status_code == 200
    assert r.content.startswith(b"\x89PNG")


def test_pedir_un_adjunto_de_otra_carpeta_no_devuelve_nada(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files=[
        ("diccionario", ("dd.md", _DICC.encode("utf-8"), "text/markdown")),
    ]).json()["sid"]

    r = c.get(f"/api/v1/expedientes/{sid}/adjuntos/..%2F..%2Fmanifiesto.yaml")

    assert r.status_code == 404


def test_un_expediente_sin_adjuntos_los_lista_vacios(tmp_path):
    c = _cli(tmp_path)

    r = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")})

    assert r.json()["adjuntos"] == []
