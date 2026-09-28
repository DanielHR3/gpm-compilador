# tests/test_documentos.py
import pytest

from gpmc.comparativa.documentos import (
    DESTINOS, Documento, a_dicts, agregados, avisos, conservar_decisiones, decidir,
    desde_dicts, id_de, inventario_determinista, reconciliar, referencias, resumen)
from gpmc.nucleo.manifiesto import (
    Accion, Actor, Campo, Flujo, Manifiesto, Pantalla, Tarea, Tramite)

_ASIS = ("# Análisis AS-IS — Trámite de prueba\n\n"
         "- **Requisitos:** identificación oficial vigente, comprobante de domicilio, "
         "orden de trabajo\n")


def _m(extra_ciudadano=(), con_accion=False):
    ciudadano = [
        Campo(nombre="curp", etiqueta="CURP", autollena={"nombres": "nombre"}),
        Campo(nombre="doc_comprobante", etiqueta="Documento: Comprobante de domicilio", tipo="file"),
        Campo(nombre="vista", tipo="file", etiqueta="Vista de solo lectura (A → B)"),
        *[Campo(nombre=n, etiqueta=e, tipo="file") for n, e in extra_ciudadano],
    ]
    funcionario = [Campo(nombre="doc_constancia", etiqueta="Constancia firmada", tipo="file")]
    return Manifiesto(
        tramite=Tramite(nombre="Trámite de prueba", dependencia="X"),
        actores=[Actor(id="ciudadano", nombre="Ciudadano", tipo="autoservicio"),
                 Actor(id="funcionario", nombre="Funcionario", tipo="grupo")],
        pantallas=[Pantalla(id="p1", nombre="Solicitud", actor="ciudadano", campos=ciudadano),
                   Pantalla(id="p2", nombre="Emisión", actor="funcionario", campos=funcionario)],
        flujo=Flujo(tareas=[Tarea(id="t1", nombre="Única", inicial=True, terminal=True)]),
        acciones=[Accion(tipo="documento", nombre="oficio", titulo="Oficio de respuesta")]
        if con_accion else [],
    )


def test_referencias_clasifica_lo_que_puede_respaldar_un_destino():
    clases = {r.nombre: r.clase for r in referencias(_m(con_accion=True))}
    assert clases == {
        "curp": "consulta",
        "doc_comprobante": "archivo_ciudadano",
        "doc_constancia": "archivo_otro",
        "oficio": "accion_documento",
    }
    ref = next(r for r in referencias(_m()) if r.nombre == "doc_comprobante")
    assert (ref.etiqueta, ref.pantalla, ref.actor) == ("Comprobante de domicilio", "Solicitud", "Ciudadano")


def test_el_inventario_determinista_conserva_lo_que_casa_y_deja_lo_demas_sin_destino():
    docs = inventario_determinista(_ASIS, _m())
    assert [(d.nombre, d.destino, d.campo) for d in docs] == [
        ("identificación oficial vigente", "sin_destino", ""),
        ("comprobante de domicilio", "conserva", "doc_comprobante"),
        ("orden de trabajo", "sin_destino", ""),
    ]
    assert {d.origen for d in docs} == {"lector"}
    assert {d.estado for d in docs} == {"propuesto"}
    assert len({d.id for d in docs}) == 3


def test_un_archivo_del_funcionario_no_cuenta_como_conservado():
    docs = inventario_determinista("- **Requisitos:** constancia firmada\n", _m())
    assert docs[0].destino == "sin_destino"


def test_el_id_es_estable_y_no_depende_de_acentos_ni_mayusculas():
    assert id_de("Identificación Oficial", "INE vigente") == id_de("identificacion oficial", "ine  vigente")
    assert id_de("a", "b") != id_de("a", "c")


def test_decidir_acepta_o_corrige():
    docs = inventario_determinista(_ASIS, _m())
    aceptado = decidir(docs[1], "conserva")
    assert (aceptado.estado, aceptado.destino) == ("aceptado", "conserva")
    corregido = decidir(docs[0], "elimina", "Se valida con la CURP.")
    assert (corregido.estado, corregido.destino) == ("corregido", "elimina")
    assert (corregido.motivo, corregido.motivo_de) == ("Se valida con la CURP.", "persona")
    assert corregido.veredicto == ""


def test_decidir_rechaza_un_destino_que_no_existe_y_sin_destino():
    doc = inventario_determinista(_ASIS, _m())[0]
    for malo in ("sin_destino", "borrar", ""):
        with pytest.raises(ValueError):
            decidir(doc, malo)
    assert set(DESTINOS) == {"elimina", "conserva", "consulta", "sistema"}


