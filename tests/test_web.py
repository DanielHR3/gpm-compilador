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


def test_la_raiz_sirve_la_spa_no_html_viejo(monkeypatch, tmp_path):
    dist = tmp_path / "dist"; dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    assert 'id=root' in c.get("/").text
    assert 'id=root' in c.get("/revisar/" + "a" * 16).text     # fallback SPA
    assert c.get("/historial").status_code == 200               # HTML viejo sigue


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


# ── Vistas HTML (mockup de referencia visual) ────────────────────────

_HTML_VISTAS = b"""<!doctype html><html><body>
<h1>Mockup de pantallas</h1>
<p>Pantalla 1: Datos del solicitante</p>
</body></html>"""


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
    # `/revisar/*` ya no es un handler HTML: cae al fallback de la SPA (Task 11).
    # El 404 de sesión inexistente vive ahora en los endpoints reales.
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
        # El endpoint rechaza el sid raro (404/400); si el cliente colapsa el
        # `..` y la ruta ya no cae bajo /descargar, termina en el fallback de la
        # SPA (index.html o 503). En ningún caso se entrega un archivo de fuera
        # del almacén.
        assert r.status_code in (400, 404, 503, 200), f"{malo} devolvio {r.status_code}"
        assert "root:" not in r.text and "/bin/" not in r.text


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


# ── Endurecimiento (auditoría 2026-09-08) ──────────────────────────

def test_toda_respuesta_trae_cabeceras_de_seguridad(cliente):
    # `/` ahora sirve la SPA (o 503 si dist/ no está compilado); el middleware
    # de cabeceras seguras aplica a cualquier respuesta.
    r = cliente.get("/")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "SAMEORIGIN"


def test_vistas_se_sirve_en_sandbox(cliente):
    r = cliente.post("/extraer", files={
        "diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown"),
        "vistas": ("v.html", b"<html><body><script>alert(1)</script>ok</body></html>", "text/html"),
    }, follow_redirects=False)
    sid = _sid_de(r)
    v = cliente.get(f"/vistas/{sid}")
    assert v.status_code == 200
    assert "sandbox" in v.headers.get("content-security-policy", "")


def test_un_archivo_gigante_da_un_error_visible_con_el_nombre(cliente):
    grande = b"x" * (11 * 1024 * 1024)  # 11 MB > tope de 10
    r = cliente.post("/extraer", files={
        "diccionario": ("enorme.md", grande, "text/markdown"),
    }, follow_redirects=False)
    assert r.status_code == 200
    # Antes se descartaba en silencio y se quejaba de "falta el Diccionario".
    assert "supera el límite de 10 MB" in r.text
    assert "enorme.md" in r.text


# ── Purga de sesiones viejas (fuga de disco) ────────────────────────

def test_purga_borra_sesiones_viejas_y_respeta_las_recientes(tmp_path):
    import time, os
    from gpmc.web.app import _purgar_sesiones, crear_app
    from fastapi.testclient import TestClient

    raiz = tmp_path / "almacen"
    raiz.mkdir()
    vieja = raiz / ("a" * 16)
    vieja.mkdir()
    (vieja / "manifiesto.yaml").write_text("x", encoding="utf-8")
    fresca = raiz / ("b" * 16)
    fresca.mkdir()
    ajena = raiz / "no-es-sesion"          # nombre que no casa: no se toca
    ajena.mkdir()

    viejo = time.time() - 8 * 86400
    os.utime(vieja, (viejo, viejo))
    os.utime(ajena, (viejo, viejo))

    _purgar_sesiones(raiz, dias=7)
    assert not vieja.exists()
    assert fresca.exists()
    assert ajena.exists()


def test_extraer_dispara_la_purga(tmp_path):
    import time, os
    from fastapi.testclient import TestClient
    from gpmc.web.app import crear_app

    raiz = tmp_path / "alm"
    raiz.mkdir()
    vieja = raiz / ("c" * 16)
    vieja.mkdir()
    viejo = time.time() - 30 * 86400
    os.utime(vieja, (viejo, viejo))

    cli = TestClient(crear_app(almacen=raiz))
    cli.post("/extraer", files={"diccionario": ("dd.md", _DICC_MIN.encode("utf-8"), "text/markdown")})
    assert not vieja.exists()


def test_sin_dist_construido_la_ruta_app_da_503(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(tmp_path / "no-existe"))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    r = c.get("/app")
    assert r.status_code == 503
    assert "npm run build" in r.text


def test_con_dist_falso_la_ruta_app_sirve_index(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "x.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    assert c.get("/app").status_code == 200
    assert "SPA" in c.get("/app").text
    assert c.get("/app/assets/x.js").status_code == 200
    assert c.get("/app").headers["content-security-policy"].startswith("default-src 'self'")


def test_la_ruta_app_no_permite_salir_de_dist(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))

    # Percent-encoded `..`: no debe entregar un fichero de fuera de dist; cae
    # al fallback de index.html como cualquier ruta de cliente desconocida.
    r = c.get("/app/%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd")
    assert r.status_code == 200
    assert "SPA" in r.text
    assert "root:" not in r.text

    # Variante `../` en claro (el cliente puede colapsarla; da igual: el
    # resultado no debe contener el fichero ajeno).
    r = c.get("/app/../../../etc/passwd", follow_redirects=True)
    assert "root:" not in r.text


def test_index_html_directo_lleva_csp(monkeypatch, tmp_path):
    # `index.html` es un archivo real de dist/, así que `GET /index.html` entra
    # por la rama de FileResponse: debe llevar la misma CSP que `/`.
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><title>SPA</title>", encoding="utf-8"
    )
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    r = c.get("/index.html")
    assert r.status_code == 200
    assert r.headers["content-security-policy"].startswith("default-src 'self'")
