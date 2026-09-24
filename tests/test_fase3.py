"""Fase 3: TO-BE y Diccionario propuestos desde el AS-IS.

Ninguna prueba toca la red: todo pasa por ProveedorFalso.
"""
import json
from pathlib import Path

import pytest


def test_candado_solo_abre_con_openai_y_llave():
    from gpmc.agentes.fase3 import puede_generar
    assert puede_generar({"GPMC_IA_PROVEEDOR": "openai", "GPMC_IA_LLAVE": "k"}) is None
    motivo = puede_generar({"GPMC_IA_PROVEEDOR": "gemini", "GPMC_IA_LLAVE": "k"})
    assert motivo and "licencia" in motivo
    assert puede_generar({"GPMC_IA_PROVEEDOR": "openai"})       # sin llave
    assert puede_generar({})


def test_prompts_versionados_y_bloques_delimitados():
    from gpmc.agentes import prompt_fase3 as p
    assert p.VERSION_PROMPT_DICC == "dicc-v1"
    assert p.VERSION_PROMPT_TOBE == "tobe-v1"
    assert p.VERSION_PROMPT_MEJORA == "mejora-v1"
    ctx = p.contexto_dicc("# Analisis AS-IS — X\n\n**Requisitos:** CURP")
    assert "<<PLANTILLA>>" in ctx and "<</PLANTILLA>>" in ctx
    assert "<<DATOS>>" in ctx and "<</DATOS>>" in ctx
    assert "### Pantalla 1" in ctx                # la plantilla del Diccionario viaja como formato
    ctx2 = p.contexto_tobe("as-is", "# Diccionario de Datos — X")
    assert "<<DICCIONARIO>>" in ctx2 and "```mermaid" in ctx2
    ctx3 = p.contexto_mejora("as-is", "borrador", ["[DIC-00] no se extrajo ninguna pantalla"], "diccionario")
    assert "<<BORRADOR>>" in ctx3 and "<<HUECOS>>" in ctx3 and "[DIC-00]" in ctx3


def test_prompt_tobe_pide_la_forma_actor_dos_puntos_pantalla():
    """La prueba del 2026-09-23 perdio las compuertas porque los nodos salian
    como «ACTOR — Pantalla». La regla va en el prompt."""
    from gpmc.agentes.prompt_fase3 import INSTRUCCION_TOBE, esquema_de
    assert "Actor: Pantalla" in INSTRUCCION_TOBE
    assert "@@campo" in INSTRUCCION_TOBE
    assert esquema_de("tobe") == {"type": "object", "properties": {"tobe": {"type": "string"}},
                                  "required": ["tobe"]}


def test_los_prompts_citan_las_reglas_y_la_estructura_de_simplificacion():
    """Las 12 reglas de compatibilidad (CLAUDE.md de la boveda, 2026-09-18) y
    las secciones de sus documentos van en los dos prompts: el borrador debe
    salir en la forma que ellos editan, no en una que tengan que traducir."""
    from gpmc.agentes import prompt_fase3 as p
    assert p.FECHA_REGLAS_COMPATIBILIDAD == "2026-09-18"
    for regla in ("30 caracteres", " · ", '"Etiqueta" = Valor', "Siempre visible",
                  "Diagrama compilable", "Solo lectura"):
        assert regla in p.REGLAS_COMPATIBILIDAD, regla
    assert p.REGLAS_COMPATIBILIDAD in p.INSTRUCCION_DICC
    assert p.REGLAS_COMPATIBILIDAD in p.INSTRUCCION_TOBE
    for seccion in ("## Ficha técnica", "## Sección 1 — Pantallas", "## 2. Textos y Avisos",
                    "## 5. Leyenda", "## Pendientes"):
        assert seccion in p.ESTRUCTURA_DICC, seccion
    for seccion in ("## Problema", "## Análisis de eliminación por requisito y por paso",
                    "### Diagrama compilable", "### Diagrama completo del flujo",
                    "## Riesgos / dependencias", "## Pendientes del expediente"):
        assert seccion in p.ESTRUCTURA_TOBE, seccion
    assert p.ESTRUCTURA_DICC in p.INSTRUCCION_DICC and p.ESTRUCTURA_TOBE in p.INSTRUCCION_TOBE
