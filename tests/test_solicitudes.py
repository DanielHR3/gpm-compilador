"""Solicitudes desde Simplifica: «Enviar al Compilador» y campanita
(spec 2026-11-10-solicitudes-desde-simplifica)."""
from fastapi.testclient import TestClient

from gpmc.web import solicitudes
from gpmc.web.app import crear_app
from tests.test_api import _ENT_OPENAI, _cli_usuarios, _entrar

ENVIO, LECTURA = "envio-123", "lectura-456"
ENT = {**_ENT_OPENAI, "GPMC_TOKEN_ENVIO": ENVIO, "GPMC_TOKEN_SERVICIO": LECTURA}
URL = "/api/v1/solicitudes"
B_ENVIO = {"Authorization": f"Bearer {ENVIO}"}
FICHA = {"ruts_id": "4321", "nombre": "Licencia de funcionamiento", "dependencia": "Secretaría X",
         "enviado_por": "luis", "ruts": {"costo": "$500", "tiempo_entrega": "5 días", "description": "Permite abrir"}}


def _cli(tmp_path, entorno=ENT):
    return TestClient(crear_app(almacen=tmp_path, entorno=entorno))


# --- registro ---

def test_registrar_y_leer_con_la_mas_reciente_primero(tmp_path, monkeypatch):
    monkeypatch.setattr(solicitudes, "ahora", lambda: "2026-11-10T10:00:00")
    solicitudes.registrar(tmp_path, {**FICHA, "ruts_id": "1"})
    monkeypatch.setattr(solicitudes, "ahora", lambda: "2026-11-10T11:00:00")
    solicitudes.registrar(tmp_path, FICHA)
    lista = solicitudes.leer(tmp_path)
    assert [s["ruts_id"] for s in lista] == ["4321", "1"]
    assert lista[0]["nueva"] is True and lista[0]["recibida"] == "2026-11-10T11:00:00"


def test_reenviar_actualiza_y_vuelve_a_marcar_nueva(tmp_path):
    solicitudes.registrar(tmp_path, FICHA)
    solicitudes.marcar_vista(tmp_path, "4321")
    assert solicitudes.leer(tmp_path)[0]["nueva"] is False
    solicitudes.registrar(tmp_path, {**FICHA, "nombre": "Licencia nueva"})
    [s] = solicitudes.leer(tmp_path)
    assert s["nueva"] is True and s["nombre"] == "Licencia nueva"


def test_bytes_rotos_no_revientan_y_se_conservan(tmp_path):
    (tmp_path / solicitudes.ARCHIVO).write_bytes(b"\xff\xfe\n")
    assert solicitudes.leer(tmp_path) == []
    assert solicitudes.registrar(tmp_path, FICHA) is True
    assert b"\xff\xfe" in (tmp_path / solicitudes.ARCHIVO).read_bytes()


def test_la_purga_no_toca_solicitudes(tmp_path):
    import os
    import time
    from gpmc.web.sesiones import _purgar_sesiones
    solicitudes.registrar(tmp_path, FICHA)
    viejo = time.time() - 30 * 86400
    os.utime(tmp_path / solicitudes.ARCHIVO, (viejo, viejo))
    _purgar_sesiones(tmp_path)
    assert (tmp_path / solicitudes.ARCHIVO).exists()


def test_as_is_inicial_trae_frontmatter_y_titulo():
    texto = solicitudes.as_is_inicial({**FICHA, "nombre": 'Licencia "rara"\nmal'})
    assert texto.startswith('---\nruts_id: "4321"\ndependencia: "Secretaría X"\n---\n')
    assert "# Análisis AS-IS — Licencia \"rara\" mal" in texto
    from gpmc.extractores import metadatos
    r = metadatos.extraer(texto)
    assert r.tramite.ruts_id == "4321" and r.tramite.dependencia == "Secretaría X"


# --- POST con token de envío ---