def test_el_titular_cuenta_solo_lo_decidido():
    docs = inventario_determinista(_ASIS, _m())
    r = resumen(docs, _m())
    assert (r["total"], r["decididos"], r["completo"]) == (3, 0, False)
    assert r["titular"] == "Faltan 3 documentos por revisar."
    decidir(docs[0], "elimina")
    decidir(docs[1], "conserva")
    r = resumen(docs, _m())
    assert r["titular"] == "De 2 documentos revisados, 1 ya no se pide. Falta 1 por revisar."
    decidir(docs[2], "sistema")
    r = resumen(docs, _m())
    assert r["completo"] is True and r["ya_no_se_piden"] == 2
    assert r["titular"] == "De 3 documentos que pedía el trámite, 2 ya no se piden."
    assert r["por_destino"] == {"elimina": 1, "conserva": 1, "consulta": 0,
                                "sistema": 1, "sin_destino": 0}
    assert r["solicitados"] == 1


def test_sin_documentos_el_titular_lo_dice():
    r = resumen([], _m())
    assert r["completo"] is False
    assert r["titular"] == "El AS-IS no trae documentos que se puedan leer."


def test_agregados_son_los_archivos_del_ciudadano_que_nadie_ocupa():
    m = _m(extra_ciudadano=(("doc_rfc", "Documento: RFC"),))
    docs = inventario_determinista(_ASIS, m)
    assert agregados(docs, m) == ["RFC"]
    assert resumen(docs, m)["agregados"] == ["RFC"]


def test_reconciliar_devuelve_a_sin_destino_lo_que_apunta_a_un_campo_que_ya_no_existe():
    docs = inventario_determinista(_ASIS, _m())
    decidir(docs[1], "conserva")
    decidir(docs[0], "elimina")
    docs[1].campo = "campo_que_ya_no_esta"
    fuera = reconciliar(docs, _m())
    assert (fuera[1].destino, fuera[1].estado, fuera[1].veredicto) == (
        "sin_destino", "propuesto", "campo_desaparecido")
    # Venia «sin destino»: elegirle uno es corregir la propuesta, no aceptarla.
    assert (fuera[0].destino, fuera[0].estado) == ("elimina", "corregido")


def test_volver_a_analizar_no_pisa_lo_que_decidio_la_persona():
    previos = inventario_determinista(_ASIS, _m())
    decidir(previos[0], "elimina", "Se valida con la CURP.")
    nuevos = inventario_determinista(_ASIS, _m())
    nuevos[0].destino = "consulta"
    nuevos[2].destino = "sistema"
    fuera = conservar_decisiones(nuevos, previos)
    assert (fuera[0].destino, fuera[0].estado, fuera[0].motivo_de) == ("elimina", "corregido", "persona")
    assert (fuera[2].destino, fuera[2].estado) == ("sistema", "propuesto")


def test_cmp05_por_cada_eliminado_decidido_sin_frase_del_to_be():
    docs = inventario_determinista(_ASIS, _m())
    decidir(docs[0], "elimina")
    decidir(docs[2], "elimina")
    docs[2].cita_to_be = "La orden de trabajo se elimina"
    h = avisos(docs)
    assert [(x.codigo, x.nivel) for x in h] == [("CMP-05", "por_confirmar")]
    assert "identificación oficial vigente" in h[0].mensaje
    # Propuesto y no decidido: todavia no es una afirmacion de nadie.
    assert avisos(inventario_determinista(_ASIS, _m())) == []


def test_ida_y_vuelta_a_json():
    docs = inventario_determinista(_ASIS, _m())
    decidir(docs[0], "elimina", "motivo")
    filas = a_dicts(docs)
    assert desde_dicts(filas) == docs
    # Una clave de mas o una fila rota no tumban la lectura de la sesion.
    assert desde_dicts([{**filas[0], "sobra": 1}, "roto", {"nombre": "sin id"}]) == [docs[0]]
    assert desde_dicts(None) == []


def test_como_se_simplifico_nombra_los_documentos_de_cada_destino_decidido():
    docs = inventario_determinista(_ASIS, _m())
    assert resumen(docs, _m())["simplificacion"] == []
    decidir(docs[0], "elimina")
    decidir(docs[2], "elimina")
    decidir(docs[1], "conserva")
    assert resumen(docs, _m())["simplificacion"] == [
        {"destino": "elimina", "frase": "Se eliminaron",
         "documentos": ["identificación oficial vigente", "orden de trabajo"]},
        {"destino": "conserva", "frase": "Se conserva",
         "documentos": ["comprobante de domicilio"]},
    ]


def test_lo_propuesto_y_sin_revisar_no_se_afirma_en_la_simplificacion():
    docs = inventario_determinista(_ASIS, _m())
    # El comprobante sale «conserva» del lector, pero nadie lo ha aceptado.
    assert docs[1].destino == "conserva"
    assert resumen(docs, _m())["simplificacion"] == []


