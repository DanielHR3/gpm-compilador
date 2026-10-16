# tests/test_auditoria.py
"""Lo que se consulta de la bitacora de acciones (2026-10-16): el CSV para la
auditoria interna y el filtro de errores. El registro ya existia (spec
2026-09-25); faltaba la mitad que se ve."""
import pytest

from gpmc.web.auditoria import COLUMNAS, a_csv, es_error
from tests.test_usuarios import _almacenes


def test_el_csv_lleva_las_siete_columnas_y_escapa_comas_y_comillas():
    filas = [{"fecha": "2026-10-16T18:00:00+00:00", "usuario": "luis.vera@hidalgo.gob.mx", "dependencia": "DSA",
              "accion": "hueco.resolver", "sid": "a" * 16, "detalle": 'DIC-08, p1::x "largo"', "ip": "10.0.0.9"}]
    csv = a_csv(filas)
    lineas = csv.splitlines()
    assert lineas[0] == ",".join(COLUMNAS)
    assert lineas[1] == '2026-10-16T18:00:00+00:00,luis.vera@hidalgo.gob.mx,DSA,hueco.resolver,' + "a" * 16 + ',"DIC-08, p1::x ""largo""",10.0.0.9'
    assert csv.startswith("﻿") is False and csv.endswith("\n")


def test_un_error_es_un_fallo_del_servidor_o_una_accion_que_el_servidor_rechazo():
    assert es_error({"accion": "error.servidor", "detalle": "RuntimeError en GET /api/v1/x (500)"})
    assert es_error({"accion": "gpm.descargar", "detalle": "produccion (409)"})
    assert es_error({"accion": "sesion.fallo", "detalle": ""})
    assert not es_error({"accion": "gpm.descargar", "detalle": "produccion"})
    assert not es_error({"accion": "hueco.resolver", "detalle": "DIC-08"})


@pytest.mark.parametrize("nombre,almacen", list(_almacenes()), ids=lambda x: x if isinstance(x, str) else "")
def test_el_almacen_filtra_solo_errores(nombre, almacen):
    almacen.vaciar()
    almacen.auditar("luis.vera@hidalgo.gob.mx", "DSA", "hueco.resolver", "a" * 16, "DIC-08", "10.0.0.9")
    almacen.auditar("luis.vera@hidalgo.gob.mx", "DSA", "gpm.descargar", "a" * 16, "produccion (409)", "10.0.0.9")
    almacen.auditar("anonimo", "", "error.servidor", None, "RuntimeError en GET /api/v1/x (500)", "10.0.0.1")
    almacen.auditar("x@hidalgo.gob.mx", "", "sesion.fallo", None, "", "10.0.0.2")
    assert [f["accion"] for f in almacen.auditoria(solo_errores=True)] == ["sesion.fallo", "error.servidor", "gpm.descargar"]
    assert len(almacen.auditoria()) == 4
