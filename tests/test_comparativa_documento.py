# tests/test_comparativa_documento.py
from gpmc.comparativa.armar import comparar, no_disponible
from gpmc.comparativa.documento import a_html, grafica_svg
from gpmc.extractores.as_is import EstadoActual
from gpmc.extractores.rediseno import Rediseno
from tests.test_comparativa import _estado, _m


def test_el_documento_es_una_pagina_completa_en_utf8():
    html = a_html(comparar(_estado(), Rediseno(), _m()))
    assert html.startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in html
    assert "Trámite de prueba" in html
    assert "Requisitos documentales" in html
    assert "sobre 2 de 7 métricas" in html


def test_no_carga_nada_de_fuera():
    html = a_html(comparar(_estado(), Rediseno(), _m()))
    assert "http://" not in html.replace("http://www.w3.org/2000/svg", "")
    assert "https://" not in html
    assert "<script" not in html


def test_un_requisito_hostil_sale_como_texto():
    hostil = '<script>alert(1)</script>'
    html = a_html(comparar(_estado(requisitos=[hostil, "b"]), Rediseno(), _m()))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_una_metrica_declarada_hostil_no_rompe_el_svg():
    c = comparar(_estado(), Rediseno(), _m(),
                 declaradas={"visitas": {"antes": "2 </svg><b>", "despues": "0 </svg><b>"}})
    html = a_html(c)
    assert "</svg><b>" not in html


def test_la_grafica_lleva_una_pareja_de_barras_por_metrica_comparable():
    svg = grafica_svg(comparar(_estado(), Rediseno(), _m()).metricas)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert svg.count("<rect") == 4
    assert 'role="img"' in svg and "<title>" in svg
    # El valor va escrito: el color no es el unico portador del dato.
    assert "−50 %" in svg


def test_sin_metricas_comparables_no_hay_grafica():
    assert grafica_svg(comparar(EstadoActual(), Rediseno(), _m()).metricas) == ""
    html = a_html(comparar(EstadoActual(), Rediseno(), _m()))
    assert "<svg" not in html and "No se puede medir" in html


def test_cada_valor_dice_su_origen():
    html = a_html(comparar(_estado(), Rediseno(), _m()))
    for origen in ("contado", "leído", "sin dato"):
        assert origen in html


def test_sin_as_is_el_documento_lo_dice():
    html = a_html(no_disponible("No se cargó el Análisis AS-IS."))
    assert "No se cargó el Análisis AS-IS." in html and "<svg" not in html
