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
    assert g.diccionario.version_prompt == "mejora-v1"
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
