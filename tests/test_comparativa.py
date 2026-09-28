# tests/test_comparativa.py
import ast
from pathlib import Path

from gpmc.comparativa.armar import (
    METRICAS, a_dict, clave_de_metrica, comparar, no_disponible)
from gpmc.extractores.as_is import EstadoActual
from gpmc.extractores.rediseno import Punto, Rediseno
from gpmc.nucleo.manifiesto import (
    Actor, Campo, Flujo, Manifiesto, Pantalla, Tarea, Tramite)


def _m(archivos=("Documento: Identificación Oficial",), tareas=2, autollena=None):
    campos = [Campo(nombre=f"doc_{i}", etiqueta=e, tipo="file")
              for i, e in enumerate(archivos)]
    campos.append(Campo(nombre="curp", etiqueta="CURP", autollena=autollena or {}))
    campos.append(Campo(nombre="vista", tipo="file",
                        etiqueta="Vista de solo lectura (Solicitud → Revisión)"))
    return Manifiesto(
        tramite=Tramite(nombre="Trámite de prueba", dependencia="Dependencia X"),
        actores=[Actor(id="ciudadano", nombre="Ciudadano"),
                 Actor(id="funcionario", nombre="Funcionario")],
        pantallas=[Pantalla(id="p1", nombre="Solicitud", actor="ciudadano", campos=campos)],
        flujo=Flujo(tareas=[
            # El manifiesto exige una tarea inicial y una terminal.
            Tarea(id=f"t{i}", nombre=f"Tarea {i}",
                  actor="ciudadano" if i == 0 else "funcionario",
                  inicial=(i == 0), terminal=(i == tareas - 1))
            for i in range(tareas)]),
    )


def _estado(**k):
    base = dict(pasos=["a", "b", "c", "d"],
                requisitos=["identificación oficial", "orden de trabajo"],
                tiempo="13 días hábiles", sistemas=["e-SIT", "Excel"])
    base.update(k)
    return EstadoActual(**base)


def _metrica(c, clave):
    return next(x for x in c.metricas if x.clave == clave)


def test_las_siete_metricas_salen_siempre_y_en_orden():
    c = comparar(_estado(), Rediseno(), _m())
    assert [x.clave for x in c.metricas] == [k for k, _ in METRICAS]
    assert c.total_metricas == 7


def test_requisitos_y_pasos_se_cuentan_y_llevan_origen():
    c = comparar(_estado(), Rediseno(), _m())
    r = _metrica(c, "requisitos")
    assert (r.antes.numero, r.antes.origen) == (2.0, "contado")
    # La fila «Vista de solo lectura» no es un documento que entregue nadie.
    assert (r.despues.numero, r.despues.origen) == (1.0, "contado")
    assert r.diferencia == 1.0 and r.porcentaje == 50.0
    p = _metrica(c, "pasos")
    assert (p.antes.numero, p.despues.numero, p.porcentaje) == (4.0, 2.0, 50.0)


def test_lo_que_no_se_leyo_es_sin_dato_y_no_cero():
    c = comparar(EstadoActual(), Rediseno(), _m())
    assert _metrica(c, "pasos").antes.origen == "sin_dato"
    assert _metrica(c, "pasos").antes.numero is None
    assert _metrica(c, "requisitos").porcentaje is None


def test_el_tiempo_se_lee_y_no_se_convierte():
    r = Rediseno(declaradas=[("Tiempo de respuesta", "", "24 horas")])
    t = _metrica(comparar(_estado(), r, _m()), "tiempo")
    assert (t.antes.texto, t.antes.origen) == ("13 días hábiles", "leido")
    assert (t.despues.texto, t.despues.origen) == ("24 horas", "declarado")
    assert t.porcentaje is None


def test_el_tiempo_entra_con_la_misma_unidad_en_los_dos_lados():
    r = Rediseno(declaradas=[("Tiempo de respuesta", "", "3 días hábiles")])
    t = _metrica(comparar(_estado(), r, _m()), "tiempo")
    assert t.porcentaje == 76.9


