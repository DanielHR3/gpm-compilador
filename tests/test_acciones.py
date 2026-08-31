import json

import pytest

from gpmc.compilador.acciones import (
    construir_acciones, php_costo, php_documento, php_folio,
)
from gpmc.nucleo.manifiesto import Accion


def test_el_folio_usa_bloqueo_transaccional_nunca_count_ni_rand():
    """Las dos implementaciones existentes usan ->count() o rand(); ninguna sirve."""
    php = php_folio(prefijo="BT", variable="folio")
    assert "lockForUpdate()" in php
    assert "->count()" not in php
    assert "rand(" not in php


def test_el_folio_usa_la_forma_autentica_dato_seguimiento():
    """Forma copiada de los dos exports auténticos que sí funcionan
    (constancia-ambiental, pago-de-bases): el contador se llavea por el NOMBRE de
    la variable en la tabla 'dato_seguimiento', columna 'valor'. Ver acta
    2026-08-30, PLAT-4."""
    php = php_folio(prefijo="BT", variable="numero_folio")
    assert "dato_seguimiento" in php
    assert "->where('nombre', 'numero_folio')" in php
    assert "->value('valor')" in php


def test_el_folio_no_referencia_proceso_id():
    """Regresión de PLAT-4: la plataforma reasigna el proceso_id al importar y NO
    reescribe las referencias dentro del PHP. Un folio que lo hardcodee queda roto
    tras importar. La forma auténtica no lo menciona."""
    php = php_folio(prefijo="BT", variable="folio")
    assert "proceso_id" not in php


def test_el_folio_no_comenta_el_return_en_una_sola_linea():
    """La expresión va en una sola línea. Un comentario '//' comentaría todo lo
    que le sigue —el str_pad y el return— y el folio devolvería null. El export
    auténtico trae ese '//'; nosotros no lo reproducimos."""
    php = php_folio(prefijo="BT", variable="folio")
    assert "\n" not in php
    assert "//" not in php
    assert "return" in php


def test_el_folio_incluye_el_prefijo_y_el_anio():
    php = php_folio(prefijo="SEDECO-VOI", variable="folio")
    assert "SEDECO-VOI" in php
    assert "date('Y')" in php


def test_el_documento_escapa_toda_variable():
    """DOC-01. Ni una implementacion ni la DGT escapan; el compilador siempre lo hace."""
    php = php_documento(plantilla="<h1>{{nombre}}</h1>", variables=["nombre"])
    assert "htmlspecialchars" in php
    assert "ENT_QUOTES" in php


def test_el_documento_no_interpola_variables_no_declaradas():
    with pytest.raises(ValueError, match="apellido"):
        php_documento(plantilla="<p>{{apellido}}</p>", variables=["nombre"])


def test_el_costo_emite_la_tabla_de_tarifas():
    php = php_costo(variable="monto", tarifas={"persona_fisica": 76, "persona_moral": 152})
    assert "76" in php and "152" in php
    assert "persona_fisica" in php


def test_construye_una_accion_de_folio():
    accs, docs, _ = construir_acciones(
        [Accion(tipo="folio", nombre="crear-folio", variable="folio", prefijo="BT")],
        proceso_id="900",
        ids=iter(range(5000, 5100)),
    )
    assert len(accs) == 1 and docs == []
    a = accs[0]
    assert a["tipo"] == "variable"
    assert a["nombre"] == "crear-folio"
    extra = json.loads(a["extra"])
    assert extra["variable"] == "folio"
    assert "lockForUpdate()" in extra["expresion"]
    # PLAT-4: la expresión no puede llevar proceso_id; la plataforma lo reasigna
    assert "proceso_id" not in extra["expresion"]
    assert "dato_seguimiento" in extra["expresion"]


def test_construye_una_notificacion_como_enviar_correo():
    accs, docs, _ = construir_acciones(
        [Accion(tipo="notificacion", nombre="avisar", para="@@correo",
                asunto="Resolución", contenido="Su trámite fue resuelto.")],
        proceso_id="900",
        ids=iter(range(5000, 5100)),
    )
    a = accs[0]
    assert a["tipo"] == "enviar_correo"
    extra = json.loads(a["extra"])
    assert extra["para"] == "@@correo"
    assert extra["tema"] == "Resolución"


def test_la_notificacion_exige_destinatario():
    with pytest.raises(ValueError, match="destinatario"):
        construir_acciones(
            [Accion(tipo="notificacion", nombre="avisar", asunto="X", contenido="Y")],
            proceso_id="900",
            ids=iter(range(5000, 5100)),
        )


def test_el_documento_produce_una_entidad_documento():
    accs, docs, _ = construir_acciones(
        [Accion(tipo="documento", nombre="oficio", variable="oficio_contenido",
                plantilla="<p>{{folio}}</p>", variables=["folio"])],
        proceso_id="900",
        ids=iter(range(5000, 5100)),
    )
    assert len(docs) == 1
    d = docs[0]
    assert d["output"] == "pdf"
    assert d["paper_size"] == "LETTER"
    assert d["proceso_id"] == "900"
    assert len(d) == 29, "la entidad Documento tiene 29 claves"


def test_el_documento_no_configura_firma():
    _, docs, _ = construir_acciones(
        [Accion(tipo="documento", nombre="oficio", variable="x",
                plantilla="<p>hola</p>", variables=[])],
        proceso_id="900",
        ids=iter(range(5000, 5100)),
    )
    d = docs[0]
    for clave in ("firmador_nombre", "firmador_cargo", "hsm_configuracion_id", "timbre", "validez"):
        assert d[clave] is None, f"{clave} no debe configurarse por inferencia"

def test_el_documento_configura_firma_si_se_pide():
    _, docs, _ = construir_acciones(
        [
            Accion(
                nombre="d", tipo="documento",
                plantilla="Cuerpo", variables=[],
                firmador_nombre="Juan", firmador_cargo="Jefe",
                titulo="Tit", subtitulo="Sub"
            )
        ],
        "123",
        iter(range(5000, 5100))
    )
    d = docs[0]
    assert d["firmador_nombre"] == "Juan"
    assert d["firmador_cargo"] == "Jefe"
    assert d["titulo"] == "Tit"
    assert d["subtitulo"] == "Sub"
