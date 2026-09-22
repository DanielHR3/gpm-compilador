"""Tarjetas de documentos del simulador.

Las acciones de tipo `documento` son lo unico del manifiesto que el ciudadano
se lleva a casa, y hasta ahora el simulador no las mostraba. Estas pruebas
fijan dos cosas: que se lea de donde cuelga cada documento (tarea e instante)
y que la pagina diga la verdad cuando la plantilla no sirve — en los
expedientes reales hay plantillas que son el volcado de un PDF escaneado.
"""

import json

from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.simulador.documentos import documentos_de
from gpmc.simulador.html import generar

PROSA = (
    "SOLICITUD DE REPOSICION DE CERTIFICADO\n\n"
    "Por este medio solicito a usted copia del certificado con los siguientes "
    "datos del vehiculo y del propietario, con fundamento en el programa de "
    "verificacion vehicular obligatorio vigente para el estado de Hidalgo.\n"
)

BASE = {
    "tramite": {"nombre": "Prueba", "dependencia": "DGT"},
    "actores": [{"id": "ciudadano", "nombre": "Ciudadano"}],
    "pantallas": [
        {"id": "p1", "nombre": "Solicitud", "actor": "ciudadano", "paso_ciudadano": 1,
         "campos": [{"nombre": "curp", "etiqueta": "CURP", "tipo": "text"}]},
    ],
    "flujo": {
        "tareas": [
            {"id": "t1", "nombre": "Nueva Solicitud", "actor": "ciudadano", "inicial": True,
             "pantallas": ["p1"], "acciones_despues": ["Formato de Solicitud"]},
            {"id": "t2", "nombre": "Fin", "terminal": True},
        ],
        "conexiones": [{"de": "t1", "a": "t2"}],
    },
    "acciones": [
        {"tipo": "documento", "nombre": "Formato de Solicitud", "plantilla": PROSA,
         "firmador_nombre": "Mtra. Monica", "firmador_cargo": "Secretaria"},
    ],
}


def _m(**cambios):
    return Manifiesto.model_validate({**json.loads(json.dumps(BASE)), **cambios})


def _con_acciones(acciones, tareas=None):
    d = json.loads(json.dumps(BASE))
    d["acciones"] = acciones
    if tareas is not None:
        d["flujo"]["tareas"] = tareas
    else:
        # El manifiesto rechaza una tarea que enganche una accion inexistente,
        # asi que la tarea inicial dispara justo las acciones de esta prueba.
        d["flujo"]["tareas"][0]["acciones_despues"] = [a["nombre"] for a in acciones]
    return Manifiesto.model_validate(d)


def test_solo_toma_las_acciones_de_tipo_documento():
    m = _con_acciones([
        {"tipo": "folio", "nombre": "Folio"},
        {"tipo": "costo", "nombre": "Cobro"},
        {"tipo": "documento", "nombre": "Formato de Solicitud", "plantilla": PROSA},
    ])
    assert [d["nombre"] for d in documentos_de(m)] == ["Formato de Solicitud"]


def test_dice_en_que_tarea_y_en_que_instante_se_genera():
    d = documentos_de(_m())[0]
    assert d["tarea"] == "Nueva Solicitud"
    assert d["instante"] == "despues"
    assert d["actor"] == "Ciudadano"


def test_una_plantilla_con_prosa_queda_como_legible():
    assert documentos_de(_m())[0]["estado"] == "legible"


def test_una_plantilla_volcada_de_un_pdf_escaneado_no_es_legible():
    # Caso real de «(5) Repocision de Certificado»: columnas de un PDF
    # escaneado, sin una sola frase.
    volcado = "2511014769 \n 9 \n 3 \n 174 \n HGG721D \n 2002 \n HIDALGO \n UNO"
    m = _con_acciones([{"tipo": "documento", "nombre": "Certificado", "plantilla": volcado}])
    d = documentos_de(m)[0]
    assert d["estado"] == "ilegible"
    assert d["nota"]


def test_una_plantilla_de_puras_rayas_tampoco_es_legible():
    # Caso real de «(1) Solicitud de Ampliacion y o Prorroga».
    m = _con_acciones([{"tipo": "documento", "nombre": "Solicitud", "plantilla": "_" * 28}])
    assert documentos_de(m)[0]["estado"] == "ilegible"


def test_una_accion_sin_plantilla_se_reporta_como_tal():
    m = _con_acciones([{"tipo": "documento", "nombre": "Oficio"}])
    d = documentos_de(m)[0]
    assert d["estado"] == "sin_plantilla"
    assert d["plantilla"] == ""


def test_un_documento_que_ninguna_tarea_dispara_lo_dice():
    m = _con_acciones(
        [{"tipo": "documento", "nombre": "Huerfano", "plantilla": PROSA}],
        tareas=[{"id": "t1", "nombre": "Nueva Solicitud", "actor": "ciudadano",
                 "inicial": True, "pantallas": ["p1"]},
                {"id": "t2", "nombre": "Fin", "terminal": True}],
    )
    d = documentos_de(m)[0]
    assert d["tarea"] is None
    assert d["instante"] is None


def test_conserva_el_firmante_y_la_variable_de_contenido():
    m = _con_acciones([{"tipo": "documento", "nombre": "Oficio", "plantilla": PROSA,
                        "firmador_nombre": "Mtra. Monica", "firmador_cargo": "Secretaria",
                        "variable": "oficio_contenido"}])
    d = documentos_de(m)[0]
    assert d["firmador_nombre"] == "Mtra. Monica"
    assert d["firmador_cargo"] == "Secretaria"
    assert d["variable"] == "oficio_contenido"


def test_cada_documento_trae_un_id_estable_para_el_dom():
    m = _con_acciones([{"tipo": "documento", "nombre": "A", "plantilla": PROSA},
                       {"tipo": "documento", "nombre": "A", "plantilla": PROSA}])
    ids = [d["id"] for d in documentos_de(m)]
    assert len(set(ids)) == 2


# --- la pagina ---------------------------------------------------------

def test_la_pagina_lleva_los_documentos_y_su_seccion():
    pagina = generar(_m())
    assert "const DOCUMENTOS=" in pagina
    assert "Formato de Solicitud" in pagina
    assert "vistaDocumentos" in pagina


def test_sin_documentos_la_seccion_no_se_ofrece():
    pagina = generar(_con_acciones([{"tipo": "folio", "nombre": "Folio"}]))
    assert "constDOCUMENTOS=[]" in pagina.replace(" ", "")


def test_una_plantilla_con_marcado_no_puede_romper_la_pagina():
    m = _con_acciones([{"tipo": "documento", "nombre": "Oficio",
                        "plantilla": "</script><img src=x onerror=alert(1)>"}])
    pagina = generar(m)
    assert "</script><img" not in pagina
    assert "onerror=alert(1)" not in pagina or "\\u003c" in pagina


def test_la_pagina_declara_su_codificacion():
    # Servida por FastAPI el charset viaja en la cabecera, pero la pagina se
    # guarda y se comparte como archivo suelto: sin meta, los acentos salen
    # rotos al abrirla desde el disco.
    assert generar(_m()).startswith('<meta charset="utf-8">')