def test_un_valor_declarado_con_texto_no_se_compara_con_un_conteo():
    r = Rediseno(declaradas=[("Pasos operativos", "", "5 pasos rápidos")])
    p = _metrica(comparar(_estado(), r, _m()), "pasos")
    assert p.despues.origen == "declarado" and p.porcentaje is None


def test_antes_en_cero_no_divide():
    r = Rediseno(declaradas=[("Visitas presenciales", "0", "0")])
    v = _metrica(comparar(_estado(), r, _m()), "visitas")
    assert v.diferencia == 0.0 and v.porcentaje is None


def test_una_metrica_que_sube_da_porcentaje_negativo():
    c = comparar(_estado(pasos=["a"]), Rediseno(), _m(tareas=3))
    assert _metrica(c, "pasos").porcentaje == -200.0


def test_la_pantalla_gana_sobre_el_to_be_lado_por_lado():
    r = Rediseno(declaradas=[("Visitas presenciales", "2", "1")])
    c = comparar(_estado(), r, _m(), declaradas={"visitas": {"antes": "", "despues": "0"}})
    v = _metrica(c, "visitas")
    assert (v.antes.texto, v.despues.texto, v.porcentaje) == ("2", "0", 100.0)


def test_lo_declarado_corrige_una_cuenta():
    c = comparar(_estado(), Rediseno(), _m(), declaradas={"pasos": {"antes": "19", "despues": ""}})
    p = _metrica(c, "pasos")
    assert (p.antes.numero, p.antes.origen) == (19.0, "declarado")
    assert p.despues.origen == "contado"


def test_una_clave_declarada_desconocida_se_ignora():
    c = comparar(_estado(), Rediseno(), _m(), declaradas={"inventada": {"antes": "1", "despues": "0"}})
    assert len(c.metricas) == 7


def test_porcentaje_global_es_el_promedio_con_su_base():
    c = comparar(_estado(), Rediseno(), _m())
    # requisitos 50, pasos 50; actores, sistemas, tiempo, visitas y capturas sin par.
    assert (c.porcentaje_global, c.base_global) == (50.0, 2)
    assert "sobre 2 de 7 métricas" in c.frase


def test_con_menos_de_dos_comparables_no_hay_cifra_global():
    c = comparar(_estado(requisitos=[]), Rediseno(), _m())
    assert c.porcentaje_global is None and c.veredicto == "sin_medida"
    assert "No se puede medir" in c.frase


def test_los_tres_veredictos():
    assert comparar(_estado(), Rediseno(), _m()).veredicto == "reduce"
    mixto = comparar(_estado(pasos=["a"]), Rediseno(), _m(tareas=3))
    assert mixto.veredicto == "mixto"
    igual = comparar(_estado(pasos=["a", "b"], requisitos=["identificación oficial"]),
                     Rediseno(), _m())
    assert igual.veredicto == "no_reduce"
    assert any(h.codigo == "CMP-03" for h in igual.huecos)


def test_destino_de_cada_requisito():
    r = Rediseno(eliminaciones=[Punto("La orden de trabajo se elimina",
                                      "**La orden de trabajo se elimina**: la sustituye la solicitud.")])
    c = comparar(_estado(requisitos=["identificación oficial", "orden de trabajo", "acta"]),
                 r, _m(archivos=("Documento: Identificación Oficial", "Documento: RFC")))
    assert [(x.nombre, x.destino) for x in c.requisitos] == [
        ("identificación oficial", "conservado"),
        ("orden de trabajo", "eliminado"),
        ("acta", "sin_destino"),
        ("RFC", "nuevo"),
    ]
    assert "la sustituye la solicitud" in c.requisitos[1].fundamento


def test_los_cuatro_huecos_son_por_confirmar():
    c = comparar(EstadoActual(requisitos=["acta", "identificación oficial"]),
                 Rediseno(), _m())
    codigos = {h.codigo for h in c.huecos}
    assert {"CMP-01", "CMP-02", "CMP-04"} <= codigos
    assert {h.nivel for h in c.huecos} == {"por_confirmar"}
    cmp02 = [h for h in c.huecos if h.codigo == "CMP-02"]
    assert len(cmp02) == 1 and "Visitas presenciales" in cmp02[0].mensaje
    cmp04 = [h for h in c.huecos if h.codigo == "CMP-04"]
    assert len(cmp04) == 1 and "acta" in cmp04[0].mensaje


