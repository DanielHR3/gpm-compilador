# tests/test_documento_estilo.py
"""Los dos documentos descargables (comparativa y documentos del tramite)
comparten cabecera, pie y hoja de estilo: la misma identidad que la SPA."""
from datetime import date

from gpmc.comparativa import estilo
from gpmc.comparativa.armar import Comparativa
from gpmc.comparativa.documento import a_html as comparativa_html
from gpmc.comparativa.pagina_documentos import a_html as documentos_html


def test_la_hoja_lleva_el_guinda_institucional_y_la_tipografia_de_la_spa():
    assert "#A02142" in estilo.CSS or "#a02142" in estilo.CSS.lower()
    # Montserrat es la tipografia del sistema de diseno; si no esta instalada,
    # cae a la del sistema. Nunca se carga de la red.
    assert "Montserrat" in estilo.CSS and "@import" not in estilo.CSS and "http" not in estilo.CSS


def test_la_cabecera_y_el_pie_dicen_que_es_y_de_cuando():
    html = estilo.pagina("Antes y después", "Trámite X", "<p>cuerpo</p>", "Uso interno.",
                         hoy=date(2026, 10, 16))
    assert "<!doctype html>" in html.lower() and 'lang="es"' in html
    assert "<title>Antes y después — Trámite X</title>" in html
    assert "Compilador GPM" in html and "Simplificación Administrativa" in html
    assert "16 de octubre de 2026" in html
    assert "<p>cuerpo</p>" in html
    assert "<script" not in html


def test_los_dos_documentos_usan_la_misma_cabecera():
    c = Comparativa(disponible=False, motivo="Sin AS-IS", tramite="X")
    uno = comparativa_html(c)
    dos = documentos_html("X", {"titular": "t", "por_destino": {}, "agregados": [],
                                "simplificacion": []}, [])
    for html in (uno, dos):
        assert 'class="cabecera"' in html and 'class="pie"' in html
        assert "Compilador GPM" in html
