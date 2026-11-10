"""GET /api/v1/expedientes?ruts_id=… para Simplifica, con token de servicio
(spec 2026-11-06-api-de-estado-para-simplifica)."""
from fastapi.testclient import TestClient

from gpmc.web import estado
from gpmc.web.app import crear_app
from tests.test_api import _ENT_OPENAI, _cli_usuarios, _entrar
from tests.test_estado_hitos import _ASIS_RUTS, _subir

TOKEN = "tok-123"
CON_TOKEN = {**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": TOKEN}
URL = "/api/v1/expedientes"
BEARER = {"Authorization": f"Bearer {TOKEN}"}


def _cli(tmp_path, entorno=CON_TOKEN):
    return TestClient(crear_app(almacen=tmp_path, entorno=entorno))


def test_sin_variable_de_token_la_ruta_no_existe_404(tmp_path):
    for ent in (_ENT_OPENAI, {**_ENT_OPENAI, "GPMC_TOKEN_SERVICIO": "  "}):
        r = _cli(tmp_path, ent).get(URL, params={"ruts_id": "4321"}, headers=BEARER)
        assert r.status_code == 404 and r.json() == {"error": "no encontrado"}


def test_sin_token_o_con_token_malo_o_sin_bearer_da_401_con_el_mismo_cuerpo(tmp_path):
    c = _cli(tmp_path)
    for h in ({}, {"Authorization": ""}, {"Authorization": "Bearer "}, {"Authorization": TOKEN},
              {"Authorization": f"Basic {TOKEN}"}, {"Authorization": "Bearer tok-1234"},
              {"Authorization": "Bearer tok-12"}):
        r = c.get(URL, params={"ruts_id": "4321"}, headers=h)
        assert r.status_code == 401, h
        assert r.json() == {"error": "no autorizado"}, h


def test_el_token_no_se_acepta_en_la_url(tmp_path):
    r = _cli(tmp_path).get(URL, params={"ruts_id": "4321", "token": TOKEN})
    assert r.status_code == 401


def test_con_token_valido_y_sin_expediente_devuelve_lista_vacia(tmp_path):
    r = _cli(tmp_path).get(URL, params={"ruts_id": "4321"}, headers=BEARER)
    assert r.status_code == 200 and r.json() == {"expedientes": []}


def test_contrato_exacto_siete_claves_y_nulos(tmp_path, monkeypatch):
    monkeypatch.setattr(estado, "hoy", lambda: "2026-11-10")
    c = _cli(tmp_path)
    _subir(c, to_be=None)
    r = c.get(URL, params={"ruts_id": "4321"}, headers=BEARER)
    assert r.status_code == 200
    assert r.json() == {"expedientes": [{"analista": "", "actualizado": "2026-11-10", "entregables": {
        "as-is": "2026-11-10", "to-be": None, "diccionario": "2026-11-10", "bpmn": None,
        "gpm": None, "aprobacion": None, "publicado": None}}]}
    assert list(r.json()["expedientes"][0]["entregables"]) == [
        "as-is", "to-be", "diccionario", "bpmn", "gpm", "aprobacion", "publicado"]


def test_ruts_id_ausente_o_invalido_da_422(tmp_path):
    c = _cli(tmp_path)
    assert c.get(URL, headers=BEARER).status_code == 422
    for malo in ("", "4321&x=1", "a b", "1" * 21, "../x", " 4321"):
        assert c.get(URL, params={"ruts_id": malo}, headers=BEARER).status_code == 422, malo


def test_la_respuesta_no_trae_campos_del_ciudadano(tmp_path):
    c = _cli(tmp_path)
    _subir(c)
    [exp] = c.get(URL, params={"ruts_id": "4321"}, headers=BEARER).json()["expedientes"]
    assert set(exp) == {"analista", "actualizado", "entregables"}
    assert "curp" not in str(exp).lower()


def test_registro_corrupto_no_da_500(tmp_path):
    (tmp_path / estado.ARCHIVO).write_text("{basura\n\x00\n", encoding="utf-8")
    r = _cli(tmp_path).get(URL, params={"ruts_id": "4321"}, headers=BEARER)
    assert r.status_code == 200 and r.json() == {"expedientes": []}


def test_post_expedientes_sigue_funcionando_igual(tmp_path):
    c = _cli(tmp_path)
    sid = _subir(c)
    assert len(sid) == 16


def test_sin_almacen_de_usuarios_no_se_audita_y_responde_igual(tmp_path):
    r = _cli(tmp_path).get(URL, params={"ruts_id": "4321"}, headers=BEARER)
    assert r.status_code == 200


# --- con cuentas de persona instaladas ---

def test_con_usuarios_el_token_de_servicio_abre_la_ruta(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=CON_TOKEN)
    assert c.get(URL, params={"ruts_id": "4321"}, headers=BEARER).status_code == 200
    assert c.get(URL, params={"ruts_id": "4321"}).status_code == 401


def test_un_jwt_de_persona_en_la_cabecera_no_abre_la_ruta(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=CON_TOKEN)
    token_persona = _entrar(c).json()["token"]
    c2 = TestClient(c.app)
    r = c2.get(URL, params={"ruts_id": "4321"}, headers={"Authorization": f"Bearer {token_persona}"})
    assert r.status_code == 401 and r.json() == {"error": "no autorizado"}
    # ni con la cookie de sesión de la persona
    assert c.get(URL, params={"ruts_id": "4321"}).status_code == 401


def test_el_token_de_servicio_no_abre_otras_rutas(tmp_path):
    c, _ = _cli_usuarios(tmp_path, entorno=CON_TOKEN)
    assert c.get("/api/v1/historial", headers=BEARER).status_code == 401
    assert c.get(URL + "/" + "a" * 16, headers=BEARER).status_code == 401
    assert c.post(URL, headers=BEARER, files={"diccionario": ("d.md", b"x", "text/markdown")}).status_code == 401


def test_la_consulta_con_token_valido_queda_auditada_como_servicio_simplifica(tmp_path):
    c, usuarios = _cli_usuarios(tmp_path, entorno=CON_TOKEN)
    c.get(URL, params={"ruts_id": "4321"}, headers=BEARER)
    filas = [f for f in usuarios.auditoria() if f["accion"] == "estado.consultar"]
    assert len(filas) == 1
    assert filas[0]["usuario"] == "servicio:simplifica" and "4321" in filas[0]["detalle"]
    assert TOKEN not in str(usuarios.auditoria())
    c.get(URL, params={"ruts_id": "4321"}, headers={"Authorization": "Bearer malo"})
    assert len([f for f in usuarios.auditoria() if f["accion"] == "estado.consultar"]) == 1


def test_la_auditoria_solo_lleva_codigo_si_se_rechazo_y_no_guarda_texto_libre(tmp_path):
    c, usuarios = _cli_usuarios(tmp_path, entorno=CON_TOKEN)
    c.get(URL, params={"ruts_id": "4321"}, headers=BEARER)
    c.get(URL, params={"ruts_id": "<script>"}, headers=BEARER)
    detalles = sorted(f["detalle"] for f in usuarios.auditoria() if f["accion"] == "estado.consultar")
    assert detalles == ["4321", "ruts_id invalido (422)"]