def test_actores_tareas_y_autollenados_salen_del_manifiesto():
    c = comparar(_estado(), Rediseno(), _m(autollena={"nombres": "nombre", "sexo": "sexo"}))
    assert _metrica(c, "actores").despues.numero == 2.0
    # El actor va con su nombre, no con su id tecnico: lo lee una persona.
    assert c.tareas_despues[0] == {"nombre": "Tarea 0", "actor": "Ciudadano"}
    assert c.autollenados == 2


def test_la_prosa_del_equipo_viaja_tal_cual():
    r = Rediseno(cambios=[Punto("Captura a distancia", "x")],
                 impacto=[Punto("Elimina traslados", "y")])
    c = comparar(_estado(fricciones=["Doble captura"]), r, _m())
    assert c.cambios == ["Captura a distancia"]
    assert c.impacto == ["Elimina traslados"]
    assert c.fricciones == ["Doble captura"]
    assert c.pasos_antes == ["a", "b", "c", "d"]


def test_no_disponible_y_a_dict_son_serializables():
    import json
    d = a_dict(no_disponible("No se cargó el Análisis AS-IS."))
    assert d["disponible"] is False and d["metricas"] == []
    json.dumps(a_dict(comparar(_estado(), Rediseno(), _m())))


def test_clave_de_metrica_reconoce_los_nombres_del_equipo():
    assert clave_de_metrica("Requisitos Documentales") == "requisitos"
    assert clave_de_metrica("Pasos Operativos Internos") == "pasos"
    assert clave_de_metrica("Tiempo de Respuesta (Lead Time)") == "tiempo"
    assert clave_de_metrica("Interacciones Presenciales") is None
    assert clave_de_metrica("Captura Manual de Datos") == "capturas"


def test_la_comparativa_y_los_extractores_nuevos_no_importan_capas_de_arriba():
    raiz = Path(__file__).resolve().parents[1] / "src" / "gpmc"
    prohibidos = ("gpmc.agentes", "gpmc.web", "gpmc.cli", "gpmc.compilador")
    for ruta in [raiz / "extractores" / "as_is.py", raiz / "extractores" / "rediseno.py",
                 *sorted((raiz / "comparativa").glob("*.py"))]:
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            nombres = []
            if isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""]
            elif isinstance(nodo, ast.Import):
                nombres = [a.name for a in nodo.names]
            for n in nombres:
                assert not n.startswith(prohibidos), f"{ruta.name} importa {n}"


def test_los_decimales_van_con_punto_como_se_escribe_en_mexico():
    r = Rediseno(declaradas=[("Tiempo de respuesta", "", "3 días hábiles")])
    c = comparar(_estado(requisitos=[]), r, _m())
    # pasos 50 y tiempo 76.9 -> promedio 63.45 -> 63.5 (o 63.4 por redondeo bancario)
    assert "−76.9 %" in c.frase and "," not in c.frase.split("Simplificación global:")[1]


def test_una_cifra_global_negativa_dice_que_es_aumento_neto():
    c = comparar(_estado(pasos=["a"], requisitos=["x"]), Rediseno(),
                 _m(archivos=("Documento: Uno", "Documento: Dos"), tareas=2))
    # requisitos 1 -> 2 (-100) y pasos 1 -> 2 (-100): nada baja.
    assert c.porcentaje_global == -100.0
    assert "Simplificación global: −100 % (aumento neto) sobre 2 de 7 métricas." in c.frase


# --- Hallazgos de la revision de la rama (2026-09-28) ---------------------------

