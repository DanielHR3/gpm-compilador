import json

import pytest

from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.simulador.analisis import analizar
from gpmc.simulador.html import generar

BASE = {
    "tramite": {"nombre": "Prueba", "dependencia": "DGT"},
    "actores": [{"id": "ciudadano", "nombre": "Ciudadano"},
                {"id": "func", "nombre": "Funcionario", "tipo": "grupo",
                 "grupos_usuarios": ["Area"]}],
    "pantallas": [
        {"id": "p1", "nombre": "Solicitud", "actor": "ciudadano", "paso_ciudadano": 1,
         "campos": [{"nombre": "curp", "etiqueta": "CURP", "tipo": "text", "obligatorio": True}]},
        {"id": "p2", "nombre": "Revisión", "actor": "func",
         "campos": [{"nombre": "ok", "etiqueta": "¿Correcto?", "tipo": "radio",
                     "catalogo": [{"etiqueta": "Sí", "valor": "si"},
                                  {"etiqueta": "No", "valor": "no"}]}]},
    ],
    "flujo": {
        "tareas": [
            {"id": "t1", "nombre": "Capturar", "actor": "ciudadano", "inicial": True, "pantallas": ["p1"]},
            {"id": "t2", "nombre": "Revisar", "actor": "func", "pantallas": ["p2"]},
            {"id": "t3", "nombre": "Fin", "terminal": True},
        ],
        "conexiones": [
            {"de": "t1", "a": "t2"},
            {"de": "t2", "a": "t3", "cuando": {"campo": "ok", "igual": "si"}},
            {"de": "t2", "a": "t1", "cuando": {"campo": "ok", "igual": "no"}},
        ],
    },
    "acciones": [],
}


def _m(**cambios):
    return Manifiesto.model_validate({**BASE, **cambios})


def test_un_flujo_sano_no_reporta_problemas():
    assert analizar(_m()).problemas == []


def test_detecta_tarea_inalcanzable():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["tareas"].append({"id": "t9", "nombre": "Huerfana", "actor": "func"})
    p = analizar(Manifiesto.model_validate(d)).problemas
    assert any("t9" in x and "alcanz" in x.lower() for x in p), p


def test_detecta_condicion_sobre_valor_fuera_del_catalogo():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["conexiones"][1]["cuando"]["igual"] = "quiza"
    p = analizar(Manifiesto.model_validate(d)).problemas
    assert any("quiza" in x for x in p), p


def test_detecta_campo_usado_antes_de_capturarse():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["conexiones"][0] = {"de": "t1", "a": "t2",
                                   "cuando": {"campo": "ok", "igual": "si"}}
    p = analizar(Manifiesto.model_validate(d)).problemas
    assert any("antes" in x.lower() or "captur" in x.lower() for x in p), p


def test_precalcula_la_tabla_de_transiciones_con_el_evaluador_compartido():
    a = analizar(_m())
    t2 = a.transiciones["t2"]
    assert t2["campo"] == "ok"
    assert t2["destinos"]["si"] == "t3"
    assert t2["destinos"]["no"] == "t1"


def test_el_html_es_autocontenido_y_no_evalua_reglas_en_javascript():
    html = generar(_m())
    assert "<!" not in html[:20], "el artefacto es un fragmento, no un documento con doctype propio"
    assert "http://" not in html and "https://" not in html, "debe ser autocontenido"
    assert "@@" not in html, "el JS no debe recibir sintaxis de reglas de GPM"
    assert "TRANSICIONES" in html, "el JS consulta una tabla precalculada por Python"


def test_el_html_incluye_las_pantallas_los_campos_y_el_stepper():
    html = generar(_m())
    assert "CURP" in html
    assert "¿Correcto?" in html
    assert "Solicitud" in html
    assert "Paso 1" in html or "paso_ciudadano" in html


def test_el_html_marca_los_problemas_detectados():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["tareas"].append({"id": "t9", "nombre": "Huerfana", "actor": "func"})
    html = generar(Manifiesto.model_validate(d))
    assert "t9" in html


def test_el_html_se_declara_como_simulacion():
    html = generar(_m())
    assert "simulaci" in html.lower()


def test_usa_la_paleta_institucional_real():
    """Muestreada de las capturas de la plataforma de modelado."""
    html = generar(_m())
    assert "#5e132c" in html or "#66132a" in html


def test_el_aviso_de_simulacion_sigue_siendo_prominente():
    """Al parecerse a la plataforma real, el aviso importa mas, no menos."""
    html = generar(_m())
    i = html.lower().index("simulaci")
    assert i < len(html) * 0.5, "el aviso debe ir arriba, no al pie"
    assert "no es" in html.lower() or "no la plataforma" in html.lower()
