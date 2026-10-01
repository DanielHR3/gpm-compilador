# tests/test_comparativa_propuestas.py
"""Como entra a la comparativa lo que propone el agente, ya verificado."""
import json

from gpmc.comparativa.armar import a_dict, comparar, lados_sin_dato
from gpmc.comparativa.propuestas import (
    Evidencia, Mejora, Propuesta, conservar_descartes, id_de_mejora, mejoras_a_dicts,
    mejoras_desde, propuestas_a_dicts, propuestas_desde)
from gpmc.extractores.rediseno import Elemento, Rediseno
from tests.test_comparativa import _estado, _m, _metrica


def _visitas(lado="antes", n=3, **k):
    return Propuesta("visitas", lado,
                     [Evidencia(f"Visita {i}", f"acude a la ventanilla {i}") for i in range(n)],
                     **k)


def test_una_propuesta_llena_un_lado_vacio_y_dice_que_es_propuesta():
    c = comparar(_estado(), Rediseno(), _m(), propuestas=[_visitas(motivo="Va tres veces.")])
    v = _metrica(c, "visitas")
    assert (v.antes.texto, v.antes.numero, v.antes.origen) == ("3", 3.0, "propuesto")
    assert v.propuesta_antes["motivo"] == "Va tres veces."
    assert [e["cita"] for e in v.propuesta_antes["evidencia"]] == [
        "acude a la ventanilla 0", "acude a la ventanilla 1", "acude a la ventanilla 2"]
    assert v.despues.origen == "sin_dato" and v.propuesta_despues is None


def test_la_cifra_es_cuantas_evidencias_hay_y_ninguno_es_cero():
    ninguna = Propuesta("visitas", "despues", [Evidencia("Ninguna", "no queda ninguna visita")],
                        ninguno=True)
    v = _metrica(comparar(_estado(), Rediseno(), _m(), propuestas=[_visitas(n=4), ninguna]),
                 "visitas")
    assert (v.antes.numero, v.despues.numero, v.porcentaje) == (4.0, 0.0, 100.0)
    assert v.propuesta_despues["ninguno"] is True


def test_el_tiempo_propuesto_es_el_plazo_tal_como_esta_escrito():
    p = Propuesta("tiempo", "despues", [Evidencia("3 días hábiles", "se resuelve en 3 días hábiles")],
                  texto="3 días hábiles")
    t = _metrica(comparar(_estado(), Rediseno(), _m(), propuestas=[p]), "tiempo")
    assert (t.despues.texto, t.despues.origen, t.porcentaje) == ("3 días hábiles", "propuesto", 76.9)


def test_una_propuesta_no_pisa_lo_contado_ni_lo_leido():
    p = Propuesta("pasos", "antes", [Evidencia("Paso", "un paso")])
    c = comparar(_estado(), Rediseno(), _m(), propuestas=[p])
    assert _metrica(c, "pasos").antes.origen == "contado"
    assert _metrica(c, "pasos").propuesta_antes is None


def test_lo_declarado_por_una_persona_gana_a_la_propuesta():
    c = comparar(_estado(), Rediseno(), _m(), declaradas={"visitas": {"antes": "5", "despues": ""}},
                 propuestas=[_visitas()])
    v = _metrica(c, "visitas")
    assert (v.antes.texto, v.antes.origen) == ("5", "declarado") and v.propuesta_antes is None


def test_una_propuesta_sin_evidencia_no_entra():
    c = comparar(_estado(), Rediseno(), _m(), propuestas=[Propuesta("visitas", "antes", [])])
    assert _metrica(c, "visitas").antes.origen == "sin_dato"


def test_la_frase_y_un_aviso_dicen_que_cifras_propuso_el_agente():
    ninguna = Propuesta("visitas", "despues", [Evidencia("Ninguna", "no queda ninguna visita")],
                        ninguno=True)
    c = comparar(_estado(), Rediseno(), _m(), propuestas=[_visitas(), ninguna])
    assert c.base_global == 3
    assert "1 de esas 3 usa cifras propuestas por el agente" in c.frase
    cmp06 = [h for h in c.huecos if h.codigo == "CMP-06"]
    assert len(cmp06) == 1 and cmp06[0].nivel == "por_confirmar"
    assert "Visitas presenciales (antes y después)" in cmp06[0].mensaje
    # CMP-02 ya no nombra lo que el agente lleno.
    cmp02 = next(h for h in c.huecos if h.codigo == "CMP-02")
    assert "Visitas presenciales" not in cmp02.mensaje and "Sistemas externos" in cmp02.mensaje


def test_sin_propuestas_nada_cambia():
    c = comparar(_estado(), Rediseno(), _m())
    assert "propuestas por el agente" not in c.frase
    assert not [h for h in c.huecos if h.codigo == "CMP-06"]


def test_lados_sin_dato_es_lo_que_se_le_pide_al_agente():
    c = comparar(_estado(pasos=[]), Rediseno(), _m())
    assert lados_sin_dato(c) == [
        ("pasos", "antes"), ("actores", "antes"), ("sistemas", "despues"),
        ("tiempo", "despues"), ("visitas", "antes"), ("visitas", "despues"),
        ("capturas", "antes"), ("capturas", "despues")]


