from gpmc.estimador import Metricas, estimar
from gpmc.nucleo.manifiesto import Manifiesto

BASE = {
    "tramite": {"nombre": "X", "dependencia": "D"},
    "actores": [{"id": "c", "nombre": "C"}],
    "pantallas": [{"id": "p1", "nombre": "P", "actor": "c",
                   "campos": [{"nombre": f"c{i}", "tipo": "text"} for i in range(10)]}],
    "flujo": {"tareas": [{"id": "t1", "nombre": "A", "inicial": True, "pantallas": ["p1"]},
                         {"id": "t2", "nombre": "F", "terminal": True}],
              "conexiones": [{"de": "t1", "a": "t2"}]},
    "acciones": [],
}


def test_cuenta_las_seis_metricas():
    e = estimar(Manifiesto.model_validate(BASE))
    assert isinstance(e.metricas, Metricas)
    assert e.metricas.tareas == 2
    assert e.metricas.vistas == 1
    assert e.metricas.campos == 10
    assert e.metricas.bifurcaciones == 0
    assert e.metricas.acciones == 0
    assert e.metricas.integraciones == 0


def test_cuenta_las_integraciones_por_origen():
    d = {**BASE}
    d["pantallas"] = [{**BASE["pantallas"][0],
                       "campos": [{"nombre": "curp", "tipo": "text", "origen": "sipubeh"}]}]
    assert estimar(Manifiesto.model_validate(d)).metricas.integraciones == 1


def test_de_punta_a_punta_diccionario_extractor_estimador(tmp_path):
    """Deuda de proceso: ninguna prueba recorría Diccionario → extractor → estimador,
    así que quitar 'origen' del extractor dejó `integraciones` en 0 para un trámite
    con integraciones sin que nada fallara. Esta prueba cruza esa frontera: un campo
    con endpoint declarado en el Diccionario debe llegar a estimador.integraciones."""
    from gpmc.extractores.expediente import extraer_expediente
    dicc = (
        "### Pantalla 1 — Solicitante — Datos\n\n"
        "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Endpoint | Descripcion |\n"
        "| Estado | Texto | select | mgee | El estado @@estado |\n"
    )
    carpeta = tmp_path / "exp"
    carpeta.mkdir()
    (carpeta / "5.-Diccionario de Datos.md").write_text(dicc, encoding="utf-8")
    r = extraer_expediente(carpeta)
    assert r.manifiesto is not None, r.huecos
    met = estimar(r.manifiesto).metricas
    assert met.integraciones == 1, "el endpoint del Diccionario debe contarse como integración"


def test_clasifica_pero_marca_la_escala_como_no_calibrada():
    e = estimar(Manifiesto.model_validate(BASE))
    assert e.nivel in ("Bajo", "Medio", "Complejo")
    assert e.calibrado is False
    assert "calibrad" in e.advertencia.lower()


def test_explica_que_criterio_determino_el_nivel():
    grande = {**BASE}
    grande["pantallas"] = [{"id": f"p{i}", "nombre": "P", "actor": "c",
                            "campos": [{"nombre": f"x{i}", "tipo": "text"}]} for i in range(15)]
    grande["flujo"] = {"tareas": [{"id": "t1", "nombre": "A", "inicial": True},
                                  {"id": "t2", "nombre": "F", "terminal": True}],
                       "conexiones": [{"de": "t1", "a": "t2"}]}
    e = estimar(Manifiesto.model_validate(grande))
    assert e.nivel == "Complejo"
    assert any("vista" in m.lower() for m in e.motivos), e.motivos


def test_reporta_la_ambiguedad_de_la_tabla_de_origen():
    """El tramite medido (ID 848) tiene 1 integracion API: cinco criterios lo
    ponen en Bajo y ese solo aparece descrito en Medio. La tabla es ambigua."""
    d = {**BASE}
    d["pantallas"] = [{**BASE["pantallas"][0],
                       "campos": [{"nombre": "curp", "tipo": "text", "origen": "sipubeh"}]}]
    e = estimar(Manifiesto.model_validate(d))
    assert any("ambig" in m.lower() or "integracion" in m.lower() or "integración" in m.lower()
               for m in e.motivos), e.motivos
