"""Proveedor de la plataforma de licencias (Norte 70) contra un servidor local
que imita las respuestas vistas en la consola «Peticiones API» el 2026-10-13."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from gpmc.agentes.proveedor import (ErrorDeProveedor, ErrorDeRed, NingunProveedor,
                                    RespuestaInvalida, crear_proveedor, hay_proveedor)

ENTORNO = {"GPMC_IA_PROVEEDOR": "norte70", "GPMC_IA_LLAVE": "usuario:secreto",
           "GPMC_IA_USUARIO_ID": "u1"}


class Plataforma:
    """Guion de respuestas de `/openai/query`: (codigo, cuerpo) en orden."""

    def __init__(self, consultas):
        self.consultas = list(consultas)
        self.tokens_emitidos = 0
        self.peticiones = []


def _servidor(plataforma: Plataforma):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _contestar(self, codigo, cuerpo):
            datos = json.dumps(cuerpo).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            cuerpo = json.loads(self.rfile.read(largo) or b"null")
            plataforma.peticiones.append((self.path, dict(self.headers), cuerpo))
            if self.path == "/token/generate":
                plataforma.tokens_emitidos += 1
                return self._contestar(201, {"token": f"jwt{plataforma.tokens_emitidos}"})
            codigo, resp = plataforma.consultas.pop(0)
            self._contestar(codigo, resp)

    srv = HTTPServer(("127.0.0.1", 0), Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def plataforma():
    p = Plataforma([])
    srv = _servidor(p)
    p.entorno = {**ENTORNO, "GPMC_IA_URL": f"http://127.0.0.1:{srv.server_port}"}
    yield p
    srv.shutdown()


def _ok(texto, saldo):
    return 201, {"id_conversation": "c1", "bot_response": texto, "remainingUses": saldo,
                 "alerts": {}}


def test_consulta_completa_y_cuerpo_de_la_peticion(plataforma):
    plataforma.consultas = [_ok('{"a": 1}', 99_000)]
    p = crear_proveedor(entorno=plataforma.entorno)
    r = p.completar("INSTRUCCION", "CONTEXTO", {"type": "object"})
    assert json.loads(r.texto) == {"a": 1} and r.modelo == "norte70"
    ruta_t, cab_t, _ = plataforma.peticiones[0]
    assert ruta_t == "/token/generate" and cab_t["Authorization"].startswith("Basic ")
    ruta, cab, cuerpo = plataforma.peticiones[1]
    assert ruta == "/openai/query" and cab["Authorization"] == "Bearer jwt1"
    assert cuerpo["systemName"] == "Compilador GPM" and cuerpo["id_user"] == "u1"
    assert cuerpo["id_conversation"] is None
    q = cuerpo["user_query"]
    assert q.index("INSTRUCCION") < q.index('"type": "object"') < q.index("CONTEXTO")


def test_no_hereda_el_modelo_de_otro_proveedor(plataforma):
    plataforma.consultas = [_ok("{}", 1)]
    p = crear_proveedor(entorno={**plataforma.entorno, "GPMC_IA_MODELO": "gemini-3.6-flash"})
    assert p.completar("i", "c", {}).modelo == "norte70"


def test_el_token_se_reusa_y_el_consumo_sale_del_saldo(plataforma):
    plataforma.consultas = [_ok("{}", 1000), _ok("{}", 760)]
    p = crear_proveedor(entorno=plataforma.entorno)
    p.completar("i", "c", {})
    assert p.consumo_ultima is None
    p.completar("i", "c", {})
    assert plataforma.tokens_emitidos == 1
    assert p.saldo == 760 and p.consumo_ultima == 240


def test_quita_la_cerca_de_codigo(plataforma):
    plataforma.consultas = [_ok('```json\n{"a": 2}\n```', 1)]
    r = crear_proveedor(entorno=plataforma.entorno).completar("i", "c", {})
    assert json.loads(r.texto) == {"a": 2}


def test_texto_libre_es_respuesta_invalida(plataforma):
    plataforma.consultas = [_ok("Me especializo en denuncias ciudadanas", 1)]
    with pytest.raises(RespuestaInvalida):
        crear_proveedor(entorno=plataforma.entorno).completar("i", "c", {})


def test_sistema_sin_prompt_es_error_de_proveedor(plataforma):
    """Lo que contesta la plataforma si el sistema no tiene «Prompt del Sistema
    (IA)»: no se arregla reintentando."""
    plataforma.consultas = [(400, {"message": "No se ha configurado un prompt para el sistema",
                                   "error": "Bad Request", "statusCode": 400})]
    with pytest.raises(ErrorDeProveedor, match="prompt"):
        crear_proveedor(entorno=plataforma.entorno).completar("i", "c", {})


def test_401_renueva_el_token_una_vez(plataforma):
    plataforma.consultas = [(401, {"message": "Unauthorized"}), _ok("{}", 1)]
    crear_proveedor(entorno=plataforma.entorno).completar("i", "c", {})
    assert plataforma.tokens_emitidos == 2
    assert plataforma.peticiones[-1][1]["Authorization"] == "Bearer jwt2"


def test_5xx_es_error_de_red(plataforma):
    plataforma.consultas = [(503, {"message": "saturado"})]
    with pytest.raises(ErrorDeRed):
        crear_proveedor(entorno=plataforma.entorno).completar("i", "c", {})


def test_sin_servidor_es_error_de_red():
    p = crear_proveedor(entorno={**ENTORNO, "GPMC_IA_URL": "http://127.0.0.1:9"})
    with pytest.raises(ErrorDeRed):
        p.completar("i", "c", {})


def test_faltan_variables_no_hay_proveedor():
    sin_id = {k: v for k, v in ENTORNO.items() if k != "GPMC_IA_USUARIO_ID"}
    assert isinstance(crear_proveedor(entorno=sin_id), NingunProveedor)
    assert isinstance(crear_proveedor(entorno={**ENTORNO, "GPMC_IA_LLAVE": "sin-dos-puntos"}),
                      NingunProveedor)
    assert hay_proveedor(entorno=ENTORNO) is True


def test_norte70_abre_el_candado_de_la_fase3():
    from gpmc.agentes.fase3 import modo_pruebas, puede_generar
    assert puede_generar(ENTORNO) is None
    assert modo_pruebas({**ENTORNO, "GPMC_FASE3_PRUEBAS": "1"}) is False


@pytest.mark.red
@pytest.mark.skipif(not os.environ.get("GPMC_IA_PRUEBA_REAL")
                    or os.environ.get("GPMC_IA_PROVEEDOR") != "norte70",
                    reason="prueba real: GPMC_IA_PRUEBA_REAL=1 y GPMC_IA_PROVEEDOR=norte70")
def test_real_contra_la_plataforma():
    p = crear_proveedor()
    r = p.completar("Contesta la suma que se te pide.", "2+3",
                    {"type": "object", "properties": {"suma": {"type": "integer"}},
                     "required": ["suma"]})
    assert json.loads(r.texto)["suma"] == 5
