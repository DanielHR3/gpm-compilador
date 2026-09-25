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
    almacen.vaciar()
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
    almacen.vaciar()
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


# --- roles, registro pendiente y recuperacion (decisiones del 2026-09-25, tarde) -------

@pytest.mark.parametrize("nombre,almacen", list(_almacenes()), ids=lambda x: x if isinstance(x, str) else "")
def test_un_registro_queda_pendiente_y_no_entra_hasta_que_el_superusuario_lo_aprueba(nombre, almacen):
    almacen.vaciar()
    almacen.alta("daniel.hernandezr@hidalgo.gob.mx", "Daniel", "DGT", "Secreta-123", rol="admin")
    u = almacen.alta("luis.vera@hidalgo.gob.mx", "Luis", "DSA", "Otra-456", estado="pendiente")
    assert (u.rol, u.estado, u.activo) == ("analista", "pendiente", False)
    assert almacen.autenticar("luis.vera@hidalgo.gob.mx", "Otra-456") is None
    assert [x.correo for x in almacen.usuarios(estado="pendiente")] == ["luis.vera@hidalgo.gob.mx"]
    almacen.aprobar("luis.vera@hidalgo.gob.mx")
    u = almacen.autenticar("luis.vera@hidalgo.gob.mx", "Otra-456")
    assert u is not None and u.estado == "activo" and u.rol == "analista"
    admin = almacen.autenticar("daniel.hernandezr@hidalgo.gob.mx", "Secreta-123")
    assert admin is not None and admin.rol == "admin"
    almacen.cambiar_rol("luis.vera@hidalgo.gob.mx", "admin")
    assert almacen.por_correo("luis.vera@hidalgo.gob.mx").rol == "admin"
    almacen.desactivar("luis.vera@hidalgo.gob.mx")
    assert almacen.por_correo("luis.vera@hidalgo.gob.mx").estado == "inactivo"
    assert almacen.autenticar("luis.vera@hidalgo.gob.mx", "Otra-456") is None
    assert almacen.por_correo("nadie@hidalgo.gob.mx") is None


@pytest.mark.parametrize("nombre,almacen", list(_almacenes()), ids=lambda x: x if isinstance(x, str) else "")
def test_la_recuperacion_es_un_token_de_un_solo_uso_que_caduca(nombre, almacen):
    almacen.vaciar()
    from gpmc.web.usuarios import verificar_contrasena
    almacen.alta("daniel.hernandezr@hidalgo.gob.mx", "Daniel", "DGT", "Secreta-123")
    t = almacen.crear_recuperacion("daniel.hernandezr@hidalgo.gob.mx", ahora=_T0)
    assert len(t) >= 32
    assert almacen.consumir_recuperacion("basura", ahora=_T0) is None
    assert almacen.consumir_recuperacion(t, ahora=_T0 + timedelta(hours=1, seconds=1)) is None   # caduco
    t2 = almacen.crear_recuperacion("daniel.hernandezr@hidalgo.gob.mx", ahora=_T0)
    assert almacen.consumir_recuperacion(t2, ahora=_T0 + timedelta(minutes=30)) == "daniel.hernandezr@hidalgo.gob.mx"
    assert almacen.consumir_recuperacion(t2, ahora=_T0 + timedelta(minutes=31)) is None          # ya usado
    almacen.cambiar_contrasena("daniel.hernandezr@hidalgo.gob.mx", "Nueva-789")
    assert almacen.autenticar("daniel.hernandezr@hidalgo.gob.mx", "Secreta-123") is None
    assert almacen.autenticar("daniel.hernandezr@hidalgo.gob.mx", "Nueva-789") is not None
    assert almacen.crear_recuperacion("nadie@hidalgo.gob.mx", ahora=_T0) is None


def test_el_correo_institucional_se_valida_por_dominio():
    from gpmc.web.usuarios import correo_institucional
    assert correo_institucional("Luis.Vera@Hidalgo.gob.mx", "hidalgo.gob.mx") == "luis.vera@hidalgo.gob.mx"
    assert correo_institucional("luis@gmail.com", "hidalgo.gob.mx") is None
    assert correo_institucional("luis@hidalgo.gob.mx.evil.com", "hidalgo.gob.mx") is None
    assert correo_institucional("sin-arroba", "hidalgo.gob.mx") is None
    assert correo_institucional("  ", "hidalgo.gob.mx") is None


def test_el_correo_smtp_se_configura_solo_con_host_y_el_falso_guarda_lo_enviado():
    from gpmc.web.correo import CorreoEnMemoria, correo_desde_entorno
    assert correo_desde_entorno({}) is None
    c = correo_desde_entorno({"GPMC_SMTP_HOST": "smtp.hidalgo.gob.mx", "GPMC_SMTP_PUERTO": "587",
                              "GPMC_SMTP_USUARIO": "u", "GPMC_SMTP_CLAVE": "k",
                              "GPMC_SMTP_REMITENTE": "compilador@hidalgo.gob.mx"})
    assert c is not None and c.remitente == "compilador@hidalgo.gob.mx" and c.puerto == 587
    f = CorreoEnMemoria()
    f.enviar("luis.vera@hidalgo.gob.mx", "Asunto", "Cuerpo")
    assert f.enviados == [{"para": "luis.vera@hidalgo.gob.mx", "asunto": "Asunto", "texto": "Cuerpo"}]
