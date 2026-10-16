from gpmc.extractores import metadatos as ext
from gpmc.nucleo.huecos import Hueco


_AS_IS_MINIMO = """---
dependencia: Secretaría X
---
# Análisis AS-IS — Trámite de prueba
"""


_AS_IS_WIKILINK = """---
tramite: "[[1. REINGENIERIA/_recuperados/Alta de Avisos de Testamento]]"
dependencia: Secretaría X
---
# Análisis AS-IS — Alta de Avisos de Testamento
"""


_AS_IS_H1_NO_ESTANDAR = """# Arquitectura Actual (AS-IS) - Acceso a la Información

## Descripción del flujo
Texto cualquiera.
"""


def test_el_nombre_del_wikilink_es_solo_el_ultimo_segmento():
    # El frontmatter de Obsidian trae la ruta completa de la bóveda; el nombre
    # del trámite es solo la última nota, no "1. REINGENIERIA/_recuperados/...".
    r = ext.extraer(_AS_IS_WIKILINK)
    assert r.tramite is not None
    assert r.tramite.nombre == "Alta de Avisos de Testamento"


def test_saca_el_nombre_de_un_h1_no_estandar_que_menciona_as_is():
    r = ext.extraer(_AS_IS_H1_NO_ESTANDAR)
    assert r.tramite is not None
    assert r.tramite.nombre == "Acceso a la Información"


def test_una_carpeta_con_forma_de_id_de_sesion_no_se_usa_como_nombre():
    # El asistente web pasa el id de sesión como nombre de carpeta temporal.
    # No es un nombre de trámite: debe reportarse META-04, no aceptarse en silencio.
    r = ext.extraer("# Documento sin nombre de trámite\n",
                    nombre_carpeta="b5a8defd46ca96d2")
    assert r.tramite is None
    assert [h for h in r.huecos if h.codigo == "META-04"]


def test_una_carpeta_con_nombre_normal_si_es_el_ultimo_recurso():
    # Guarda de regresión: la CLI pasa el nombre real del expediente.
    r = ext.extraer("# Documento sin nombre de trámite\n",
                    nombre_carpeta="Alta de Avisos de Testamento")
    assert r.tramite is not None
    assert r.tramite.nombre == "Alta de Avisos de Testamento"


def test_huecos_son_Hueco_y_traen_codigo_meta():
    r = ext.extraer(_AS_IS_MINIMO)
    assert r.huecos
    assert all(isinstance(h, Hueco) for h in r.huecos)
    codigos = {h.codigo for h in r.huecos}
    assert "META-01" in codigos            # falta el tiempo de respuesta
    assert all(c.startswith("META-") for c in codigos)


def test_tiempo_faltante_es_falta_dato():
    r = ext.extraer(_AS_IS_MINIMO)
    meta01 = [h for h in r.huecos if h.codigo == "META-01"][0]
    assert meta01.nivel == "falta_dato"


def test_costo_faltante_es_por_confirmar():
    r = ext.extraer(_AS_IS_MINIMO)
    meta03 = [h for h in r.huecos if h.codigo == "META-03"][0]
    assert meta03.nivel == "por_confirmar"


# --- la dependencia tambien vive en la Ficha tecnica (2026-10-16) --------------

_AS_IS_SIN_FRONTMATTER = """# Análisis AS-IS — Constancia de Residencia

El ciudadano acude a la ventanilla. **Tiempo de respuesta:** 3 días hábiles.
"""

_DICC_CON_FICHA = """# Diccionario de Datos — Constancia de Residencia

## Ficha técnica

| Campo | Dato |
|---|---|
| Nombre del trámite | Constancia de Residencia |
| Dependencia responsable | Presidencia Municipal — Secretaría General |
| Tipo | Trámite |
"""


def test_sin_frontmatter_la_dependencia_sale_de_la_ficha_tecnica_del_diccionario():
    # En «Solo tengo el AS-IS» el modelo escribe la Ficha tecnica con la
    # dependencia, pero META-02 bloqueaba el .gpm porque solo se leia el
    # frontmatter. Nueve de nueve propuestas lo arrastraban.
    r = ext.extraer(_AS_IS_SIN_FRONTMATTER, diccionario=_DICC_CON_FICHA)
    assert r.tramite.dependencia == "Presidencia Municipal — Secretaría General"
    assert not [h for h in r.huecos if h.codigo == "META-02"]


def test_sin_frontmatter_la_dependencia_sale_de_la_ficha_tecnica_del_as_is():
    # Constancia de No Infraccion trae la misma tabla en el cuerpo del AS-IS.
    as_is = _AS_IS_SIN_FRONTMATTER + "\n| Dependencia responsable | SEMARNATH — Dirección de Verificación Vehicular |\n"
    r = ext.extraer(as_is)
    assert r.tramite.dependencia == "SEMARNATH — Dirección de Verificación Vehicular"
    assert not [h for h in r.huecos if h.codigo == "META-02"]


def test_el_frontmatter_gana_sobre_la_ficha_tecnica():
    as_is = "---\ndependencia: Secretaría X\n---\n" + _AS_IS_SIN_FRONTMATTER
    r = ext.extraer(as_is, diccionario=_DICC_CON_FICHA)
    assert r.tramite.dependencia == "Secretaría X"


def test_una_ficha_con_la_dependencia_pendiente_no_cuenta():
    # «[Pendiente de confirmar]» es lo que el prompt manda escribir cuando el
    # AS-IS no lo dice: no es una dependencia, y META-02 sigue en pie.
    dicc = _DICC_CON_FICHA.replace("Presidencia Municipal — Secretaría General", "[Pendiente de confirmar]")
    r = ext.extraer(_AS_IS_SIN_FRONTMATTER, diccionario=dicc)
    assert r.tramite.dependencia == "[por confirmar]"
    assert [h for h in r.huecos if h.codigo == "META-02"]