def test_singular_y_plural_son_la_misma_unidad():
    # La plantilla del TO-BE enseña justo este caso: «3 días hábiles» a «1 día hábil».
    for antes, despues, pct in (("13 días hábiles", "1 día hábil", 92.3),
                                ("2 visitas", "1 visita", 50.0),
                                ("6 meses", "1 mes", 83.3)):
        c = comparar(_estado(), Rediseno(), _m(),
                     declaradas={"visitas": {"antes": antes, "despues": despues}})
        assert _metrica(c, "visitas").porcentaje == pct, (antes, despues)


def test_unidades_distintas_siguen_sin_compararse():
    c = comparar(_estado(), Rediseno(), _m(),
                 declaradas={"visitas": {"antes": "2 días", "despues": "1 hora"}})
    assert _metrica(c, "visitas").porcentaje is None


def test_cmp03_dice_que_es_con_las_cifras_leidas_y_manda_a_revisarlas():
    c = comparar(_estado(pasos=["a", "b"], requisitos=["identificación oficial"]),
                 Rediseno(), _m())
    h = [x for x in c.huecos if x.codigo == "CMP-03"][0]
    assert "Con las cifras leídas" in h.mensaje and "corrígelas" in h.mensaje
# --- Documentos del tramite (2026-09-28) ------------------------------------------

def _docs(m, decididos=True):
    from gpmc.comparativa.documentos import decidir, inventario_determinista
    docs = inventario_determinista(
        "- **Requisitos:** identificación oficial, orden de trabajo, acta\n", m)
    if decididos:
        decidir(docs[0], "conserva")
        decidir(docs[1], "elimina")
        decidir(docs[2], "consulta")
    return docs


def test_con_todo_revisado_los_requisitos_salen_de_los_documentos():
    m = _m()
    c = comparar(_estado(), Rediseno(), m, documentos=_docs(m))
    r = _metrica(c, "requisitos")
    assert (r.antes.numero, r.antes.origen) == (3.0, "revisado")
    # Despues: lo que se conserva mas lo que el TO-BE agrega.
    assert (r.despues.numero, r.despues.origen) == (1.0, "revisado")
    assert r.porcentaje == 66.7
    assert c.requisitos == []
    assert c.documentos["completo"] is True
    assert not [h for h in c.huecos if h.codigo == "CMP-04"]


def test_con_revision_a_medias_la_comparativa_sigue_como_antes():
    m = _m()
    c = comparar(_estado(), Rediseno(), m, documentos=_docs(m, decididos=False))
    assert _metrica(c, "requisitos").antes.origen == "contado"
    assert c.requisitos != []
    assert c.documentos["completo"] is False


def test_lo_declarado_a_mano_gana_sobre_lo_revisado():
    m = _m()
    c = comparar(_estado(), Rediseno(), m, documentos=_docs(m),
                 declaradas={"requisitos": {"antes": "9", "despues": ""}})
    r = _metrica(c, "requisitos")
    assert (r.antes.numero, r.antes.origen) == (9.0, "declarado")
    assert r.despues.origen == "revisado"


def test_un_eliminado_sin_frase_del_to_be_sale_como_cmp05():
    m = _m()
    c = comparar(_estado(), Rediseno(), m, documentos=_docs(m))
    cmp05 = [h for h in c.huecos if h.codigo == "CMP-05"]
    assert len(cmp05) == 1 and "orden de trabajo" in cmp05[0].mensaje


def test_sin_documentos_no_cambia_nada():
    c = comparar(_estado(), Rediseno(), _m())
    assert c.documentos is None


def test_el_despues_de_lo_revisado_son_los_archivos_que_pide_el_to_be():
    # I3 de la revision: «conserva» decidido a mano sin campo no puede contar
    # dos veces. El despues es lo que el tramite rediseñado le pide al solicitante.
    from gpmc.comparativa.documentos import decidir, inventario_determinista
    m = _m()
    docs = inventario_determinista("- **Requisitos:** credencial, cartilla\n", m)
    decidir(docs[0], "conserva")
    decidir(docs[1], "elimina")
    r = _metrica(comparar(_estado(), Rediseno(), m, documentos=docs), "requisitos")
    assert (r.antes.numero, r.despues.numero) == (2.0, 1.0)
