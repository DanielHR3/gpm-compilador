# tests/test_prompt_fase3_v3.py
"""Prompts v3 de la Fase 3 (2026-10-16): menos tokens, dos comprobaciones mas.

Diagnostico en la bitacora de IA: ~53,000 tokens por corrida, con el ejemplo
de escala (~3,500) viajando entero en las cuatro llamadas y las dos rondas de
mejora reenviando plantilla y ejemplo que el borrador ya trae. GEN-01 y GEN-02
se repetian en Reposicion."""
from gpmc.agentes import prompt_fase3 as p


def test_las_versiones_suben_a_v3():
    assert (p.VERSION_PROMPT_DICC, p.VERSION_PROMPT_TOBE, p.VERSION_PROMPT_MEJORA) == (
        "dicc-v3", "tobe-v3", "mejora-v3")


def test_el_ejemplo_viaja_partido_por_documento():
    dicc = p.ejemplo("diccionario")
    tobe = p.ejemplo("tobe")
    # El Diccionario ve la escala en pantallas; el TO-BE, en el diagrama.
    assert "### Pantalla 8" in dicc and "```mermaid" not in dicc
    assert "```mermaid" in tobe and "¿@@modalidad_pago?" in tobe and "### Pantalla 1" not in tobe
    # Los dos ven la tabla de eliminacion: es la escala del analisis.
    assert "Análisis de eliminación" in dicc and "Análisis de eliminación" in tobe
    # Y entre los dos no se pierde nada del ejemplo entero.
    assert len(dicc) + len(tobe) < len(p.ejemplo()) * 1.6


def test_cada_contexto_lleva_solo_su_mitad_del_ejemplo():
    ctx_d = p.contexto_dicc("as-is")
    ctx_t = p.contexto_tobe("as-is", "# Diccionario de Datos — X")
    assert "### Pantalla 8" in ctx_d and "¿@@modalidad_pago?" not in ctx_d
    assert "¿@@modalidad_pago?" in ctx_t and "### Pantalla 8" not in ctx_t


def test_la_ronda_de_mejora_no_reenvia_plantilla_ni_ejemplo():
    for ctx in (p.contexto_mejora("as-is", "borrador", ["[GEN-01] x"], "diccionario"),
                p.contexto_mejora("as-is", "borrador", ["[FLU-02] x"], "tobe", diccionario="d")):
        assert "<<PLANTILLA>>" not in ctx and "<<EJEMPLO>>" not in ctx
        assert "<<BORRADOR>>" in ctx and "<<HUECOS>>" in ctx and "<<DATOS>>" in ctx
    # Y la instruccion ya no describe bloques que no viajan.
    assert "<<PLANTILLA>>" not in p.INSTRUCCION_MEJORA and "<<EJEMPLO>>" not in p.INSTRUCCION_MEJORA
    assert "Corregir no es recortar" in p.INSTRUCCION_MEJORA


def test_el_diccionario_cierra_con_la_comprobacion_de_requisitos():
    # GEN-01 dos veces en Reposicion: «Fotografia del ultimo holograma» sin fila Archivo.
    assert "Antes de responder" in p.INSTRUCCION_DICC
    assert "<<REQUISITOS>> línea por línea" in p.INSTRUCCION_DICC


def test_el_tobe_cierra_con_la_comprobacion_del_ciclo_de_correccion():
    # GEN-02 dos veces en Reposicion: el AS-IS habla de solventar y nada vuelve a la revision.
    assert "Antes de responder" in p.INSTRUCCION_TOBE
    assert "solventar" in p.INSTRUCCION_TOBE and "Requiere corrección" in p.INSTRUCCION_TOBE


def test_el_presupuesto_de_cada_contexto_no_crece_sin_que_alguien_lo_vea():
    # En caracteres, medido el 2026-10-16 tras partir el ejemplo; +10 % de holgura.
    # Subir un tope exige una medida nueva en la bitacora de IA.
    assert len(p.contexto_dicc("")) <= p.PRESUPUESTO["diccionario"]
    assert len(p.contexto_tobe("", "")) <= p.PRESUPUESTO["tobe"]
    assert len(p.contexto_mejora("", "", [], "diccionario")) <= p.PRESUPUESTO["mejora"]
    assert len(p.INSTRUCCION_DICC) + len(p.INSTRUCCION_TOBE) + len(p.INSTRUCCION_MEJORA) <= p.PRESUPUESTO["instrucciones"]
