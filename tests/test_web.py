from pathlib import Path

import pytest

from tests.conftest import WIKI, legible as _legible
from fastapi.testclient import TestClient

from gpmc.web.app import crear_app


EXPEDIENTE = WIKI / "anita" / "Alta de Avisos de Testamento"


@pytest.fixture
def cliente(tmp_path):
    return TestClient(crear_app(almacen=tmp_path))


def _insumos():
    if not _legible(EXPEDIENTE / "Diccionario de Datos.md"):
        pytest.skip("expediente de referencia no disponible")
    return {
        "as_is": (EXPEDIENTE / "Análisis AS-IS.md").read_bytes(),
        "to_be": (EXPEDIENTE / "Propuesta TO-BE.md").read_bytes(),
        "diccionario": (EXPEDIENTE / "Diccionario de Datos.md").read_bytes(),
    }


def test_la_portada_pide_los_tres_insumos(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    for campo in ("as_is", "to_be", "diccionario", "vistas"):
        assert f'name="{campo}"' in r.text


def test_subir_los_insumos_crea_una_sesion_y_extrae(cliente):
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    }, follow_redirects=False)
    assert r.status_code in (302, 303), r.text
    assert "/revisar/" in r.headers["location"]


# Diccionario mínimo e inline: no depende de GPMC_WIKI, así la prueba corre en
# un checkout limpio. Sin TO-BE => INS-01 bloqueante; 'Nombre' sin @@ => DIC-01
# por_confirmar. Dos niveles presentes, que es lo que la prueba verifica.
_DICC_MIN = """### Pantalla 1 — Solicitante — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |
| CURP | Texto | Input | Sí | La CURP @@curp |
| Nombre | Texto | Input | Sí | El nombre del solicitante |
"""


def test_el_paso_de_revision_agrupa_huecos_por_nivel(cliente):
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
    })
    assert r.status_code == 200, r.text
    texto = r.text.lower()
    assert "por confirmar" in texto
    assert "bloqueante" in texto or "faltan datos" in texto
    assert "<details" in r.text


def test_revision_enlaza_al_simulador_en_la_misma_pestana(cliente):
    # El navegador bloquea las pestañas nuevas de target="_blank"; los botones
    # de navegación del asistente deben abrir en la misma pestaña.
    # Excepcion: el enlace de vistas sí abre en pestaña nueva.
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
    })
    sid = r.url.path.rsplit("/", 1)[-1]
    assert f'href="/simulador/{sid}"' in r.text
    # Contar target="_blank": sin vistas subidas, no debe haber ninguno
    assert 'target="_blank"' not in r.text


# ── Vistas HTML (mockup de referencia visual) ────────────────────────

_HTML_VISTAS = b"""<!doctype html><html><body>
<h1>Mockup de pantallas</h1>
<p>Pantalla 1: Datos del solicitante</p>
</body></html>"""


def test_subir_vistas_las_persiste_y_la_revision_muestra_el_enlace(cliente):
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
        "vistas": ("vistas.html", _HTML_VISTAS, "text/html"),
    })
    assert r.status_code == 200, r.text
    assert "Ver vistas (HTML)" in r.text
    assert 'target="_blank"' in r.text  # el enlace de vistas abre en nueva pestaña


def test_el_endpoint_de_vistas_sirve_el_html_subido(cliente):
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
        "vistas": ("vistas.html", _HTML_VISTAS, "text/html"),
    })
    sid = r.url.path.rsplit("/", 1)[-1]
    v = cliente.get(f"/vistas/{sid}")
    assert v.status_code == 200
    assert "Mockup de pantallas" in v.text


def test_sin_vistas_el_enlace_no_aparece_y_el_endpoint_devuelve_404(cliente):
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
    })
    assert "Ver vistas (HTML)" not in r.text
    sid = r.url.path.rsplit("/", 1)[-1]
    v = cliente.get(f"/vistas/{sid}")
    assert v.status_code == 404


def test_vistas_de_sesion_inexistente_devuelve_404(cliente):
    assert cliente.get("/vistas/noexiste").status_code == 404


# ── Resolucion interactiva de huecos (POST /resolver) ────────────────


def test_resolver_una_sesion_inexistente_devuelve_404(cliente):
    # Regresion: el handler declaraba `request: Request` sin importar Request,
    # asi que FastAPI trataba `request` como query param obligatorio y todo
    # POST a /resolver devolvia 422 antes de llegar a la logica.
    r = cliente.post("/resolver/0123456789abcdef", data={"meta01": "x"})
    assert r.status_code == 404


def test_resolver_aplica_la_respuesta_al_manifiesto_y_redirige(cliente):
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
    })
    sid = r.url.path.rsplit("/", 1)[-1]

    resp = cliente.post(f"/resolver/{sid}", data={"meta01": "10 dias habiles"},
                        follow_redirects=False)
    assert resp.status_code == 303, resp.text
    assert resp.headers["location"] == f"/revisar/{sid}"

    yaml = cliente.get(f"/descargar/{sid}/manifiesto").text
    assert "10 dias habiles" in yaml


def test_descargar_el_gpm_de_una_sesion(cliente):
    import json
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    }, follow_redirects=False)
    sid = r.headers["location"].rsplit("/", 1)[-1]

    g = cliente.get(f"/descargar/{sid}/gpm")
    assert g.status_code == 200
    assert g.headers["content-type"].startswith("application/")
    datos = json.loads(g.content)
    assert datos["nombre"] == "Alta de Avisos de Testamento"
    assert datos["Sections"] == []


