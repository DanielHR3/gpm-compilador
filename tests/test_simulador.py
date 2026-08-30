import json

import pytest

from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.simulador.analisis import analizar
from gpmc.simulador.html import generar

BASE = {
    "tramite": {"nombre": "Prueba", "dependencia": "DGT"},
    "actores": [{"id": "ciudadano", "nombre": "Ciudadano"},
                {"id": "func", "nombre": "Funcionario", "tipo": "grupo",
                 "grupos_usuarios": ["Area"]}],
    "pantallas": [
        {"id": "p1", "nombre": "Solicitud", "actor": "ciudadano", "paso_ciudadano": 1,
         "campos": [{"nombre": "curp", "etiqueta": "CURP", "tipo": "text", "obligatorio": True}]},
        {"id": "p2", "nombre": "Revisión", "actor": "func",
         "campos": [{"nombre": "ok", "etiqueta": "¿Correcto?", "tipo": "radio",
                     "catalogo": [{"etiqueta": "Sí", "valor": "si"},
                                  {"etiqueta": "No", "valor": "no"}]}]},
    ],
    "flujo": {
        "tareas": [
            {"id": "t1", "nombre": "Capturar", "actor": "ciudadano", "inicial": True, "pantallas": ["p1"]},
            {"id": "t2", "nombre": "Revisar", "actor": "func", "pantallas": ["p2"]},
            {"id": "t3", "nombre": "Fin", "terminal": True},
        ],
        "conexiones": [
            {"de": "t1", "a": "t2"},
            {"de": "t2", "a": "t3", "cuando": {"campo": "ok", "igual": "si"}},
            {"de": "t2", "a": "t1", "cuando": {"campo": "ok", "igual": "no"}},
        ],
    },
    "acciones": [],
}


def _m(**cambios):
    return Manifiesto.model_validate({**BASE, **cambios})


def test_un_flujo_sano_no_reporta_problemas():
    assert analizar(_m()).problemas == []


def test_detecta_tarea_inalcanzable():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["tareas"].append({"id": "t9", "nombre": "Huerfana", "actor": "func"})
    p = analizar(Manifiesto.model_validate(d)).problemas
    assert any("t9" in x and "alcanz" in x.lower() for x in p), p


def test_detecta_condicion_sobre_valor_fuera_del_catalogo():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["conexiones"][1]["cuando"]["igual"] = "quiza"
    p = analizar(Manifiesto.model_validate(d)).problemas
    assert any("quiza" in x for x in p), p


def test_detecta_campo_usado_antes_de_capturarse():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["conexiones"][0] = {"de": "t1", "a": "t2",
                                   "cuando": {"campo": "ok", "igual": "si"}}
    p = analizar(Manifiesto.model_validate(d)).problemas
    assert any("antes" in x.lower() or "captur" in x.lower() for x in p), p


def test_precalcula_la_tabla_de_transiciones_con_el_evaluador_compartido():
    a = analizar(_m())
    t2 = a.transiciones["t2"]
    assert t2["campo"] == "ok"
    assert t2["destinos"]["si"] == "t3"
    assert t2["destinos"]["no"] == "t1"


def test_el_html_es_autocontenido_y_no_evalua_reglas_en_javascript():
    html = generar(_m())
    assert "<!" not in html[:20], "el artefacto es un fragmento, no un documento con doctype propio"
    assert "http://" not in html and "https://" not in html, "debe ser autocontenido"
    assert "@@" not in html, "el JS no debe recibir sintaxis de reglas de GPM"
    assert "TRANSICIONES" in html, "el JS consulta una tabla precalculada por Python"


def test_el_html_incluye_las_pantallas_los_campos_y_el_stepper():
    html = generar(_m())
    assert "CURP" in html
    assert "¿Correcto?" in html
    assert "Solicitud" in html
    assert "Paso 1" in html or "paso_ciudadano" in html


def test_el_html_marca_los_problemas_detectados():
    d = json.loads(json.dumps(BASE))
    d["flujo"]["tareas"].append({"id": "t9", "nombre": "Huerfana", "actor": "func"})
    html = generar(Manifiesto.model_validate(d))
    assert "t9" in html


def test_el_html_se_declara_como_simulacion():
    html = generar(_m())
    assert "simulaci" in html.lower()


def test_usa_la_paleta_institucional_real():
    """Muestreada de las capturas de la plataforma de modelado."""
    html = generar(_m())
    assert "#5e132c" in html or "#66132a" in html


def test_el_aviso_de_simulacion_sigue_siendo_prominente():
    """Al parecerse a la plataforma real, el aviso importa mas, no menos."""
    html = generar(_m())
    i = html.lower().index("simulaci")
    assert i < len(html) * 0.5, "el aviso debe ir arriba, no al pie"
    assert "no es" in html.lower() or "no la plataforma" in html.lower()


