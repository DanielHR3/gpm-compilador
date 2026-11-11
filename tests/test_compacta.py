"""Fase 3 compacta (spec 2026-11-11): el modelo decide en JSON corto y el
Compilador escribe el Diccionario y la Propuesta TO-BE."""
import json

from gpmc.agentes import compacta as cp
from gpmc.agentes.fase3 import extraer_borradores
from gpmc.nucleo.huecos import bloquean

CAT = {"version": 1, "campos": {
    "curp": {"etiqueta": "CURP", "tipo": "Texto", "tramites": 16, "celdas": {
        "Nombre del Campo": "CURP", "Tipo de Dato": "Texto", "Componente Sugerido": "Campo de texto",
        "Obligatorio": "Sí", "Límite / Especificaciones": "18 caracteres", "Descripción": "CURP del solicitante."}},
    "observaciones": {"etiqueta": "Observaciones", "tipo": "Texto", "tramites": 8, "celdas": {
        "Nombre del Campo": "Observaciones", "Tipo de Dato": "Texto", "Componente Sugerido": "Área de texto",
        "Obligatorio": "No", "Límite / Especificaciones": "500 caracteres", "Descripción": "Qué debe corregir."}},
}}
ASIS = ("# Análisis AS-IS — Constancia de Prueba\n\n"
        "- **Requisitos:** identificación oficial vigente, comprobante de domicilio\n\n"
        "Si hay observaciones el ciudadano debe solventar y volver a entregar.\n")
RESPUESTA = {
    "pantallas": [
        {"actor": "Ciudadano", "nombre": "Solicitud", "campos": ["@@curp", "#1", "#2", "Motivo de la solicitud|Área de texto|Sí|300 caracteres||Para qué la pide"]},
        {"actor": "Funcionario", "nombre": "Revisión", "campos": ["Dictamen|Lista desplegable|Sí||Aprobado · Rechazado|Resultado de la revisión", "@@observaciones"]},
        {"actor": "Ciudadano", "nombre": "Corrección", "campos": ["Respuesta a las observaciones|Área de texto|Sí|500 caracteres||"]},
        {"actor": "Funcionario", "nombre": "Emisión", "campos": ["Constancia emitida|Archivo|Sí|||La constancia firmada"]},
    ],
    "flujo": ["1>2", "2>4?Dictamen=Aprobado", "2>3?Dictamen=Rechazado", "3>2"],
    "problema": "El trámite pide dos visitas.",
    "eliminaciones": ["Copia de la CURP|Sí|Se consulta en línea"],
    "impacto": ["Una visita menos"], "riesgos": [], "pendientes": [],
}


def _armar(resp=RESPUESTA):
    return cp.armar(cp.leer(json.dumps(resp)), CAT, ASIS, "Constancia de Prueba")


def test_de_la_respuesta_corta_salen_los_dos_documentos_y_el_extractor_los_lee():
    a = _armar()
    m, huecos = extraer_borradores(ASIS, a.diccionario, a.tobe)
    assert m is not None and [p.nombre for p in m.pantallas] == ["Solicitud", "Revisión", "Corrección", "Emisión"]
    campos = {c.nombre: c for p in m.pantallas for c in p.campos}
    assert campos["curp"].longitud_exacta == 18                      # la fila del catálogo
    assert campos["dictamen"].tipo == "select" and len(campos["dictamen"].catalogo) == 2
    assert campos["motivo_de_la_solicitud"].tipo == "textarea"
    assert not [h for h in huecos if h.nivel == "bloqueante"]


def test_los_requisitos_citados_por_numero_son_campos_archivo_y_no_hay_gen01():
    a = _armar()
    m, huecos = extraer_borradores(ASIS, a.diccionario, a.tobe)
    archivos = [c.etiqueta for p in m.pantallas for c in p.campos if c.tipo == "file"]
    assert any("identificación oficial" in e.lower() for e in archivos)
    assert any("comprobante de domicilio" in e.lower() for e in archivos)
    assert "GEN-01" not in {h.codigo for h in huecos}