def test_quien_inicia_el_tramite_es_solicitante_aunque_sea_una_dependencia():
    # Periodico Oficial (prueba en vivo, 2026-09-28): quien pide la publicacion
    # es una dependencia, actor de tipo «grupo». Sus archivos son lo que el
    # tramite le pide, no algo que «genera el sistema».
    m = Manifiesto(
        tramite=Tramite(nombre="Publicación", dependencia="X"),
        actores=[Actor(id="dependencia", nombre="Dependencia", tipo="grupo"),
                 Actor(id="periodico", nombre="Periódico Oficial", tipo="grupo")],
        pantallas=[
            Pantalla(id="p1", nombre="Nueva Solicitud", actor="dependencia", campos=[
                Campo(nombre="doc_oficio", etiqueta="Oficio de solicitud", tipo="file")]),
            Pantalla(id="p2", nombre="Cotización", actor="periodico", campos=[
                Campo(nombre="doc_f7", etiqueta="Formato F7", tipo="file")]),
        ],
        flujo=Flujo(tareas=[
            Tarea(id="t1", nombre="Nueva Solicitud", actor="dependencia", inicial=True),
            Tarea(id="t2", nombre="Cotización", actor="periodico", terminal=True)]),
    )
    assert {r.nombre: r.clase for r in referencias(m)} == {
        "doc_oficio": "archivo_ciudadano", "doc_f7": "archivo_otro"}
    docs = inventario_determinista("- **Requisitos:** oficio de solicitud\n", m)
    assert (docs[0].destino, docs[0].campo) == ("conserva", "doc_oficio")


# --- Hallazgos de la revision de la rama (2026-09-28) ---------------------------

def test_la_barra_solo_cuenta_lo_decidido_lo_demas_esta_por_revisar():
    # I5: recien analizado, «conserva» es una propuesta, no un hecho.
    docs = inventario_determinista(_ASIS, _m())
    assert resumen(docs, _m())["por_destino"] == {
        "elimina": 0, "conserva": 0, "consulta": 0, "sistema": 0, "sin_destino": 3}


def test_volver_a_analizar_conserva_lo_decidido_aunque_cambie_el_nombre_o_no_venga():
    # C1: el id sale del nombre y la cita, que el modelo redacta.
    previos = inventario_determinista(_ASIS, _m())
    decidir(previos[0], "consulta", "Se valida con la CURP.")
    decidir(previos[2], "elimina")
    nuevos = [
        Documento(id=id_de("INE o pasaporte", "identificación oficial vigente"),
                  nombre="INE o pasaporte", cita_as_is="identificación oficial vigente",
                  destino="elimina", origen="agente"),
        Documento(id=id_de("Comprobante", "comprobante de domicilio"), nombre="Comprobante",
                  cita_as_is="comprobante de domicilio", destino="conserva",
                  campo="doc_comprobante", origen="agente"),
    ]
    fuera = conservar_decisiones(nuevos, previos)
    assert [(d.nombre, d.destino, d.estado) for d in fuera] == [
        ("identificación oficial vigente", "consulta", "corregido"),
        ("Comprobante", "conserva", "propuesto"),
        # No vino en el analisis nuevo y la persona ya lo habia decidido: se queda.
        ("orden de trabajo", "elimina", "corregido"),
    ]


def test_cambiar_el_destino_no_hereda_la_evidencia_de_la_propuesta():
    # I4: el campo y la frase respaldaban otro destino.
    doc = Documento(id="x", nombre="Comprobante de domicilio", cita_as_is="comprobante",
                    destino="conserva", campo="doc_comprobante",
                    cita_to_be="El comprobante se adjunta en la solicitud", origen="agente")
    decidir(doc, "elimina")
    assert (doc.destino, doc.campo, doc.cita_to_be) == ("elimina", "", "")
    assert [h.codigo for h in avisos([doc])] == ["CMP-05"]


def test_aceptar_sin_cambiar_conserva_la_evidencia():
    doc = Documento(id="x", nombre="Orden", cita_as_is="orden", destino="elimina",
                    cita_to_be="La orden de trabajo se elimina", origen="agente")
    decidir(doc, "elimina")
    assert doc.cita_to_be == "La orden de trabajo se elimina" and avisos([doc]) == []


def test_decidir_conserva_a_mano_busca_su_campo_entre_los_libres():
    # I3: sin campo, el archivo del TO-BE se contaba como conservado y como agregado.
    m = _m()
    docs = inventario_determinista("- **Requisitos:** recibo de domicilio, comprobante de domicilio\n", m)
    assert [d.destino for d in docs] == ["sin_destino", "conserva"]
    otro = Documento(id="y", nombre="Comprobante de domicilio", cita_as_is="comprobante")
    decidir(otro, "conserva", refs=referencias(m), docs=[])
    assert otro.campo == "doc_comprobante"
    assert agregados([otro], m) == []