def test_los_elementos_de_la_tabla_de_eliminacion_se_cuentan_por_clase():
    r = Rediseno(elementos=[
        Elemento("Acta", "Sí", "Se consulta.", "elimina", "requisito"),
        Elemento("Paso 1", "Sí", "", "elimina", "paso"),
        Elemento("INE", "No, se conserva", "", "conserva", "requisito"),
        Elemento("Paso 2", "Se reduce", "", "cambia", "paso"),
        Elemento("Paso 3", "Depende", "", "otro", "paso")])
    c = comparar(_estado(), r, _m())
    assert c.resumen_elementos == {"total": 5, "elimina": 2, "conserva": 1, "cambia": 1,
                                   "sin_decision": 0, "otro": 1}
    assert c.elementos[0] == {"nombre": "Acta", "decision": "Sí", "fundamento": "Se consulta.",
                              "clase": "elimina", "tipo": "requisito"}
    assert comparar(_estado(), Rediseno(), _m()).resumen_elementos is None


def test_el_resumen_dice_en_palabras_que_bajo_que_subio_y_que_falta():
    r = Rediseno(elementos=[Elemento("Acta", "Sí", "", "elimina"),
                            Elemento("INE", "No", "", "conserva")])
    c = comparar(_estado(pasos=["a"]), r, _m(tareas=3), propuestas=[_visitas(n=2)])
    por_clase = {x["clase"]: x["texto"] for x in c.resumen}
    assert por_clase["elementos"] == ("De los 2 elementos del trámite actual que revisó el "
                                      "equipo, 1 se elimina y 1 se conserva.")
    assert por_clase["baja"] == "Baja: requisitos documentales, de 2 a 1."
    assert por_clase["sube"] == "Sube: pasos del proceso, de 1 a 3."
    assert por_clase["sin_dato"].startswith("Sin dato en el expediente: ")
    assert "capturas manuales del mismo dato" in por_clase["sin_dato"]
    assert "visitas presenciales (después)" in por_clase["sin_dato"]


def test_lo_que_queda_igual_tambien_se_dice():
    c = comparar(_estado(pasos=["a", "b"], requisitos=["identificación oficial"]),
                 Rediseno(), _m())
    por_clase = {x["clase"]: x["texto"] for x in c.resumen}
    assert por_clase["igual"] == ("Queda igual: requisitos documentales (1); "
                                  "pasos del proceso (2).")


def test_los_puntos_de_mejora_viajan_y_los_descartados_no_cuentan():
    m1 = Mejora("a1", "Quitar la tarjeta", "documento", "Consultarla.", "Ahorra un escaneo.")
    m2 = Mejora("b2", "Unir dos revisiones", "paso", "Una pantalla.", "Menos espera.",
                descartada=True)
    c = comparar(_estado(), Rediseno(), _m(), mejoras=[m1, m2])
    assert [(x["id"], x["descartada"]) for x in c.mejoras] == [("a1", False), ("b2", True)]
    json.dumps(a_dict(c))


def test_propuestas_y_mejoras_van_y_vienen_de_json():
    p = [_visitas(motivo="x"), Propuesta("tiempo", "despues", [Evidencia("1 día", "en 1 día")],
                                         texto="1 día")]
    assert propuestas_desde(json.loads(json.dumps(propuestas_a_dicts(p)))) == p
    m = [Mejora("a1", "T", "paso", "P", "B", cita="frase", fuente="to_be", campo="doc_x",
                etiqueta_campo="Doc X", servicio="consultacurpn", requiere="servicio_publico")]
    assert mejoras_desde(json.loads(json.dumps(mejoras_a_dicts(m)))) == m
    # Un archivo viejo o roto no revienta la pantalla.
    assert propuestas_desde(None) == [] and propuestas_desde([{"metrica": "x"}, 3]) == []
    assert mejoras_desde("no es lista") == []


def test_un_descarte_sobrevive_a_volver_a_analizar():
    previa = Mejora(id_de_mejora("documento", "doc_tarjeta", "", "Quitar la tarjeta"),
                    "Quitar la tarjeta", "documento", "P", "B", campo="doc_tarjeta",
                    descartada=True)
    # El modelo redacta distinto el titulo: se reencuentra por el campo.
    nueva = Mejora(id_de_mejora("documento", "doc_tarjeta", "", "Eliminar tarjeta de circulación"),
                   "Eliminar tarjeta de circulación", "documento", "P2", "B2", campo="doc_tarjeta")
    otra = Mejora(id_de_mejora("paso", "", "revisión manual del pago", "Automatizar"),
                  "Automatizar", "paso", "P", "B", cita="revisión manual del pago", fuente="to_be")
    salida = conservar_descartes([nueva, otra], [previa])
    assert [(x.titulo, x.descartada) for x in salida] == [
        ("Eliminar tarjeta de circulación", True), ("Automatizar", False)]
