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


def test_con_documentos_revisados_dice_como_se_simplifico():
    from gpmc.comparativa.documentos import decidir, inventario_determinista
    m = _m()
    docs = inventario_determinista("- **Requisitos:** identificación oficial, <i>orden</i>\n", m)
    decidir(docs[0], "conserva")
    decidir(docs[1], "elimina")
    html = a_html(comparar(_estado(), Rediseno(), m, documentos=docs))
    assert "De 2 documentos que pedía el trámite, 1 ya no se pide." in html
    assert "<strong>Se eliminó:</strong> &lt;i&gt;orden&lt;/i&gt;" in html
    assert "<i>orden</i>" not in html


def test_sin_documentos_revisados_el_documento_no_los_menciona():
    assert "Documentos del trámite" not in a_html(comparar(_estado(), Rediseno(), _m()))


def _con_agente():
    from gpmc.comparativa.propuestas import Evidencia, Mejora, Propuesta
    from gpmc.extractores.rediseno import Elemento
    r = Rediseno(elementos=[
        Elemento("Requisito: <b>acta</b>", "Sí", "Se consulta en línea.", "elimina", "requisito"),
        Elemento("Paso 3. Revisión", "No, se conserva", "", "conserva", "paso")])
    propuestas = [Propuesta("visitas", "antes", [
        Evidencia("Ir a <i>ventanilla</i>", "Usuario lo lleva a Ventanilla"),
        Evidencia("Ir al banco", "paga (en banco)")], motivo="Va dos veces en persona.")]
    mejoras = [
        Mejora("a1", "Quitar la tarjeta", "documento", "Consultarla en el padrón.",
               "Ahorra un escaneo.", cita="Se adjunta en PDF", fuente="to_be",
               campo="doc_tarjeta", etiqueta_campo="Tarjeta de Circulación", requiere="convenio",
               accion="eliminar"),
        Mejora("b2", "Punto descartado", "paso", "x", "y", descartada=True)]
    return comparar(_estado(), r, _m(), propuestas=propuestas, mejoras=mejoras)


def test_el_documento_enseña_la_evidencia_de_cada_cifra_propuesta():
    html = a_html(_con_agente())
    assert "propuesto por el agente" in html
    assert "Va dos veces en persona." in html
    assert "«Usuario lo lleva a Ventanilla»" in html
    # El nombre lo redacta el modelo: entra escapado como cualquier otro dato.
    assert "<i>ventanilla</i>" not in html and "&lt;i&gt;ventanilla&lt;/i&gt;" in html


def test_el_documento_trae_el_resumen_los_elementos_y_las_mejoras_vivas():
    html = a_html(_con_agente())
    assert "De los 2 elementos del trámite actual que revisó el equipo" in html
    assert "Qué pasó con cada elemento del trámite" in html
    assert "<b>acta</b>" not in html and "Se consulta en línea." in html
    assert "Qué más se puede simplificar" in html and "Quitar la tarjeta" in html
    assert "A futuro: requiere conectar" in html and "Tarjeta de Circulación" in html
    assert "Se puede eliminar" in html
    assert "Punto descartado" not in html


def test_sin_agente_ni_tabla_el_documento_no_inventa_secciones():
    html = a_html(comparar(_estado(), Rediseno(), _m()))
    assert "Qué más se puede simplificar" not in html
    assert "Qué pasó con cada elemento" not in html
