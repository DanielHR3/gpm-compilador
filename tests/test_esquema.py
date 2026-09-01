from gpmc.nucleo import esquema
from gpmc.nucleo.formato import leer
from tests.conftest import legible as _legible


def test_campo_tiene_las_25_claves_reales(exports_autenticos, export_referencia):
    """El esquema de campo de la plataforma tiene 25 claves; emitir menos lo rompe."""
    real = leer(export_referencia)["Formularios"][0]["Campos"][0]
    nuestro = esquema.campo(
        id="1", nombre="curp", tipo="text", etiqueta="CURP",
        formulario_id="10", posicion="1",
    )
    assert set(nuestro) == set(real)
    assert list(nuestro) == list(real), "el orden de las claves tambien debe coincidir"


def test_tarea_tiene_las_40_claves_reales(exports_autenticos, export_referencia):
    real = leer(export_referencia)["Tareas"][0]
    nuestra = esquema.tarea(id="1", identificador="box_1", nombre="Captura", proceso_id="99")
    assert set(nuestra) == set(real)


def test_proceso_incluye_las_tres_colecciones_vacias():
    p = esquema.proceso(
        id="1", nombre="X", homoclave="", ruts=esquema.RUTS(),
        tareas=[], formularios=[], acciones=[], conexiones=[], documentos=[],
    )
    assert p["Sections"] == []
    assert p["ElectronicFiles"] == []
    assert p["Documentos"] == []


def test_extra_de_raiz_va_doblemente_codificado():
    """La plataforma guarda extra como un string JSON que contiene otro string JSON."""
    import json

    p = esquema.proceso(
        id="1", nombre="X", homoclave="", ruts=esquema.RUTS(),
        tareas=[], formularios=[], acciones=[], conexiones=[], documentos=[],
    )
    interno = json.loads(p["extra"])
    assert isinstance(interno, str), "el primer loads debe devolver otro string"
    assert json.loads(interno)["folio_consecutivo_inicial"] == "1"


def test_publico_activa_public_y_add_in_menu_juntos():
    """En los 12 exports auténticos 'public' y 'add_in_menu' se mueven juntos: un
    trámite visible en el portal del ciudadano tiene los dos en '1'; los ocultos,
    los dos en '0'. Emitir 'public=1' con 'add_in_menu=0' deja el trámite fuera del
    menú del ciudadano, así que no se puede iniciar. Verificado en el portal el
    2026-08-31."""
    pub = esquema.proceso(
        id="1", nombre="X", homoclave="", ruts=esquema.RUTS(publico=True),
        tareas=[], formularios=[], acciones=[], conexiones=[], documentos=[],
    )
    assert pub["public"] == "1"
    assert pub["add_in_menu"] == "1"

    priv = esquema.proceso(
        id="1", nombre="X", homoclave="", ruts=esquema.RUTS(publico=False),
        tareas=[], formularios=[], acciones=[], conexiones=[], documentos=[],
    )
    assert priv["public"] == "0"
    assert priv["add_in_menu"] == "0"


def test_conexion_secuencial_versus_evaluacion():
    assert esquema.conexion(1, 10, 20)["tipo"] == "secuencial"
    assert esquema.conexion(1, 10, 20)["regla"] is None
    cond = esquema.conexion(2, 10, 30, regla="@@x=='si'")
    assert cond["tipo"] == "evaluacion"
    assert cond["regla"] == "@@x=='si'"


def test_catalogo_va_como_string_json():
    c = esquema.campo(
        id="1", nombre="tipo", tipo="radio", etiqueta="Tipo",
        formulario_id="10", posicion="1",
        datos=[{"etiqueta": "Sí", "valor": "si"}],
    )
    import json
    assert isinstance(c["datos"], str)
    assert json.loads(c["datos"])[0]["valor"] == "si"
