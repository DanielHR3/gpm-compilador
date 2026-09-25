"""Usuarios, contraseñas, JWT y bitácora de acciones (spec 2026-09-25).

El almacén en memoria es el que ven las pruebas de la API; el de Postgres se
prueba solo con `GPMC_BD_PRUEBAS` (DSN), como el material real.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest


# --- contraseñas -------------------------------------------------------------------

def test_la_contrasena_se_guarda_cifrada_con_sal_y_se_verifica():
    from gpmc.web.usuarios import hash_contrasena, verificar_contrasena
    h1, h2 = hash_contrasena("Secreta-123"), hash_contrasena("Secreta-123")
    assert h1 != h2 and "Secreta" not in h1 and h1.startswith("scrypt$")
    assert verificar_contrasena("Secreta-123", h1) and verificar_contrasena("Secreta-123", h2)
    assert not verificar_contrasena("secreta-123", h1)
    assert not verificar_contrasena("Secreta-123", "basura")


# --- JWT --------------------------------------------------------------------------

_T0 = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def test_el_token_lleva_correo_nombre_y_dependencia_y_vence_a_las_8_horas():
    from gpmc.web.usuarios import emitir_token, leer_token
    t = emitir_token("s3cr3to", "daniel.hernandezr@hidalgo.gob.mx", "Daniel", "DGT", ahora=_T0)
    assert t.count(".") == 2
    c = leer_token("s3cr3to", t, ahora=_T0 + timedelta(hours=7, minutes=59))
    assert c == {"sub": "daniel.hernandezr@hidalgo.gob.mx", "nombre": "Daniel", "dependencia": "DGT",
                 "iat": int(_T0.timestamp()), "exp": int((_T0 + timedelta(hours=8)).timestamp())}
    assert leer_token("s3cr3to", t, ahora=_T0 + timedelta(hours=8, seconds=1)) is None


def test_un_token_manipulado_o_con_otro_secreto_no_vale():
    from gpmc.web.usuarios import emitir_token, leer_token
    t = emitir_token("s3cr3to", "luis.vera@hidalgo.gob.mx", "Luis", "DSA", ahora=_T0)
    assert leer_token("otro", t, ahora=_T0) is None
    cab, cuerpo, firma = t.split(".")
    assert leer_token("s3cr3to", f"{cab}.{cuerpo}x.{firma}", ahora=_T0) is None
    assert leer_token("s3cr3to", "no.es.token", ahora=_T0) is None
    assert leer_token("s3cr3to", "", ahora=_T0) is None


# --- almacén: contrato comun ----------------------------------------------------------

def _almacenes():
    from gpmc.web.usuarios import AlmacenEnMemoria
    yield "memoria", AlmacenEnMemoria()
    dsn = os.environ.get("GPMC_BD_PRUEBAS")
    if dsn:
        from gpmc.web.usuarios import AlmacenPostgres
        a = AlmacenPostgres(dsn)
        a.crear_tablas()
        a.vaciar()            # solo existe para pruebas
        yield "postgres", a


@pytest.mark.parametrize("nombre,almacen", list(_almacenes()), ids=lambda x: x if isinstance(x, str) else "")
def test_alta_autenticar_y_baja(nombre, almacen):
    almacen.alta("daniel.hernandezr@hidalgo.gob.mx", "Daniel", "DGT", "Secreta-123")
    u = almacen.autenticar("daniel.hernandezr@hidalgo.gob.mx", "Secreta-123")
    assert u is not None and (u.correo, u.nombre, u.dependencia, u.activo) == (
        "daniel.hernandezr@hidalgo.gob.mx", "Daniel", "DGT", True)
    assert almacen.autenticar("Daniel.HernandezR@hidalgo.gob.mx", "Secreta-123") is not None  # el correo no distingue mayusculas
    assert almacen.autenticar("daniel.hernandezr@hidalgo.gob.mx", "mal") is None
    assert almacen.autenticar("nadie@hidalgo.gob.mx", "Secreta-123") is None
    with pytest.raises(ValueError):
        almacen.alta("daniel.hernandezr@hidalgo.gob.mx", "Otro", "DSA", "x")   # correo unico
    almacen.desactivar("daniel.hernandezr@hidalgo.gob.mx")
    assert almacen.autenticar("daniel.hernandezr@hidalgo.gob.mx", "Secreta-123") is None
    assert [(u.correo, u.activo) for u in almacen.usuarios()] == [("daniel.hernandezr@hidalgo.gob.mx", False)]


@pytest.mark.parametrize("nombre,almacen", list(_almacenes()), ids=lambda x: x if isinstance(x, str) else "")
def test_la_auditoria_registra_y_se_consulta_por_sesion_usuario_y_fecha(nombre, almacen):
    almacen.auditar("daniel.hernandezr@hidalgo.gob.mx", "DGT", "expediente.subir", "a" * 16, "3 archivos", "192.168.1.5")
    almacen.auditar("luis.vera@hidalgo.gob.mx", "DSA", "hueco.resolver", "a" * 16, "DIC-08 p1::x", "192.168.1.9")
    almacen.auditar("luis.vera@hidalgo.gob.mx", "DSA", "gpm.descargar", "b" * 16, "produccion", "192.168.1.9")
    todas = almacen.auditoria()
    assert [f["accion"] for f in todas] == ["gpm.descargar", "hueco.resolver", "expediente.subir"]  # mas reciente primero
    assert all(f["fecha"] and f["usuario"] and f["dependencia"] for f in todas)
    assert [f["accion"] for f in almacen.auditoria(sid="a" * 16)] == ["hueco.resolver", "expediente.subir"]
    assert [f["sid"] for f in almacen.auditoria(usuario="luis.vera@hidalgo.gob.mx")] == ["b" * 16, "a" * 16]
    assert almacen.auditoria(desde=datetime.now(timezone.utc) + timedelta(minutes=1)) == []
    assert len(almacen.auditoria(limite=1)) == 1
    assert todas[0]["ip"] == "192.168.1.9" and todas[0]["detalle"] == "produccion"
