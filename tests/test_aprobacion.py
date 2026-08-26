import json
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.compilador.aprobacion import generar_aprobacion

BASE = {
    "tramite": {"nombre": "Prueba", "dependencia": "DGT", "homoclave": "DGT-01"},
    "actores": [{"id": "c", "nombre": "Ciudadano"}],
    "pantallas": [
        {"id": "p1", "nombre": "Solicitud", "actor": "c", "campos": [
            {"nombre": "campo1", "etiqueta": "Campo 1", "tipo": "text", "obligatorio": True}
        ]}
    ],
    "flujo": {
        "tareas": [{"id": "t1", "nombre": "Capturar", "actor": "c", "inicial": True, "terminal": True, "pantallas": ["p1"]}],
        "conexiones": []
    }
}

def _m():
    return Manifiesto.model_validate(BASE)

def test_aprobacion_genera_html_con_marcas_esperadas():
    html = generar_aprobacion(_m())
    assert "DGT-01" in html
    assert "Prueba" in html
    assert "Campo 1" in html
    assert "BORRADOR" in html
    assert "@media print" in html

def test_aprobacion_muestra_dependencia_en_pie_de_firma():
    html = generar_aprobacion(_m())
    assert "DGT" in html
