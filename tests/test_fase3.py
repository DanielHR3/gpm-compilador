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


# --- Task 2: verificacion cruzada ---------------------------------------------

_ASIS_INLINE = ("# Análisis AS-IS — Constancia\n\n"
                "- **Requisitos:** identificación oficial vigente, tarjeta de circulación, "
                "y poder notarial si el solicitante es persona moral.\n")

_ASIS_ANIDADO = ("# Análisis AS-IS — Reposición\n\n"
                 "- **Requisitos (ficha RUTS):**\n"
                 "  - Tarjeta de circulación — \"con la placa que se registró\".\n"
                 "  - Fotografía del último holograma de verificación — mismo texto.\n"
                 "- **Flujo AS-IS:**\n  1. Usuario inicia.\n")


def test_requisitos_inline_se_parten_por_coma_e_y():
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is
    assert requisitos_del_as_is(_ASIS_INLINE) == [
        "identificación oficial vigente", "tarjeta de circulación",
        "poder notarial si el solicitante es persona moral"]


def test_requisitos_anidados_se_leen_hasta_la_raya():
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is
    assert requisitos_del_as_is(_ASIS_ANIDADO) == [
        "Tarjeta de circulación", "Fotografía del último holograma de verificación"]


def test_requisitos_documentales_y_varias_lineas_se_suman():
    """La boveda de Simplificacion escribe «**Requisitos documentales:**»,
    «**Requisitos documentales**» (dos puntos fuera) y a veces dos listas
    («Requisitos propios:» y «Requisitos que dependen de otras dependencias»)."""
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is
    texto = ("- **Requisitos documentales**: CURP, acta de nacimiento\n"
             "- **Requisitos propios:**\n  - Comprobante de domicilio\n"
             "- **Requisitos que dependen de otras 5 dependencias distintas**\n"
             "  - Constancia de no adeudo — la emite Finanzas\n")
    assert requisitos_del_as_is(texto) == [
        "CURP", "acta de nacimiento", "Comprobante de domicilio", "Constancia de no adeudo"]


def test_as_is_sin_requisitos_no_produce_gen01():
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is, verificar_cruzado
    assert requisitos_del_as_is("# Análisis AS-IS — X\n\nSin lista.\n") == []
    assert verificar_cruzado("# Análisis AS-IS — X\n", "", None) == []


def _manifiesto(campos):
    from gpmc.nucleo.manifiesto import (Actor, Campo, Conexion, Flujo, Manifiesto, Pantalla,
                                        Tarea, Tramite)
    return Manifiesto(
        tramite=Tramite(nombre="X", dependencia="D"),
        actores=[Actor(id="c", nombre="Ciudadano")],
        pantallas=[Pantalla(id="p1", nombre="Solicitud", actor="c",
                            campos=[Campo(**c) for c in campos])],
        flujo=Flujo(tareas=[Tarea(id="t1", nombre="Solicitud", actor="c", inicial=True, pantallas=["p1"]),
                            Tarea(id="t_fin", nombre="Fin", terminal=True)],
                    conexiones=[Conexion(de="t1", a="t_fin")]))


def test_requisito_sin_campo_archivo_es_gen01():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    m = _manifiesto([{"nombre": "ine", "etiqueta": "Identificación oficial vigente", "tipo": "file"},
                     {"nombre": "tarjeta", "etiqueta": "Tarjeta de circulación", "tipo": "text"}])
    huecos = verificar_cruzado(_ASIS_INLINE, "", m)
    gen = [h for h in huecos if h.codigo == "GEN-01"]
    assert [h.nivel for h in gen] == ["falta_dato", "falta_dato"]
    assert "«tarjeta de circulación»" in gen[0].mensaje      # existe pero no es archivo
    assert "poder notarial" in gen[1].mensaje


def test_compuerta_con_campo_inexistente_es_mmd04_y_nodo_sin_pantalla_flu02():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    m = _manifiesto([{"nombre": "dictamen", "etiqueta": "Dictamen", "tipo": "select"}])
    tobe = ("```mermaid\nflowchart TD\n"
            "  P1[Ciudadano: Solicitud] --> G{¿@@resultado == 'ok'?}\n"
            "  G -->|Sí| P2[Funcionario: Emisión]\n```")
    huecos = verificar_cruzado("# Análisis AS-IS — X\n", tobe, m)
    assert any(h.codigo == "MMD-04" and h.ubicacion == "G" and "@@resultado" in h.mensaje for h in huecos)
    assert any(h.codigo == "FLU-02" and h.ubicacion == "P2" and "Emisión" in h.mensaje for h in huecos)
    assert not any(h.codigo == "FLU-02" and h.ubicacion == "P1" for h in huecos)