def test_el_flujo_sale_ramificado_con_su_ciclo_de_correccion():
    a = _armar()
    assert "```mermaid" in a.tobe and "@@dictamen" in a.tobe
    m, huecos = extraer_borradores(ASIS, a.diccionario, a.tobe)
    codigos = {h.codigo for h in huecos}
    assert "FLU-03" in codigos                                      # ramificó solo
    assert not codigos & {"FLU-01", "FLU-02", "GEN-02", "GEN-03", "MMD-04"}
    assert sum(1 for c in m.flujo.conexiones if c.cuando is not None) == 2


def test_sin_flujo_las_pantallas_van_en_fila():
    a = _armar({**RESPUESTA, "flujo": []})
    m, _ = extraer_borradores(ASIS, a.diccionario, a.tobe)
    assert m is not None and len(m.flujo.conexiones) >= 3


def test_un_id_que_no_esta_en_el_catalogo_no_se_pierde_y_se_avisa():
    resp = {**RESPUESTA, "pantallas": [{"actor": "Ciudadano", "nombre": "Solicitud",
                                        "campos": ["@@curp", "@@numero_inventado", "#9"]}], "flujo": []}
    a = _armar(resp)
    assert "numero_inventado" in a.diccionario                      # queda como campo de texto
    assert any("numero_inventado" in x for x in a.avisos) and any("#9" in x for x in a.avisos)
    assert "numero_inventado" in a.tobe                             # y en Pendientes del expediente


def test_el_tobe_trae_las_secciones_del_equipo():
    t = _armar().tobe
    for s in ("## Problema", "## Análisis de eliminación", "### Diagrama compilable", "## Impacto estimado",
              "## Riesgos / dependencias", "## Pendientes del expediente"):
        assert s in t
    assert "| Copia de la CURP | Sí | Se consulta en línea |" in t


def test_una_respuesta_que_no_cumple_el_esquema_es_invalida():
    import pytest
    from gpmc.agentes.proveedor import RespuestaInvalida
    for malo in ("no es json", "{}", json.dumps({"pantallas": [], "flujo": []}),
                 json.dumps({"pantallas": [{"actor": "x", "nombre": "y", "campos": "curp"}]})):
        with pytest.raises(RespuestaInvalida):
            cp.leer(malo)


def test_el_contexto_lleva_catalogo_recortado_requisitos_numerados_y_as_is_sin_plantillas():
    ctx = cp.contexto(ASIS, CAT)
    assert "<<CATALOGO>>" in ctx and "@@curp" in ctx
    assert "#1 identificación oficial vigente" in ctx and "#2 comprobante de domicilio" in ctx
    assert "<<DATOS>>" in ctx and "<<PLANTILLA>>" not in ctx and "<<EJEMPLO>>" not in ctx
    assert len(cp.INSTRUCCION) < 6000                                # ~1,400 tokens con el ejemplo; antes ~3,400 en dos llamadas, más plantilla y ejemplo


# --- Generación: una llamada, caché por huella del AS-IS y mejora corta ------------

import pytest


@pytest.fixture(autouse=True)
def _sin_esperas(monkeypatch):
    from gpmc.agentes import fase3
    monkeypatch.setattr(fase3, "ESPERAS_REINTENTO", (0.0, 0.0))


def _gen(tmp_path, respuestas, sid="a" * 16, as_is=ASIS, **kw):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([json.dumps(r) if isinstance(r, dict) else r for r in respuestas])
    return generar(as_is, prov, tmp_path, sid, modo="compacta", catalogo=CAT, **kw), prov


def test_generar_compacta_es_una_sola_llamada_y_deja_los_dos_documentos(tmp_path):
    from gpmc.agentes.bitacora import leer
    g, prov = _gen(tmp_path, [RESPUESTA])
    assert g.estado == "listo" and prov.llamadas == 1
    assert g.diccionario.version_prompt == "compacta-v2" == g.tobe.version_prompt
    assert "### Pantalla 1 — CIUDADANO — Solicitud" in g.diccionario.texto and "```mermaid" in g.tobe.texto
    assert len(g.diccionario.vista) == 4 and g.compacta
    assert "<<PLANTILLA>>" not in prov.ultimo_contexto and "<<CATALOGO>>" in prov.ultimo_contexto
    assert [(f["documento"], f["version_prompt"]) for f in leer(tmp_path)] == [("compacta", "compacta-v2")]


