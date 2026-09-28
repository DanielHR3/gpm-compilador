# tests/test_pagina_documentos.py
from gpmc.comparativa.documentos import decidir, inventario_determinista, resumen
from gpmc.comparativa.pagina_documentos import a_html
from tests.test_documentos import _ASIS, _m


def _pagina(decididos=True):
    m = _m(extra_ciudadano=(("doc_rfc", "Documento: RFC"),))
    docs = inventario_determinista(_ASIS, m)
    if decididos:
        decidir(docs[0], "elimina", "Se valida con la CURP.")
        docs[0].cita_to_be = "La identificación oficial se elimina"
        decidir(docs[1], "conserva")
        decidir(docs[2], "sistema")
    return a_html("Trámite de prueba", resumen(docs, m), docs)


def test_lleva_el_titular_la_barra_y_una_tarjeta_por_documento():
    html = _pagina()
    assert html.startswith("<!doctype html>") and '<meta charset="utf-8">' in html
    assert "De 3 documentos que pedía el trámite, 2 ya no se piden." in html
    assert html.count('class="tarjeta"') == 3
    for texto in ("Se elimina", "Se conserva", "Lo genera el sistema",
                  "La identificación oficial se elimina", "Se valida con la CURP."):
        assert texto in html
    assert "Documentos que el TO-BE agrega" in html and "RFC" in html


def test_la_barra_lleva_la_cuenta_escrita_en_cada_tramo():
    html = _pagina()
    assert "<svg" in html and 'role="img"' in html
    assert "Se elimina · 1" in html and "Se conserva · 1" in html
    assert "Por revisar · 3" in _pagina(decididos=False)


def test_con_revision_a_medias_lo_dice_y_no_afirma_de_mas():
    html = _pagina(decididos=False)
    assert "Faltan 3 documentos por revisar." in html
    assert "Propuesto, sin revisar" in html


def test_no_carga_nada_de_fuera_ni_lleva_scripts():
    html = _pagina()
    assert "<script" not in html and "https://" not in html
    assert "http://" not in html.replace("http://www.w3.org/2000/svg", "")


def test_el_motivo_de_la_ia_va_rotulado():
    m = _m()
    docs = inventario_determinista(_ASIS, m)
    docs[0].motivo, docs[0].motivo_de = "Ya no hace falta.", "ia"
    html = a_html("T", resumen(docs, m), docs)
    assert "Redacción de la IA" in html


def test_dice_como_se_simplifico_el_tramite_nombrando_los_documentos():
    html = _pagina()
    assert "Cómo se simplificó el trámite" in html
    assert "Se eliminó" in html and "identificación oficial vigente" in html
    assert "Lo genera el sistema" in html and "orden de trabajo" in html
    assert "Cómo se simplificó el trámite" not in _pagina(decididos=False)


def test_un_eliminado_que_solo_nombra_el_to_be_lo_dice():
    from gpmc.comparativa.documentos import Documento, id_de
    m = _m()
    doc = Documento(id=id_de("Orden de trabajo", ""), nombre="Orden de trabajo", cita_as_is="",
                    destino="elimina", cita_to_be="Se elimina la Orden de Trabajo en papel",
                    origen="agente", estado="aceptado")
    html = a_html("T", resumen([doc], m), [doc])
    assert "El AS-IS no lo nombra; lo dice el TO-BE." in html
    assert "<blockquote></blockquote>" not in html