# --- Task 3: generar ------------------------------------------------------------

_DICC_OK = ("# Diccionario de Datos — Constancia\n\n"
            "### Pantalla 1 — Ciudadano — Solicitud\n\n"
            "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
            "| CURP | Texto | Input | Si | La CURP `@@curp` |\n"
            "| Identificación oficial vigente | Archivo | Visor de archivos | Si | `@@ine` |\n"
            "| Tarjeta de circulación | Archivo | Visor de archivos | Si | `@@tarjeta` |\n"
            "| Poder notarial si el solicitante es persona moral | Archivo | Visor de archivos | No | `@@poder` |\n\n"
            "### Pantalla 2 — Funcionario — Revisión\n\n"
            "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
            "| Dictamen | Lista (Aprobado, Rechazado) | Select | Si | `@@dictamen` |\n")

_TOBE_OK = ("# Propuesta TO-BE — Constancia\n\n```mermaid\nflowchart TD\n"
            "    classDef ciudadano fill:#eee\n    classDef funcionario fill:#ddd\n"
            "    Inicio([Inicio]):::ciudadano --> P1[Ciudadano: Solicitud]:::ciudadano\n"
            "    P1 --> P2[Funcionario: Revisión]:::funcionario\n"
            "    P2 --> Fin([Fin]):::funcionario\n```\n")


def _json(clave, texto):
    return json.dumps({clave: texto})


def test_generar_una_ronda_devuelve_listo_con_dos_textos_y_huecos(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    from gpmc.agentes.bitacora import leer
    prov = ProveedorFalso([_json("diccionario", _DICC_OK), _json("tobe", _TOBE_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "a" * 16, mejorar=False)
    assert g.estado == "listo" and g.motivo is None
    assert g.nombre == "Constancia"
    assert g.diccionario.texto == _DICC_OK and g.diccionario.ronda == 1
    assert g.tobe.texto == _TOBE_OK and g.tobe.version_prompt == "tobe-v1"
    assert g.diccionario.decision == "pendiente"
    # Los huecos del extractor van repartidos por documento.
    assert all(h.codigo.startswith(("DIC", "META", "GEN", "API", "DOC", "INS-03"))
               for h in g.diccionario.huecos)
    assert prov.llamadas == 2
    assert "<<DICCIONARIO>>" in prov.ultimo_contexto       # el TO-BE vio el Diccionario
    filas = leer(tmp_path)
    assert [(f["documento"], f["ronda"]) for f in filas] == [("diccionario", 1), ("tobe", 1)]
    assert filas[0]["version_prompt"] == "dicc-v1"


def test_texto_vacio_o_sin_mermaid_es_listo_con_huecos_no_error(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_OK), _json("tobe", "# Propuesta TO-BE — X\n\nsin diagrama")])
    g = generar(_ASIS_INLINE, prov, tmp_path, "b" * 16, mejorar=False)
    assert g.estado == "listo"
    assert any(h.codigo == "MMD-01" for h in g.tobe.huecos)


def test_respuesta_invalida_no_se_reintenta_y_deja_error(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    from gpmc.agentes.bitacora import leer
    prov = ProveedorFalso(["esto no es json", _json("diccionario", _DICC_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "c" * 16)
    assert g.estado == "error" and "RespuestaInvalida" in g.motivo
    assert prov.llamadas == 1
    assert leer(tmp_path)[0]["estado"] == "error"


def test_error_de_red_se_reintenta_tres_veces(tmp_path, monkeypatch):
    from gpmc.agentes import fase3
    from gpmc.agentes.proveedor import ProveedorFalso
    monkeypatch.setattr(fase3.time, "sleep", lambda s: None)
    prov = ProveedorFalso([])                          # guion agotado = ErrorDeRed
    g = fase3.generar(_ASIS_INLINE, prov, tmp_path, "d" * 16)
    assert g.estado == "error" and "ErrorDeRed" in g.motivo
    assert prov.llamadas == 3


def test_nombres_de_insumo_coinciden_con_la_web():
    from gpmc.agentes.fase3 import NOMBRES_INSUMO
    from gpmc.web.sesiones import INSUMOS
    assert NOMBRES_INSUMO == {"as_is": INSUMOS["as_is"], "tobe": INSUMOS["to_be"],
                              "diccionario": INSUMOS["diccionario"]}