def test_el_mismo_as_is_no_vuelve_a_llamar(tmp_path):
    g1, _ = _gen(tmp_path, [RESPUESTA])
    g2, prov = _gen(tmp_path, [], sid="b" * 16)
    assert prov.llamadas == 0 and g2.estado == "listo"
    assert g2.diccionario.texto == g1.diccionario.texto
    assert any("sin consumo" in p.lower() for p in g2.pasos)
    _, prov3 = _gen(tmp_path, [RESPUESTA], sid="c" * 16, as_is=ASIS + "\nOtro párrafo.\n")
    assert prov3.llamadas == 1                                       # otro AS-IS sí llama


def test_una_respuesta_invalida_no_se_guarda_en_la_cache(tmp_path):
    g, _ = _gen(tmp_path, ["no es json"])
    assert g.estado == "error" and "RespuestaInvalida" in g.motivo
    _, prov = _gen(tmp_path, [RESPUESTA], sid="d" * 16)
    assert prov.llamadas == 1


# Sin ciclo de corrección: el AS-IS habla de solventar y el flujo va en fila (GEN-02).
_MALA = {**RESPUESTA, "flujo": ["1>2", "2>3", "3>4"]}


def test_la_mejora_compacta_no_reenvia_el_as_is_y_se_queda_si_cierra_huecos(tmp_path):
    from gpmc.agentes.fase3 import mejorar
    from gpmc.agentes.proveedor import ProveedorFalso
    g, _ = _gen(tmp_path, [_MALA])
    assert any(h.codigo == "GEN-02" for h in g.tobe.huecos)
    prov = ProveedorFalso([json.dumps(RESPUESTA)])
    g2 = mejorar(ASIS, g.model_dump(mode="json"), prov, tmp_path, "a" * 16, catalogo=CAT)
    assert prov.llamadas == 1 and g2.estado == "listo"
    assert "<<ANTERIOR>>" in prov.ultimo_contexto and "<<HUECOS>>" in prov.ultimo_contexto
    assert "<<DATOS>>" not in prov.ultimo_contexto
    assert g2.tobe.ronda == 2 and g2.tobe.version_prompt == "compacta-mejora-v1"
    assert not any(h.codigo == "GEN-02" for h in g2.tobe.huecos)


def test_una_mejora_compacta_que_empeora_o_falla_conserva_la_primera(tmp_path):
    from gpmc.agentes.fase3 import mejorar
    from gpmc.agentes.proveedor import ProveedorFalso
    g, _ = _gen(tmp_path, [_MALA])
    recortada = {**RESPUESTA, "pantallas": RESPUESTA["pantallas"][:1], "flujo": []}
    for guion in ([json.dumps(recortada)], ["no es json"]):
        g2 = mejorar(ASIS, g.model_dump(mode="json"), ProveedorFalso(guion), tmp_path, "a" * 16, catalogo=CAT)
        assert g2.estado == "listo" and g2.tobe.ronda == 1 and g2.tobe.texto == g.tobe.texto


def test_la_mejora_compacta_no_gasta_en_lo_que_el_modelo_no_puede_cerrar(tmp_path):
    """Con el diseño bueno solo quedan META-* (datos que faltan en el AS-IS)."""
    from gpmc.agentes.fase3 import mejorar
    from gpmc.agentes.proveedor import ProveedorFalso
    g, _ = _gen(tmp_path, [RESPUESTA])
    prov = ProveedorFalso([])
    g2 = mejorar(ASIS, g.model_dump(mode="json"), prov, tmp_path, "a" * 16, catalogo=CAT)
    assert prov.llamadas == 0 and g2.estado == "listo" and g2.tobe.ronda == 1


# --- Reparaciones sin IA (medición real del 2026-11-11 con norte70) ------------------
# El modelo dejó pantallas vacías, ramas con campos que no existían y texto de
# la instrucción copiado tal cual. Arreglarlo aquí no cuesta tokens.

def _codigos(a):
    m, huecos = extraer_borradores(ASIS, a.diccionario, a.tobe)
    return m, {h.codigo for h in huecos}


