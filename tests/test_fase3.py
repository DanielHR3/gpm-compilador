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
    assert p.VERSION_PROMPT_DICC == "dicc-v2"
    assert p.VERSION_PROMPT_TOBE == "tobe-v2"
    assert p.VERSION_PROMPT_MEJORA == "mejora-v2"
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
    assert g.tobe.texto == _TOBE_OK and g.tobe.version_prompt == "tobe-v2"
    assert g.diccionario.decision == "pendiente"
    # Los huecos del extractor van repartidos por documento.
    assert all(h.codigo.startswith(("DIC", "META", "GEN", "API", "DOC", "INS-03"))
               for h in g.diccionario.huecos)
    assert prov.llamadas == 2
    assert "<<DICCIONARIO>>" in prov.ultimo_contexto       # el TO-BE vio el Diccionario
    filas = leer(tmp_path)
    assert [(f["documento"], f["ronda"]) for f in filas] == [("diccionario", 1), ("tobe", 1)]
    assert filas[0]["version_prompt"] == "dicc-v2"


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


# --- Task 4: ronda de mejora ----------------------------------------------------

_DICC_ROTO = "# Diccionario de Datos — Constancia\n\nSin tablas ni pantallas.\n"   # -> DIC-00 bloqueante


def test_mejora_conserva_la_ronda_2_cuando_tiene_menos_bloqueantes(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    from gpmc.agentes.bitacora import leer
    prov = ProveedorFalso([_json("diccionario", _DICC_ROTO), _json("tobe", _TOBE_OK),
                           _json("diccionario", _DICC_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "e" * 16)
    assert g.estado == "listo"
    assert g.diccionario.ronda == 2 and g.diccionario.texto == _DICC_OK
    assert g.diccionario.version_prompt == "mejora-v2"
    assert not any(h.codigo == "DIC-00" for h in g.diccionario.huecos)
    # El TO-BE no tenia bloqueantes propios: no se le pidio mejora.
    assert g.tobe.ronda == 1
    assert prov.llamadas == 3
    assert "<<HUECOS>>" in prov.ultimo_contexto and "[DIC-00]" in prov.ultimo_contexto
    assert [(f["documento"], f["ronda"]) for f in leer(tmp_path)] == [
        ("diccionario", 1), ("tobe", 1), ("diccionario", 2)]


def test_mejora_conserva_la_ronda_1_cuando_la_2_empeora(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    # Ronda 1: un solo GEN-01 (falta «poder notarial»). Ronda 2: el modelo
    # rompe el Diccionario entero (DIC-00). Se queda la 1.
    dicc_1 = _DICC_OK.replace("| Poder notarial si el solicitante es persona moral | Archivo | Visor de archivos | No | `@@poder` |\n", "")
    prov = ProveedorFalso([_json("diccionario", dicc_1), _json("tobe", _TOBE_OK),
                           _json("diccionario", _DICC_ROTO)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "f" * 16)
    assert g.diccionario.ronda == 1 and g.diccionario.texto == dicc_1
    assert any(h.codigo == "GEN-01" for h in g.diccionario.huecos)


def test_mejora_se_pide_una_sola_vez_por_documento_y_el_tobe_ve_el_diccionario_elegido(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    # Ronda 1: Diccionario con un GEN-01 (falta «poder notarial») y TO-BE sin
    # diagrama (MMD-01). Con un Diccionario roto el extractor corta antes de
    # mirar el TO-BE y no habria nada suyo que mejorar.
    dicc_1 = _DICC_OK.replace("| Poder notarial si el solicitante es persona moral | Archivo | Visor de archivos | No | `@@poder` |\n", "")
    tobe_roto = "# Propuesta TO-BE — Constancia\n\nsin diagrama\n"       # MMD-01 falta_dato
    prov = ProveedorFalso([_json("diccionario", dicc_1), _json("tobe", tobe_roto),
                           _json("diccionario", _DICC_OK), _json("tobe", _TOBE_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "0" * 16)
    assert prov.llamadas == 4
    assert g.diccionario.ronda == 2 and g.tobe.ronda == 2
    assert _DICC_OK in prov.ultimo_contexto          # la mejora del TO-BE vio el Diccionario de la ronda 2


def test_fallo_en_la_mejora_no_tira_la_ronda_1(tmp_path, monkeypatch):
    """La ronda 1 ya costo dos llamadas; si la mejora falla por red, se entrega
    la ronda 1 con sus huecos, no `error`."""
    from gpmc.agentes import fase3
    from gpmc.agentes.proveedor import ProveedorFalso
    monkeypatch.setattr(fase3.time, "sleep", lambda s: None)
    prov = ProveedorFalso([_json("diccionario", _DICC_ROTO), _json("tobe", _TOBE_OK)])
    g = fase3.generar(_ASIS_INLINE, prov, tmp_path, "1" * 16)
    assert g.estado == "listo" and g.diccionario.ronda == 1
    assert any(h.codigo == "DIC-00" for h in g.diccionario.huecos)


# --- Task 11: medir-ia --fase3 -------------------------------------------------------

def _expediente_humano(tmp_path):
    """Imita la boveda de Simplificacion: profundidad analista/dependencia/tramite,
    un tramite sin TO-BE y otro con dos Diccionarios (INS-02): los dos se omiten."""
    d = tmp_path / "ANITA" / "Notarías" / "constancia"
    d.mkdir(parents=True)
    (d / "Análisis AS-IS.md").write_text(_ASIS_INLINE, encoding="utf-8")
    (d / "Propuesta TO-BE.md").write_text(_TOBE_OK, encoding="utf-8")
    (d / "Diccionario de Datos.md").write_text(_DICC_OK, encoding="utf-8")
    s = tmp_path / "ELESVAN" / "SEMARNATH" / "sin-tobe"
    s.mkdir(parents=True)
    (s / "Análisis AS-IS.md").write_text(_ASIS_INLINE, encoding="utf-8")
    c = tmp_path / "ANITA" / "Notarías" / "con-copia"
    c.mkdir(parents=True)
    for n in ("Análisis AS-IS.md", "Propuesta TO-BE.md", "Diccionario de Datos.md",
              "Diccionario de Datos - copia.md"):
        (c / n).write_text(_DICC_OK if "Dicc" in n else _ASIS_INLINE, encoding="utf-8")
    return d


def test_medir_fase3_compara_generado_con_humano_por_clave(tmp_path):
    from gpmc.agentes.medir_fase3 import medir_carpeta, imprimir
    from gpmc.agentes.proveedor import ProveedorFalso
    _expediente_humano(tmp_path)
    # El generado pierde «poder notarial» y el TO-BE es identico.
    dicc_gen = _DICC_OK.replace("| Poder notarial si el solicitante es persona moral | Archivo | Visor de archivos | No | `@@poder` |\n", "")
    prov = ProveedorFalso([_json("diccionario", dicc_gen), _json("tobe", _TOBE_OK),
                           _json("diccionario", dicc_gen)])           # la mejora devuelve lo mismo
    medidas = medir_carpeta(tmp_path, prov, tmp_path / "almacen")
    assert [m.expediente for m in medidas] == ["constancia"]         # «sin-tobe» y «con-copia» se omiten
    m = medidas[0]
    assert m.estado == "listo"
    assert (m.campos_humano, m.campos_casan) == (5, 4)
    assert (m.requisitos_humano, m.requisitos_casan) == (3, 2)
    assert (m.tareas_humano, m.tareas_casan) == (2, 2)
    assert m.compuertas_con_regla == 0
    assert m.huecos.get("falta_dato", 0) >= 1                        # el GEN-01 de poder notarial
    salida = imprimir(medidas)
    assert "constancia" in salida and "4/5" in salida and "2/3" in salida


def test_la_plantilla_tobe_que_viaja_al_prompt_es_mermaid_dibujable():
    """Mermaid no acepta `G{¿@@campo == 'x'?}` sin comillas (Parse error:
    got 'LINK_ID'); visto al dibujar el ejemplo en la pantalla de Propuestas el
    2026-09-24. La plantilla va al prompt como ejemplo de forma: si trae la
    sintaxis rota, el modelo la copia y ningun TO-BE generado se puede dibujar.
    Es tambien la regla 10 de Simplificacion: `G{"¿@@campo?"}`."""
    import re
    from gpmc.agentes.prompt_fase3 import plantilla
    bloque = re.search(r"```mermaid(.*?)```", plantilla("tobe"), re.S).group(1)
    compuertas = re.findall(r"\{[^{}]*@@[^{}]*\}", bloque)
    assert compuertas, "la plantilla debe traer al menos una compuerta con @@"
    assert all(c.startswith('{"') and c.endswith('"}') for c in compuertas), compuertas


# --- Revision final: requisitos (hallazgo 3) y bitacora (hallazgo 5) -----------------

def test_requisitos_con_comas_dentro_de_parentesis_y_y_dentro_de_un_requisito():
    """«Identificación oficial (INE, pasaporte o cartilla), CURP» son DOS
    requisitos, y «pago de derechos y aprovechamientos» es UNO: la «y» solo
    separa en el ultimo tramo de una enumeracion «a, b y c»."""
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is
    assert requisitos_del_as_is(
        "- **Requisitos:** Identificación oficial (INE, pasaporte o cartilla), CURP\n") == [
        "Identificación oficial", "CURP"]
    assert requisitos_del_as_is(
        "- **Requisitos:** Comprobante de pago de derechos y aprovechamientos\n") == [
        "Comprobante de pago de derechos y aprovechamientos"]
    assert requisitos_del_as_is("- **Requisitos:** CURP, acta y comprobante\n") == [
        "CURP", "acta", "comprobante"]


def test_requisitos_anidados_solo_el_primer_nivel():
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is
    texto = ("- **Requisitos:**\n"
             "  - Identificación oficial\n"
             "    - vigente\n"
             "    - con fotografía\n"
             "  - CURP\n")
    assert requisitos_del_as_is(texto) == ["Identificación oficial", "CURP"]


def test_una_respuesta_invalida_del_propio_proveedor_queda_en_la_bitacora(tmp_path):
    """El proveedor de OpenAI lanza RespuestaInvalida el mismo (JSON truncado
    por el tope de tokens): esa llamada se cobra y debe quedar registrada."""
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso, RespuestaInvalida
    from gpmc.agentes.bitacora import leer

    class Truncado(ProveedorFalso):
        def completar(self, instrucciones, contexto, esquema):
            self.llamadas += 1
            raise RespuestaInvalida("no es JSON")

    g = generar(_ASIS_INLINE, Truncado([]), tmp_path, "2" * 16)
    assert g.estado == "error"
    filas = leer(tmp_path)
    assert len(filas) == 1 and filas[0]["estado"] == "error"
    assert "respuesta_invalida" in filas[0]["alertas"] and filas[0]["documento"] == "diccionario"


def test_cada_intento_reintentado_deja_su_linea(tmp_path, monkeypatch):
    """Dos timeouts y un exito son tres peticiones cobradas: tres lineas."""
    from gpmc.agentes import fase3
    from gpmc.agentes.proveedor import ErrorDeRed, ProveedorFalso
    from gpmc.agentes.bitacora import leer
    monkeypatch.setattr(fase3, "ESPERAS_REINTENTO", (0.0, 0.0))

    class Intermitente(ProveedorFalso):
        def completar(self, instrucciones, contexto, esquema):
            if self.llamadas < 2:
                self.llamadas += 1
                raise ErrorDeRed("timeout")
            return super().completar(instrucciones, contexto, esquema)

    prov = Intermitente([_json("diccionario", _DICC_OK), _json("tobe", _TOBE_OK)])
    g = fase3.generar(_ASIS_INLINE, prov, tmp_path, "3" * 16, mejorar=False)
    assert g.estado == "listo"
    filas = [f for f in leer(tmp_path) if f["documento"] == "diccionario"]
    assert [f["estado"] for f in filas] == ["error", "error", "procesada"]


# --- Dos caminos, Task 2: vista del Diccionario -----------------------------------------

def test_el_diccionario_generado_lleva_su_vista_por_pantallas(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_OK), _json("tobe", _TOBE_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "4" * 16, mejorar=False)
    v = g.diccionario.vista
    assert [(p["nombre"], p["actor"]) for p in v] == [("Solicitud", "Ciudadano"), ("Revisión", "Funcionario")]
    curp = v[0]["campos"][0]
    assert curp == {"etiqueta": "CURP", "tipo": "text", "obligatorio": True, "opciones": [], "condicion": None}
    # _DICC_OK no trae columna de catalogo: las opciones se prueban abajo,
    # con un manifiesto que si las tiene.
    assert v[1]["campos"][0]["tipo"] == "select"
    assert g.tobe.vista == []


def test_la_vista_escribe_la_condicion_en_palabras():
    from gpmc.agentes.fase3 import vista_de
    from gpmc.nucleo.manifiesto import Condicion
    m = _manifiesto([
        {"nombre": "tipo", "etiqueta": "Tipo de persona", "tipo": "select",
         "catalogo": [{"etiqueta": "Moral", "valor": "moral"}]},
        {"nombre": "poder", "etiqueta": "Poder notarial", "tipo": "file",
         "condicion_visible": Condicion(campo="tipo", igual="moral")}])
    campos = vista_de(m)[0]["campos"]
    assert campos[1]["condicion"] == "«Tipo de persona» es «Moral»"
    assert campos[0]["opciones"] == ["Moral"]
    assert vista_de(None) == []


def test_sin_pantallas_la_vista_es_vacia_y_generar_no_falla(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_ROTO), _json("tobe", _TOBE_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "5" * 16, mejorar=False)
    assert g.estado == "listo" and g.diccionario.vista == []


def test_la_vista_es_la_de_la_ronda_elegida(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_ROTO), _json("tobe", _TOBE_OK),
                           _json("diccionario", _DICC_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "6" * 16)
    assert g.diccionario.ronda == 2 and len(g.diccionario.vista) == 2


# --- Pendientes menores (2026-09-24): vista con nombres repetidos ---------------------------

def test_la_condicion_en_palabras_prefiere_el_campo_de_la_misma_pantalla_o_anterior():
    """Con un nombre tecnico repetido (CLAUDE.md §8), la etiqueta de la
    condicion debe ser la del campo que la regla de visibilidad mira de
    verdad: el de la misma pantalla o, si no, el de la pantalla anterior mas
    cercana; nunca uno de una pantalla posterior."""
    from gpmc.agentes.fase3 import vista_de
    from gpmc.nucleo.manifiesto import (Actor, Campo, Condicion, Conexion, Flujo, Manifiesto,
                                        Pantalla, Tarea, Tramite)
    dup = lambda etiqueta, **k: Campo(nombre="estatus", etiqueta=etiqueta, tipo="select", **k)
    m = Manifiesto(
        tramite=Tramite(nombre="X", dependencia="D"),
        actores=[Actor(id="c", nombre="Ciudadano")],
        pantallas=[
            Pantalla(id="p1", nombre="Uno", actor="c", campos=[dup("Estatus de la solicitud")]),
            Pantalla(id="p2", nombre="Dos", actor="c", campos=[
                Campo(nombre="obs", etiqueta="Observaciones", tipo="text",
                      condicion_visible=Condicion(campo="estatus", igual="x"))]),
            Pantalla(id="p3", nombre="Tres", actor="c", campos=[dup("Estatus del pago")]),
        ],
        flujo=Flujo(tareas=[Tarea(id="t1", nombre="Uno", actor="c", inicial=True, pantallas=["p1"]),
                            Tarea(id="t_fin", nombre="Fin", terminal=True)],
                    conexiones=[Conexion(de="t1", a="t_fin")]))
    v = vista_de(m)
    assert v[1]["campos"][0]["condicion"] == "«Estatus de la solicitud» es «x»"


# --- Modo de pruebas (2026-09-24): Gemini mientras llegan las credenciales de OpenAI --------

def test_el_modo_de_pruebas_abre_el_candado_con_cualquier_proveedor_con_llave():
    """Decision del usuario del 2026-09-24: Simplificacion prueba el camino del
    AS-IS con Gemini hasta que Planeacion entregue la licencia. Solo con la
    linea explicita en el entorno; sin ella el candado sigue igual."""
    from gpmc.agentes.fase3 import modo_pruebas, puede_generar
    gem = {"GPMC_IA_PROVEEDOR": "gemini", "GPMC_IA_LLAVE": "k"}
    assert puede_generar(gem) is not None and modo_pruebas(gem) is False
    con = {**gem, "GPMC_FASE3_PRUEBAS": "1"}
    assert puede_generar(con) is None and modo_pruebas(con) is True
    assert puede_generar({"GPMC_IA_PROVEEDOR": "gemini", "GPMC_FASE3_PRUEBAS": "1"})   # sin llave
    assert puede_generar({**gem, "GPMC_FASE3_PRUEBAS": "0"}) is not None
    assert modo_pruebas({"GPMC_IA_PROVEEDOR": "openai", "GPMC_IA_LLAVE": "k",
                         "GPMC_FASE3_PRUEBAS": "1"}) is False   # con licencia no es «pruebas»


# --- Prompt v2 (2026-09-25): la escala del equipo ------------------------------
# El primer uso real con Reposicion de Certificado (2026-09-25) dio un
# Diccionario de 3 pantallas y un TO-BE de 3 tareas; el del equipo tiene 9 y 8,
# con ciclo de correccion y modalidad de pago. Las plantillas solo ensenan la
# FORMA (2 pantallas, trámite lineal) y el modelo copiaba esa escala.

def test_los_tres_contextos_llevan_el_ejemplo_de_escala():
    from gpmc.agentes import prompt_fase3 as p
    ctxs = [p.contexto_dicc("as-is"), p.contexto_tobe("as-is", "# Diccionario de Datos — X"),
            p.contexto_mejora("as-is", "b", ["[GEN-01] x"], "diccionario"),
            p.contexto_mejora("as-is", "b", ["[FLU-02] x"], "tobe", diccionario="d")]
    for ctx in ctxs:
        assert "<<EJEMPLO>>" in ctx and "<</EJEMPLO>>" in ctx
        assert "### Pantalla 8" in ctx                       # un trámite de 8 pantallas
        assert "¿@@modalidad_pago?" in ctx and "¿@@tiene_observaciones?" in ctx


def test_el_ejemplo_no_lleva_datos_de_casos_reales():
    """La columna «Ejemplo Real del Campo» del equipo trae datos de casos
    reales; el generador de DIC-08 ya la excluye y este tampoco la manda."""
    from gpmc.agentes.prompt_fase3 import ejemplo
    texto = ejemplo()
    assert "Ejemplo Real" not in texto and "caso real" not in texto
    assert not __import__("re").search(r"[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d", texto)


def test_el_ejemplo_es_coherente_y_dibujable():
    """Si el ejemplo rompiera las reglas que el prompt exige, el modelo
    aprenderia la excepcion: cada tarea del diagrama es una pantalla del
    ejemplo, y las compuertas van entre comillas."""
    import re
    from gpmc.agentes.prompt_fase3 import ejemplo
    texto = ejemplo()
    pantallas = set(re.findall(r"^### Pantalla \d+ — .+? — (.+)$", texto, re.M))
    diagrama = re.search(r"```mermaid(.*?)```", texto, re.S).group(1)
    tareas = set(re.findall(r'\["[^":]+: ([^"]+)"\]', diagrama))
    assert len(pantallas) == 8 and tareas == pantallas
    assert re.findall(r'\{"¿@@\w+\?"\}', diagrama)


def test_las_instrucciones_piden_la_escala_del_equipo():
    from gpmc.agentes import prompt_fase3 as p
    # Diccionario: cada paso conservado del AS-IS es una pantalla, y eso no es inventar.
    assert "<<EJEMPLO>>" in p.INSTRUCCION_DICC
    assert "cada paso del AS-IS que no se elimina" in p.INSTRUCCION_DICC
    assert "no es inventar" in p.INSTRUCCION_DICC
    for momento in ("corrección", "modalidad de pago", "validación manual del pago",
                    "estatus"):
        assert momento in p.INSTRUCCION_DICC, momento
    # TO-BE: una fila por requisito y por paso, y las compuertas de siempre.
    assert "<<EJEMPLO>>" in p.INSTRUCCION_TOBE
    assert "una fila por cada requisito y por cada paso del AS-IS" in p.INSTRUCCION_TOBE
    assert "ciclo de corrección" in p.INSTRUCCION_TOBE
    # Mejora: corregir no es recortar.
    assert "no quites pantallas" in p.INSTRUCCION_MEJORA


def test_el_prompt_tobe_prohibe_compuertas_encadenadas_y_ramas_sueltas():
    """Con dicc-v2/tobe-v2 y flash-lite (2026-09-25), Reposicion salio con
    `G1 -- Sí --> G2` y ramas «No» sin destino: el compilador no ramifica eso."""
    from gpmc.agentes import prompt_fase3 as p
    assert "nunca dos compuertas seguidas" in p.INSTRUCCION_TOBE
    assert "un valor más del mismo campo" in p.INSTRUCCION_TOBE
    assert "cada rama de una compuerta llega a una tarea o a `Fin`" in p.INSTRUCCION_TOBE
    assert "un valor más del mismo campo" in p.INSTRUCCION_DICC


# --- GEN-02: el ciclo de correccion (2026-09-25) --------------------------------
# Reposicion con dicc-v2/tobe-v2 salio sin la vuelta «revision -> correccion ->
# revision» que el AS-IS describe («¿Solventa la informacion? Si, regresa a
# entregar de nuevo») y que el equipo siempre modela. Cruce determinista: el
# AS-IS habla de solventar/corregir y el diagrama compilable no regresa a
# ninguna tarea anterior, o una rama de correccion muere en Fin.

_ASIS_CON_CICLO = ("# Análisis AS-IS — X\n\n- Revisión: si falta algo, el ciudadano "
                   "regresa a solventar las observaciones.\n")
_TOBE_LINEAL = ("```mermaid\nflowchart TD\n"
                "  P1[Ciudadano: Solicitud] --> P2[Funcionario: Revisión]\n"
                "  P2 --> G{\"¿@@dictamen?\"}\n"
                "  G -- Aprobado --> P3[Funcionario: Emisión]\n"
                "  G -- Rechazado --> Fin([Fin])\n  P3 --> Fin\n```")
_TOBE_CON_VUELTA = ("```mermaid\nflowchart TD\n"
                    "  P1[Ciudadano: Solicitud] --> P2[Funcionario: Revisión]\n"
                    "  P2 --> G{\"¿@@dictamen?\"}\n"
                    "  G -- Aprobado --> P3[Funcionario: Emisión]\n"
                    "  G -- Requiere corrección --> P4[Ciudadano: Corrección]\n"
                    "  P4 --> P2\n  P3 --> Fin([Fin])\n```")


def _m_dictamen():
    return _manifiesto([{"nombre": "dictamen", "etiqueta": "Dictamen", "tipo": "select"}])


def test_as_is_con_ciclo_y_diagrama_sin_vuelta_es_gen02():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    huecos = verificar_cruzado(_ASIS_CON_CICLO, _TOBE_LINEAL, _m_dictamen())
    g = [h for h in huecos if h.codigo == "GEN-02"]
    assert len(g) == 1 and g[0].nivel == "falta_dato" and g[0].ubicacion == "flujo"
    assert "solventar" in g[0].mensaje and "corrección" in g[0].mensaje


def test_diagrama_con_vuelta_no_produce_gen02():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    huecos = verificar_cruzado(_ASIS_CON_CICLO, _TOBE_CON_VUELTA, _m_dictamen())
    assert not any(h.codigo == "GEN-02" for h in huecos)


def test_as_is_sin_ciclo_no_produce_gen02_aunque_el_diagrama_sea_lineal():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    huecos = verificar_cruzado("# Análisis AS-IS — X\n\n- Se entrega y se emite.\n",
                               _TOBE_LINEAL, _m_dictamen())
    assert not any(h.codigo == "GEN-02" for h in huecos)


def test_rama_de_correccion_que_muere_en_fin_es_gen02_aunque_el_as_is_calle():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    tobe = _TOBE_LINEAL.replace("G -- Rechazado --> Fin", "G -- Requiere corrección --> Fin")
    huecos = verificar_cruzado("# Análisis AS-IS — X\n", tobe, _m_dictamen())
    g = [h for h in huecos if h.codigo == "GEN-02"]
    assert len(g) == 1 and "Requiere corrección" in g[0].mensaje and "Fin" in g[0].mensaje


def test_gen02_se_atribuye_al_tobe_y_entra_a_la_ronda_de_mejora(tmp_path):
    from gpmc.agentes.fase3 import atribuir, generar
    from gpmc.agentes.proveedor import ProveedorFalso
    from gpmc.nucleo.huecos import Hueco
    assert atribuir(Hueco("falta_dato", "GEN-02", "flujo", "x")) == "tobe"
    dicc = _DICC_OK.replace("Lista (Aprobado, Rechazado)", "Lista (Aprobado, Requiere corrección)")
    tobe_1 = "# Propuesta TO-BE — Constancia\n\n" + _TOBE_LINEAL.replace(
        "P3[Funcionario: Emisión]", "P3[Funcionario: Emisión]").replace("Rechazado", "Requiere corrección")
    # El Diccionario de prueba tambien tiene huecos: primero se mejora ese
    # (llamada 3) y despues el TO-BE (llamada 4), que es la que ve el GEN-02.
    prov = ProveedorFalso([_json("diccionario", dicc), _json("tobe", tobe_1),
                           _json("diccionario", dicc), _json("tobe", tobe_1)])
    generar(_ASIS_CON_CICLO, prov, tmp_path, "g" * 16)
    assert prov.llamadas == 4 and "[GEN-02]" in prov.ultimo_contexto


def test_dos_ramas_que_se_juntan_no_son_un_ciclo():
    """Reposicion v2: «En línea» y «Validación manual» llegan a la misma
    Emision. El orden de visita hacia parecer ciclo esa union y el GEN-02 no
    salia. Un ciclo es una arista desde cuyo destino se vuelve al origen."""
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    tobe = ("```mermaid\nflowchart TD\n"
            "  P1[Ciudadano: Solicitud] --> P2[Funcionario: Revisión]\n"
            "  P2 --> G{\"¿@@dictamen?\"}\n"
            "  G -- En línea --> P4[Funcionario: Emisión]\n"
            "  G -- Banco --> P3[Funcionario: Validación]\n"
            "  P3 --> P4\n  P4 --> Fin([Fin])\n```")
    huecos = verificar_cruzado(_ASIS_CON_CICLO, tobe, _m_dictamen())
    assert any(h.codigo == "GEN-02" for h in huecos)


def test_una_mejora_que_recorta_el_documento_no_gana_aunque_tenga_menos_huecos(tmp_path):
    """Reposicion, 2026-09-25: la ronda 2 del TO-BE volvio truncada (el JSON se
    cerro a media linea del diagrama), tenia UN hueco (MMD-01, sin mermaid)
    contra tres de la ronda 1, y gano. Corregir no es recortar: la ronda 2
    solo se conserva si no pierde pantallas (Diccionario) ni tareas (TO-BE)."""
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    tobe_1 = "# Propuesta TO-BE — Constancia\n\n" + _TOBE_LINEAL.replace("Rechazado", "Requiere corrección")
    tobe_2_truncado = "# Propuesta TO-BE — Constancia\n\n### Diagrama compilable\n\n```mermaid\nflowchart TD\n    P1["
    prov = ProveedorFalso([_json("diccionario", _DICC_OK), _json("tobe", tobe_1),
                           _json("diccionario", _DICC_OK), _json("tobe", tobe_2_truncado)])
    g = generar(_ASIS_CON_CICLO, prov, tmp_path, "h" * 16)
    assert prov.llamadas == 4
    assert g.tobe.ronda == 1 and g.tobe.texto == tobe_1
    assert any(h.codigo == "GEN-02" for h in g.tobe.huecos)
    assert not any(h.codigo == "MMD-01" for h in g.tobe.huecos)


# --- GEN-03: etiqueta de arista fuera del catalogo (2026-09-25) -----------------
# Reposicion v2: «Transferencia o referencia bancaria» en la compuerta de
# @@modalidad_pago, cuyo catalogo dice «Banco o transferencia». Una sola
# etiqueta asi tira TODO el flujo a lineal (FLU-01), y el FLU-01 es generico:
# el modelo no sabe que corregir. Este cruce nombra la etiqueta y el catalogo.

def test_etiqueta_de_arista_fuera_del_catalogo_es_gen03_con_los_valores():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    m = _manifiesto([{"nombre": "modalidad_pago", "etiqueta": "Modalidad de pago", "tipo": "select",
                      "catalogo": [{"etiqueta": "En línea", "valor": "en_linea"},
                                   {"etiqueta": "Banco o transferencia", "valor": "banco_o_transferencia"}]}])
    tobe = ("```mermaid\nflowchart TD\n"
            "  P1[Ciudadano: Solicitud] --> G{\"¿@@modalidad_pago?\"}\n"
            "  G -- En línea --> P2[Funcionario: Emisión]\n"
            "  G -- Transferencia o referencia bancaria --> P3[Funcionario: Validación]\n```")
    huecos = verificar_cruzado("# Análisis AS-IS — X\n", tobe, m)
    g = [h for h in huecos if h.codigo == "GEN-03"]
    assert len(g) == 1 and g[0].nivel == "falta_dato" and g[0].ubicacion == "G"
    assert "Transferencia o referencia bancaria" in g[0].mensaje
    assert "@@modalidad_pago" in g[0].mensaje and "Banco o transferencia" in g[0].mensaje
    assert "En línea" not in g[0].mensaje.split("catálogo")[0]     # la buena no se reporta


def test_etiquetas_si_no_y_del_catalogo_no_producen_gen03():
    from gpmc.agentes.verificar_fase3 import verificar_cruzado
    m = _manifiesto([{"nombre": "procede", "etiqueta": "Procede", "tipo": "select",
                      "catalogo": [{"etiqueta": "Sí", "valor": "si"}, {"etiqueta": "No", "valor": "no"}]}])
    tobe = ("```mermaid\nflowchart TD\n  P1[Ciudadano: Solicitud] --> G{\"¿@@procede?\"}\n"
            "  G -- Sí --> P2[Funcionario: Emisión]\n  G -- No --> Fin([Fin])\n```")
    assert not any(h.codigo == "GEN-03" for h in verificar_cruzado("# X\n", tobe, m))


def test_gen03_se_atribuye_al_tobe():
    from gpmc.agentes.fase3 import atribuir
    from gpmc.nucleo.huecos import Hueco
    assert atribuir(Hueco("falta_dato", "GEN-03", "G", "x")) == "tobe"


# --- medir-ia --fase3: medida estructural y el ejemplo fuera (2026-09-25) --------
# «Tareas que casan» compara por nombre y el modelo bautiza distinto que el
# equipo («Solicitud de Reposicion» vs «Nueva Solicitud»): salia ~0 aunque la
# estructura fuera la misma. Y Avisos Judiciales viaja como <<EJEMPLO>> en el
# prompt: medirlo contra si mismo daba 7/8 tareas, cifra inflada.

def test_medir_fase3_trae_la_medida_estructural(tmp_path):
    from gpmc.agentes.medir_fase3 import medir_carpeta, imprimir
    from gpmc.agentes.proveedor import ProveedorFalso
    _expediente_humano(tmp_path)
    tobe_gen = ("# Propuesta TO-BE — Constancia\n\n" + _TOBE_CON_VUELTA)   # ramifica y vuelve
    # La Pantalla 2 lleva su catalogo en la columna de siempre: sin opciones el
    # flujo no ramifica y no habria compuerta que medir.
    dicc_gen = _DICC_OK.split("### Pantalla 2")[0] + (
        "### Pantalla 2 — Funcionario — Revisión\n\n"
        "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Descripcion |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Dictamen | Select | Lista desplegable | Si | Siempre visible | N/A | Aprobado · Requiere corrección | `@@dictamen` |\n") + (
        "\n### Pantalla 3 — Funcionario — Emisión\n\n"
        "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
        "| Constancia | Archivo | Visor | Si | `@@constancia` |\n"
        "\n### Pantalla 4 — Ciudadano — Corrección\n\n"
        "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
        "| Documento corregido | Archivo | Visor | Si | `@@doc_corregido` |\n")
    prov = ProveedorFalso([_json("diccionario", dicc_gen), _json("tobe", tobe_gen)] * 3)
    m = medir_carpeta(tmp_path, prov, tmp_path / "almacen")[0]
    assert m.estado == "listo"
    assert (m.pantallas_humano, m.pantallas_generadas) == (2, 4)
    assert (m.compuertas_humano, m.compuertas_generadas) == (0, 1)
    assert (m.ciclo_humano, m.ciclo_generado) == (False, True)
    salida = imprimir(m and [m])
    assert "pant." in salida and "4/2" in salida and "1/0" in salida and "ciclo" in salida


def test_medir_fase3_no_mide_el_tramite_que_viaja_como_ejemplo(tmp_path):
    from gpmc.agentes.medir_fase3 import medir_carpeta, imprimir
    from gpmc.agentes.prompt_fase3 import NOMBRE_EJEMPLO
    from gpmc.agentes.proveedor import ProveedorFalso
    assert NOMBRE_EJEMPLO == "Publicación de Avisos Judiciales en el Periódico Oficial"
    d = tmp_path / "ANITA" / "PO" / NOMBRE_EJEMPLO
    d.mkdir(parents=True)
    (d / "Análisis AS-IS.md").write_text(_ASIS_INLINE, encoding="utf-8")
    (d / "Propuesta TO-BE.md").write_text(_TOBE_OK, encoding="utf-8")
    (d / "Diccionario de Datos.md").write_text(_DICC_OK, encoding="utf-8")
    prov = ProveedorFalso([])
    medidas = medir_carpeta(tmp_path, prov, tmp_path / "almacen")
    assert len(medidas) == 1 and medidas[0].estado == "ejemplo del prompt"
    assert prov.llamadas == 0
    assert "ejemplo del prompt" in imprimir(medidas)