def test_descargar_el_simulador_de_una_sesion(cliente):
    ins = _insumos()
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", ins["as_is"], "text/markdown"),
        "to_be": ("tb.md", ins["to_be"], "text/markdown"),
        "diccionario": ("dd.md", ins["diccionario"], "text/markdown"),
    }, follow_redirects=False)
    sid = r.headers["location"].rsplit("/", 1)[-1]

    s = cliente.get(f"/simulador/{sid}")
    assert s.status_code == 200
    assert "simulaci" in s.text.lower()
    assert "http://" not in s.text and "https://" not in s.text


def test_una_sesion_inexistente_devuelve_404(cliente):
    assert cliente.get("/revisar/noexiste").status_code == 404
    assert cliente.get("/descargar/noexiste/gpm").status_code == 404


def test_rechaza_una_carga_sin_diccionario(cliente):
    r = cliente.post("/extraer", files={
        "as_is": ("as.md", b"# vacio", "text/markdown"),
        "to_be": ("tb.md", b"# vacio", "text/markdown"),
        "diccionario": ("dd.md", b"", "text/markdown"),
    })
    assert r.status_code == 200
    assert "Diccionario" in r.text


def test_el_identificador_de_sesion_no_permite_salir_del_almacen(cliente):
    for malo in ("../../etc", "..%2f..", "a/b"):
        r = cliente.get(f"/descargar/{malo}/gpm")
        assert r.status_code in (400, 404), f"{malo} devolvio {r.status_code}"


# Manifiesto minimo y valido, inline: no depende de GPMC_WIKI.
_MANIFIESTO_BUENO = """tramite: {nombre: "Trámite Bueno", dependencia: "DEP"}
actores: [{id: u, nombre: U}]
flujo:
  tareas:
  - {id: t1, nombre: T1, actor: u, inicial: true, terminal: true}
  conexiones: []
"""

# Valido como YAML pero de un esquema anterior: 'cargar' revienta al validarlo.
_MANIFIESTO_CORRUPTO = """tramite: {nombre: "Viejo"}
campos_antiguos: []
"""


def test_historial_vacio_responde_200(cliente):
    r = cliente.get("/historial")
    assert r.status_code == 200
    assert "Historial" in r.text


def test_historial_sobrevive_a_una_sesion_con_manifiesto_corrupto(cliente, tmp_path):
    buena = tmp_path / ("a" * 16)
    buena.mkdir()
    (buena / "manifiesto.yaml").write_text(_MANIFIESTO_BUENO, encoding="utf-8")
    mala = tmp_path / ("b" * 16)
    mala.mkdir()
    (mala / "manifiesto.yaml").write_text(_MANIFIESTO_CORRUPTO, encoding="utf-8")

    r = cliente.get("/historial")
    assert r.status_code == 200
    assert "Trámite Bueno" in r.text


def test_descargar_plantilla_responde_con_contenido(cliente):
    r = cliente.get("/descargar-plantilla")
    assert r.status_code == 200
    assert r.content
    assert "Diccionario de Datos" in r.text


# ── Linter: la puerta de /descargar/{sid}/gpm ───────────────────────

_TOBE_LINEAL = """# Propuesta TO-BE — Trámite Mínimo

```mermaid
flowchart TD
    classDef solicitante fill:#eee
    A([Inicio]):::solicitante --> B[Solicitante: Datos]:::solicitante
    B --> C([Fin]):::solicitante
```
"""


def _sid_de(r):
    return r.headers["location"].rsplit("/", 1)[-1]


def test_descargar_gpm_bloqueado_por_huecos_devuelve_409(cliente):
    """Solo Diccionario: falta el TO-BE (INS-01, bloqueante). El .gpm no se
    entrega."""
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
    }, follow_redirects=False)
    sid = _sid_de(r)
    g = cliente.get(f"/descargar/{sid}/gpm")
    assert g.status_code == 409
    assert "INS-01" in g.text


def test_reconocer_los_huecos_levanta_la_puerta_y_permite_descargar(cliente):
    """Diccionario + TO-BE lineal: los únicos bloqueantes son META-01 y META-02
    (falta_dato). Tras reconocer cada uno, el .gpm se descarga."""
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
        "to_be": ("tb.md", _TOBE_LINEAL.encode("utf-8"), "text/markdown"),
    }, follow_redirects=False)
    sid = _sid_de(r)

    assert cliente.get(f"/descargar/{sid}/gpm").status_code == 409

    for codigo in ("META-01", "META-02"):
        resp = cliente.post(f"/reconocer/{sid}", data={"reconocer": f"{codigo}|metadatos"},
                            follow_redirects=False)
        assert resp.status_code == 303

    g = cliente.get(f"/descargar/{sid}/gpm")
    assert g.status_code == 200, g.text
    assert g.headers["content-type"].startswith("application/")


_DICC_CON_DIC07 = """### Pantalla 1 — Solicitante — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 | N/A | X | [Captura] `@@curp` |
| Tipo | Select | Lista desplegable (select) | Sí | Siempre visible | N/A | Valores definidos | Uno | [Captura] `@@tipo` |
"""


def test_la_revision_ofrece_configurar_a_mano_los_huecos_no_interactivos(cliente):
    """DIC-07 (un select sin catálogo) no se resuelve en el asistente: la
    revisión ofrece 'Lo configuro a mano', y tras marcarlo queda constancia."""
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_CON_DIC07.encode("utf-8"), "text/markdown"),
        "to_be": ("tb.md", _TOBE_LINEAL.encode("utf-8"), "text/markdown"),
    }, follow_redirects=False)
    sid = _sid_de(r)
    pagina = cliente.get(f"/revisar/{sid}").text
    assert f'formaction="/reconocer/{sid}"' in pagina
    assert 'value="DIC-07|p1"' in pagina

    cliente.post(f"/reconocer/{sid}", data={"reconocer": "DIC-07|p1"})
    pagina2 = cliente.get(f"/revisar/{sid}").text
    assert "lo configuraré a mano" in pagina2
