"""Acuerdo entre repos: el cliente real de Sistema-3.0 (`shared/compilador.py`) entiende
la respuesta de `GET /api/v1/expedientes`. Se salta sin SISTEMA3_RAIZ, como las
pruebas de material real: es verificación del contrato, no prueba obligatoria.

El cliente se carga desde su archivo, con un `flask` mínimo de reemplazo (solo
usa `current_app.config` y `current_app.logger`), y su `urlopen` se desvía al
TestClient: así la URL y la cabecera que arma Simplifica son las que llegan aquí."""
import importlib.util
import logging
import os
import sys
import types
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from gpmc.web import estado
from gpmc.web.app import crear_app
from tests.test_api import _ENT_OPENAI
from tests.test_estado_hitos import _subir

RAIZ = os.environ.get("SISTEMA3_RAIZ", "")
CLIENTE = Path(RAIZ) / "shared" / "compilador.py" if RAIZ else None
pytestmark = pytest.mark.skipif(not (CLIENTE and CLIENTE.exists()),
                                reason="sin SISTEMA3_RAIZ o sin shared/compilador.py")
TOKEN = "tok-contrato"
ENVIO = "envio-contrato"


def _cliente_sistema3(monkeypatch, tc: TestClient):
    falso = types.ModuleType("flask")
    falso.current_app = types.SimpleNamespace(
        config={"COMPILADOR_URL": "https://compilador.prueba", "COMPILADOR_TOKEN": TOKEN,
                "COMPILADOR_TOKEN_ENVIO": ENVIO},
        logger=logging.getLogger("sistema3.prueba"))
    monkeypatch.setitem(sys.modules, "flask", falso)
    spec = importlib.util.spec_from_file_location("sistema3_compilador", CLIENTE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def urlopen(peticion, timeout=None):
        u = urlparse(peticion.full_url)
        assert u.scheme == "https" and TOKEN not in peticion.full_url
        if peticion.get_method() == "POST":
            r = tc.post(u.path, content=peticion.data, headers=dict(peticion.header_items()))
        else:
            r = tc.get(u.path + "?" + u.query, headers=dict(peticion.header_items()))
        if r.status_code >= 400:  # como urlopen: cualquier 2xx es éxito
            raise OSError(f"HTTP {r.status_code}")
        return _Resp(r.content)

    monkeypatch.setattr(mod, "urlopen", urlopen)
    return mod


class _Resp:
    def __init__(self, contenido):
        self._c = contenido

    def read(self):
        return self._c

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_sistema3_calcula_diccionario_de_datos_con_as_is_y_diccionario(tmp_path, monkeypatch):
    monkeypatch.setattr(estado, "hoy", lambda: "2026-11-10")
    tc = TestClient(crear_app(almacen=tmp_path, entorno={**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": TOKEN}))
    _subir(tc, to_be=None)
    cli = _cliente_sistema3(monkeypatch, tc)
    r = cli.consultar("4321")
    assert r["error"] is None and r["conectado"] is True
    assert (r["etapa"], r["fecha"]) == ("Diccionario de Datos", "2026-11-10")
    assert r["analista"] == ""


def test_sistema3_ve_por_iniciar_sin_expediente(tmp_path, monkeypatch):
    tc = TestClient(crear_app(almacen=tmp_path, entorno={**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": TOKEN}))
    r = _cliente_sistema3(monkeypatch, tc).consultar("999")
    assert r["error"] is None and r["etapa"] == "Por iniciar"


def test_sistema3_con_token_distinto_muestra_su_aviso_y_no_revienta(tmp_path, monkeypatch):
    tc = TestClient(crear_app(almacen=tmp_path, entorno={**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": "otro"}))
    r = _cliente_sistema3(monkeypatch, tc).consultar("4321")
    assert r["error"] and r["etapa"] is None


def test_sistema3_envia_la_ficha_y_llega_a_la_campanita(tmp_path, monkeypatch):
    from gpmc.web import solicitudes
    ent = {**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": TOKEN, "GPMC_TOKEN_ENVIO": ENVIO}
    tc = TestClient(crear_app(almacen=tmp_path, entorno=ent))
    cli = _cliente_sistema3(monkeypatch, tc)
    tramite = {"ruts_id": "4321", "nombre_tramite": "Licencia", "institucion": "Secretaría X",
               "costo": "$500", "tiempo_resolucion": "5 días", "descripcion": "Abre negocios"}
    ok, mensaje = cli.enviar(tramite, "luis")
    assert ok, mensaje
    [s] = solicitudes.leer(tmp_path)
    assert (s["ruts_id"], s["nombre"], s["enviado_por"], s["nueva"]) == ("4321", "Licencia", "luis", True)