# Pantalla con catalogos remotos: uno simple, uno en cascada, y uno cuyo
# endpoint no esta en el registro. Inline, sin red.
_CON_CATALOGOS = {
    "pantallas": [
        {"id": "p1", "nombre": "Domicilio", "actor": "ciudadano", "campos": [
            {"nombre": "estado_sol", "etiqueta": "Estado", "tipo": "select",
             "endpoint": "mgee"},
            {"nombre": "municipio_sol", "etiqueta": "Municipio", "tipo": "select",
             "endpoint": "mgem", "dependencia_tipo": "campo",
             "dependencia_campo": "estado_sol"},
            {"nombre": "raro_sol", "etiqueta": "Raro", "tipo": "select",
             "endpoint": "consultarfc"},
        ]},
    ],
    "flujo": {
        "tareas": [{"id": "t1", "nombre": "Capturar", "actor": "ciudadano",
                    "inicial": True, "pantallas": ["p1"]},
                   {"id": "tf", "nombre": "Fin", "terminal": True}],
        "conexiones": [{"de": "t1", "a": "tf"}],
    },
}


def test_el_simulador_lleva_la_url_del_catalogo_remoto():
    html = generar(_m(**_CON_CATALOGOS))
    assert "https://gaia.inegi.org.mx/wscatgeo/v2/mgee" in html
    assert '"catalogo_nodo": "datos"' in html or '"catalogo_nodo":"datos"' in html


def test_el_simulador_lleva_el_mapeo_etiqueta_valor():
    # Si etiqueta y valor se invierten, la cascada pide mgem/Hidalgo en vez de
    # mgem/13 e INEGI no devuelve nada. Ninguna otra prueba lo detectaria.
    html = generar(_m(**_CON_CATALOGOS))
    assert '"catalogo_etiqueta": "nomgeo"' in html or '"catalogo_etiqueta":"nomgeo"' in html
    assert '"catalogo_valor": "cvegeo"' in html or '"catalogo_valor":"cvegeo"' in html


def test_la_cascada_declara_de_quien_depende_y_deja_el_hueco_del_padre():
    html = generar(_m(**_CON_CATALOGOS))
    assert '"depende_de": "estado_sol"' in html or '"depende_de":"estado_sol"' in html
    # La plataforma interpola @@campo en tiempo de ejecucion; el simulador no
    # tiene ese runtime y sustituye el valor elegido, asi que la URL viaja con
    # un hueco {padre} y SIN la sintaxis de GPM.
    assert "wscatgeo/v2/mgem/{padre}" in html
    assert "@@" not in html


def test_un_endpoint_no_registrado_no_inventa_una_url():
    html = generar(_m(**_CON_CATALOGOS))
    assert "consultarfc" not in html.split("const PANTALLAS")[1].split("const ACTORES")[0] \
        or "catalogo_url" not in html.split("raro_sol")[1].split("}")[0]


def test_un_select_sin_catalogo_resoluble_sale_deshabilitado():
    # El simulador no puede mentir sobre lo que hara la plataforma: un campo que
    # es desplegable se dibuja como desplegable, aunque no se pueda poblar.
    html = generar(_m(**_CON_CATALOGOS))
    assert "disabled" in html


def test_el_simulador_conecta_los_catalogos_y_reporta_el_fallo():
    html = generar(_m(**_CON_CATALOGOS))
    assert "conectarCatalogos" in html
    assert "no se pudo consultar el catálogo" in html


def test_las_unicas_urls_externas_son_catalogos_del_registro():
    """La prueba de arriba fija que un tramite SIN catalogos remotos no trae
    ninguna URL. Este caso es el otro: cuando si los trae, las unicas URLs
    permitidas son las del registro. Sin esto, 'autocontenido' se debilitaria en
    silencio en cuanto un tramite declare un endpoint."""
    import re
    from gpmc.nucleo.integraciones import CATALOGOS

    html = generar(_m(**_CON_CATALOGOS))
    urls = set(re.findall(r"https?://[^\s\"'`<>)]+", html))
    assert urls, "este tramite si declara catalogos remotos"

    permitidas = set()
    for cat in CATALOGOS.values():
        permitidas.add(cat.url.split("@@")[0].rstrip("/?&="))
    for u in urls:
        raiz = u.split("{padre}")[0].rstrip("/?&=")
        assert any(raiz.startswith(p) for p in permitidas), \
            f"URL externa que no viene del registro de catalogos: {u}"


def test_el_simulador_no_hace_red_desde_python():
    """La red vive en el navegador. Si Python la hiciera, el nucleo perderia su
    invariante y las pruebas dependerian de que INEGI este arriba."""
    import inspect
    from gpmc.simulador import html as modulo
    fuente = inspect.getsource(modulo)
    for prohibido in ("import requests", "import urllib", "urlopen", "httpx"):
        assert prohibido not in fuente, f"{prohibido} no debe aparecer en el simulador"