def test_una_pantalla_vacia_conserva_su_lugar_en_el_flujo():
    resp = {**RESPUESTA, "pantallas": [
        RESPUESTA["pantallas"][0], {"actor": "Funcionario", "nombre": "Búsqueda del certificado", "campos": []},
        RESPUESTA["pantallas"][3]], "flujo": ["1>2", "2>3"]}
    a = _armar(resp)
    m, _ = _codigos(a)
    assert [p.nombre for p in m.pantallas] == ["Solicitud", "Búsqueda del certificado", "Emisión"]
    assert any("Búsqueda del certificado" in x and "sin campos" in x for x in a.avisos)


def test_una_rama_con_un_campo_que_no_existe_lo_crea_en_la_pantalla_de_origen():
    resp = {**RESPUESTA, "pantallas": [
        RESPUESTA["pantallas"][0], {"actor": "Funcionario", "nombre": "Revisión", "campos": ["@@observaciones"]},
        RESPUESTA["pantallas"][2], RESPUESTA["pantallas"][3]],
        "flujo": ["1>2", "2>4?Documentación completa=Sí", "2>3?Documentación completa=No", "3>2"]}
    a = _armar(resp)
    m, codigos = _codigos(a)
    campos = {c.nombre: c for c in m.pantallas[1].campos}
    assert "documentacion_completa" in campos
    assert not codigos & {"MMD-04", "FLU-01", "GEN-03"} and "FLU-03" in codigos
    assert any("Documentación completa" in x for x in a.avisos)


def test_una_sola_rama_y_un_paso_directo_son_las_dos_salidas_de_la_decision():
    resp = {**RESPUESTA, "flujo": ["1>2", "2>3?Dictamen=Rechazado", "2>4", "3>2"]}
    m, codigos = _codigos(_armar(resp))
    assert "FLU-03" in codigos and not codigos & {"FLU-01", "GEN-03"}
    assert sum(1 for c in m.flujo.conexiones if c.cuando is not None) == 2


def test_el_texto_de_la_instruccion_copiado_no_llega_al_diccionario():
    resp = {**RESPUESTA, "pantallas": [{"actor": "Funcionario", "nombre": "Revisión", "campos": [
        "¿Documentación completa?|Booleano|Sí|No|Valores|Descripción", "Folio|Texto|Sí o No|Límite||"]}], "flujo": []}
    d = _armar(resp).diccionario
    assert "Valores" not in d.split("| --- |")[-1] and "Descripción `@@" not in d and "| Límite |" not in d


def test_un_campo_repetido_en_otra_pantalla_no_se_declara_dos_veces():
    resp = {**RESPUESTA, "pantallas": [
        RESPUESTA["pantallas"][0],
        {"actor": "Funcionario", "nombre": "Revisión", "campos": ["@@curp", "@@observaciones"]},
        {"actor": "Funcionario", "nombre": "Emisión", "campos": ["@@observaciones", "@@curp"]}], "flujo": ["1>2", "2>3"]}
    a = _armar(resp)
    m, codigos = _codigos(a)
    assert "DIC-09" not in codigos and len(m.pantallas) == 3
    assert a.diccionario.count("`@@curp`") == 1 and a.diccionario.count("`@@observaciones`") == 1


# Segunda medición real (compacta-v2): el modelo escribió «2>3?Campo|No» y usó
# en una rama un valor que no había puesto en la lista de su propio campo.

def test_la_rama_se_lee_tambien_con_barra_o_dos_puntos():
    for sep in ("|", ":", " = "):
        resp = {**RESPUESTA, "flujo": ["1>2", f"2>4?Dictamen{sep}Aprobado", f"2>3?Dictamen{sep}Rechazado", "3>2"]}
        _, codigos = _codigos(_armar(resp))
        assert "FLU-03" in codigos and not codigos & {"FLU-01", "GEN-03"}, sep


def test_un_valor_de_rama_que_falta_en_la_lista_del_campo_propio_se_agrega():
    resp = {**RESPUESTA, "flujo": ["1>2", "2>4?Dictamen=Aprobado", "2>3?Dictamen=Rechazado",
                                   "2>4?Dictamen=Improcedente", "3>2"]}
    a = _armar(resp)
    m, codigos = _codigos(a)
    dictamen = next(c for p in m.pantallas for c in p.campos if c.nombre == "dictamen")
    assert len(dictamen.catalogo) == 3 and not codigos & {"FLU-01", "GEN-03"}
    assert any("Improcedente" in x for x in a.avisos)