def test_sin_variable_el_envio_no_existe_404(tmp_path):
    r = _cli(tmp_path, {**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": LECTURA}).post(URL, json=FICHA, headers=B_ENVIO)
    assert r.status_code == 404


def test_token_malo_o_el_de_lectura_dan_401(tmp_path):
    c = _cli(tmp_path)
    for h in ({}, {"Authorization": f"Bearer {LECTURA}"}, {"Authorization": "Bearer x"}, {"Authorization": ENVIO}):
        r = c.post(URL, json=FICHA, headers=h)
        assert r.status_code == 401 and r.json() == {"error": "no autorizado"}, h
    assert not (tmp_path / solicitudes.ARCHIVO).exists()


def test_el_token_de_envio_no_lee_el_estado(tmp_path):
    assert _cli(tmp_path).get("/api/v1/expedientes", params={"ruts_id": "4321"}, headers=B_ENVIO).status_code == 401


def test_envio_valido_201_y_queda_registrado(tmp_path):
    r = _cli(tmp_path).post(URL, json=FICHA, headers=B_ENVIO)
    assert r.status_code == 201 and r.json() == {"ok": True}
    [s] = solicitudes.leer(tmp_path)
    assert s["nombre"] == "Licencia de funcionamiento" and s["ruts"]["costo"] == "$500"


def test_envio_invalido_422(tmp_path):
    c = _cli(tmp_path)
    for malo in ({**FICHA, "ruts_id": "4321&x"}, {**FICHA, "ruts_id": ""}, {k: v for k, v in FICHA.items() if k != "nombre"},
                 {**FICHA, "curp": "XXXX"}, {**FICHA, "ruts": {"otra": "x"}}, {**FICHA, "nombre": "   "}):
        assert c.post(URL, json=malo, headers=B_ENVIO).status_code == 422, malo
    assert not (tmp_path / solicitudes.ARCHIVO).exists()


def test_textos_largos_se_recortan(tmp_path):
    _cli(tmp_path).post(URL, json={**FICHA, "nombre": "x" * 900, "ruts": {"description": "d" * 5000}}, headers=B_ENVIO)
    [s] = solicitudes.leer(tmp_path)
    assert len(s["nombre"]) == 300 and len(s["ruts"]["description"]) == 2000


# --- con cuentas de persona ---

def test_persona_ve_la_campanita_marca_vista_y_baja_el_as_is(tmp_path):
    c, usuarios = _cli_usuarios(tmp_path, entorno=ENT)
    TestClient(c.app).post(URL, json=FICHA, headers=B_ENVIO)
    _entrar(c)
    r = c.get(URL)
    assert r.status_code == 200 and r.json()["nuevas"] == 1
    assert r.json()["solicitudes"][0]["ruts_id"] == "4321"
    a = c.get(f"{URL}/4321/as-is")
    assert a.status_code == 200 and 'ruts_id: "4321"' in a.text
    assert "attachment" in a.headers["content-disposition"]
    assert c.post(f"{URL}/4321/vista").status_code == 200
    assert c.get(URL).json()["nuevas"] == 0
    assert c.get(f"{URL}/9999/as-is").status_code == 404
    acciones = [f["accion"] for f in usuarios.auditoria()]
    assert "solicitud.recibir" in acciones
    rec = [f for f in usuarios.auditoria() if f["accion"] == "solicitud.recibir"][0]
    assert rec["usuario"] == "servicio:simplifica" and rec["detalle"] == "4321" and ENVIO not in str(usuarios.auditoria())


def test_sin_sesion_no_se_lee_la_campanita_y_el_token_de_envio_tampoco_abre(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=ENT)
    assert c.get(URL).status_code == 401
    assert c.get(URL, headers=B_ENVIO).status_code == 401
    assert c.post(f"{URL}/4321/vista", headers=B_ENVIO).status_code == 401


def test_una_persona_con_sesion_no_puede_enviar(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=ENT)
    _entrar(c)
    assert c.post(URL, json=FICHA).status_code == 401


# --- Ficha estructurada de Simplifica: requisitos y etapas (M-110, 2026-11-11) -------------

_CON_FICHA = {**FICHA, "requisitos": [
    {"nombre": "CURP", "emisor": "RENAPO (Secretaría de Gobernación)", "tratamiento": "Consultar en línea en vez de pedirlo"},
    {"nombre": "Comprobante de pago", "emisor": "La propia dependencia", "tratamiento": "Conservar"},
    {"nombre": "Formato SUA - IMSS (original)"}],
    "etapas": ["Recepción de documentos", "Revisión", "Entrega"]}


def test_la_ficha_acepta_requisitos_y_etapas_y_sin_ellos_sigue_valiendo():
    f = solicitudes.limpiar(_CON_FICHA)
    assert [r["nombre"] for r in f["requisitos"]] == ["CURP", "Comprobante de pago", "Formato SUA - IMSS (original)"]
    assert f["requisitos"][2] == {"nombre": "Formato SUA - IMSS (original)", "emisor": "", "tratamiento": ""}
    assert f["etapas"] == ["Recepción de documentos", "Revisión", "Entrega"]
    viejo = solicitudes.limpiar(FICHA)                       # el contrato anterior no cambia
    assert viejo["requisitos"] == [] and viejo["etapas"] == []


def test_requisitos_o_etapas_mal_formados_invalidan_la_ficha():
    for malo in ({"requisitos": "CURP"}, {"requisitos": [{"nombre": "x", "curp_real": "y"}]}, {"requisitos": ["CURP"]},
                 {"requisitos": [{"emisor": "sin nombre"}]}, {"etapas": [{"n": 1}]}, {"etapas": "uno"},
                 {"requisitos": [{"nombre": "x"}] * 200}):
        assert solicitudes.limpiar({**FICHA, **malo}) is None, malo


def test_el_as_is_inicial_trae_los_requisitos_como_los_lee_el_compilador():
    from gpmc.extractores.as_is import requisitos_del_as_is
    texto = solicitudes.as_is_inicial(solicitudes.limpiar(_CON_FICHA))
    assert requisitos_del_as_is(texto) == ["CURP", "Comprobante de pago", "Formato SUA, IMSS"]
    assert "RENAPO" in texto and "Consultar en línea en vez de pedirlo" in texto
    assert "1. Recepción de documentos" in texto and "3. Entrega" in texto
    assert texto.startswith('---\nruts_id: "')
    sin = solicitudes.as_is_inicial(solicitudes.limpiar(FICHA))
    assert "Requisitos" not in sin and requisitos_del_as_is(sin) == []


def test_el_envio_con_ficha_estructurada_queda_registrado(tmp_path):
    c = _cli(tmp_path)
    r = c.post(URL, json=_CON_FICHA, headers=B_ENVIO)
    assert r.status_code == 201
    assert solicitudes.buscar(tmp_path, FICHA["ruts_id"])["etapas"] == _CON_FICHA["etapas"]


# --- Seguimiento: el trámite enviado se vuelve expediente ligado (Luis Vera, 2026-11-11) ---
# «Solo vi la notificación, no vi ningún seguimiento de ese trámite.» Su AS-IS no trae
# `ruts_id`, así que el expediente nunca quedaba ligado al trámite que mandó Simplifica.

def test_con_ruts_pone_el_id_sin_tocar_lo_demas():
    assert solicitudes.con_ruts("# Análisis AS-IS — X\n", "4321").startswith('---\nruts_id: "4321"\n---\n# Análisis AS-IS — X')
    con = solicitudes.con_ruts("---\ntipo: expediente\ndependencia: Y\n---\n# AS-IS\n", "4321")
    assert con.startswith('---\nruts_id: "4321"\ntipo: expediente\ndependencia: Y\n---\n# AS-IS')
    ya = "---\nruts_id: \"99\"\n---\n# AS-IS\n"
    assert solicitudes.con_ruts(ya, "4321") == ya                 # el que escribió el analista manda


def test_la_campanita_dice_en_que_etapa_va_cada_tramite(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=ENT)
    TestClient(c.app).post(URL, json=FICHA, headers=B_ENVIO)
    _entrar(c)
    [s] = c.get(URL).json()["solicitudes"]
    assert s["etapa"] == "Por iniciar" and s["entregables"]["as-is"] is None


def test_proponer_desde_la_solicitud_liga_el_expediente_y_avanza_la_etapa(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=ENT)
    TestClient(c.app).post(URL, json=FICHA, headers=B_ENVIO)
    _entrar(c)
    r = c.post("/api/v1/expedientes/proponer", data={"ruts_id": "4321"},
               files={"as_is": ("as-is.md", "# Análisis AS-IS — Licencia\n".encode(), "text/markdown")})
    assert r.status_code in (200, 202)
    sid = r.json()["sid"]
    assert (tmp_path / sid / "Análisis AS-IS.md").read_text(encoding="utf-8").startswith('---\nruts_id: "4321"')
    [s] = c.get(URL).json()["solicitudes"]
    assert s["etapa"] == "AS-IS cargado" and s["entregables"]["as-is"] and not s["nueva"]
    # Lo mismo ve Simplifica por su API de estado.
    e = TestClient(c.app).get("/api/v1/expedientes?ruts_id=4321", headers={"Authorization": f"Bearer {LECTURA}"})
    assert e.json()["expedientes"][0]["entregables"]["as-is"]


def test_un_ruts_id_invalido_al_proponer_da_422(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=ENT)
    _entrar(c)
    r = c.post("/api/v1/expedientes/proponer", data={"ruts_id": "../../x"},
               files={"as_is": ("as-is.md", b"# AS-IS\n", "text/markdown")})
    assert r.status_code == 422


def test_al_resolver_el_tobe_la_etapa_avanza_sin_esperar_al_diccionario(tmp_path):
    from tests.test_fase3 import _TOBE_OK
    c, _ = _cli_usuarios(tmp_path, entorno=ENT)
    TestClient(c.app).post(URL, json=FICHA, headers=B_ENVIO)
    _entrar(c)
    sid = c.post("/api/v1/expedientes/proponer", data={"ruts_id": "4321"},
                 files={"as_is": ("as-is.md", "# Análisis AS-IS — Licencia\n".encode(), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/generados/tobe/subir",
               files={"archivo": ("tobe.md", _TOBE_OK.encode(), "text/markdown")})
    assert r.status_code == 200, r.text
    [s] = c.get(URL).json()["solicitudes"]
    assert s["etapa"] == "TO-BE listo" and s["entregables"]["diccionario"] is None
