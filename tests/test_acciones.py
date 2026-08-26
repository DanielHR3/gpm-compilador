import json

import pytest

from gpmc.compilador.acciones import (
    construir_acciones, php_costo, php_documento, php_folio,
)
from gpmc.nucleo.manifiesto import Accion


def test_el_folio_usa_bloqueo_transaccional_nunca_count_ni_rand():
    """Las dos implementaciones existentes usan ->count() o rand(); ninguna sirve."""
    php = php_folio(prefijo="BT", proceso_id="820", inicial=1)
    assert "lockForUpdate()" in php
    assert "->count()" not in php
    assert "rand(" not in php


def test_el_folio_usa_la_columna_contador():
    php = php_folio(prefijo="BT", proceso_id="820", inicial=1)
    assert "'contador'" in php


def test_el_folio_incluye_el_prefijo_y_el_anio():
    php = php_folio(prefijo="SEDECO-VOI", proceso_id="900", inicial=1)
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
    accs, docs = construir_acciones(
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


def test_construye_una_notificacion_como_enviar_correo():
    accs, _ = construir_acciones(
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
    accs, docs = construir_acciones(
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
    _, docs = construir_acciones(
        [Accion(tipo="documento", nombre="oficio", variable="x",
                plantilla="<p>hola</p>", variables=[])],
        proceso_id="900",
        ids=iter(range(5000, 5100)),
    )
    d = docs[0]
    for clave in ("firmador_nombre", "firmador_cargo", "hsm_configuracion_id", "timbre", "validez"):
        assert d[clave] is None, f"{clave} no debe configurarse por inferencia"
