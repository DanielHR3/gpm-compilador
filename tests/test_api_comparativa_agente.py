# tests/test_api_comparativa_agente.py
"""La comparativa que se completa sola: analizar en segundo plano y descartar."""
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from gpmc.agentes.proveedor import NingunProveedor, ProveedorFalso
from gpmc.web.app import crear_app
from tests.test_agente_comparativa import _EVIDENCIA, _MEJORAS
from tests.test_api_comparativa import _DICC, _metrica
from tests.test_verificar_comparativa import _ASIS, _TOBE

_CON_LICENCIA = {"GPMC_IA_PROVEEDOR": "openai", "GPMC_IA_LLAVE": "k"}


def _cli(tmp_path, respuestas=(), entorno=_CON_LICENCIA, proveedor=None):
    p = proveedor if proveedor is not None else ProveedorFalso(list(respuestas))
    return TestClient(crear_app(almacen=tmp_path, proveedor=p, entorno=entorno)), p


def _sesion(c, con_as_is=True):
    archivos = {"diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown"),
                "to_be": ("tb.md", _TOBE.encode("utf-8"), "text/markdown")}
    if con_as_is:
        archivos["as_is"] = ("as.md", _ASIS.encode("utf-8"), "text/markdown")
    r = c.post("/api/v1/expedientes", files=archivos)
    assert r.status_code == 201, r.text
    return r.json()["sid"]


def _url(sid, resto=""):
    return f"/api/v1/expedientes/{sid}/comparativa{resto}"


def _guardado(tmp_path, sid):
    return json.loads((tmp_path / sid / "comparativa.json").read_text(encoding="utf-8"))


def test_antes_de_analizar_la_comparativa_dice_que_se_puede(tmp_path):
    c, _ = _cli(tmp_path)
    d = c.get(_url(_sesion(c))).json()
    assert d["analisis"] == {"estado": "sin_analizar", "motivo": None, "pasos": [],
                             "puede_analizar": True, "motivo_analizar": None,
                             "pruebas": False, "modelo": "", "terminado": None}
    assert d["mejoras"] == [] and _metrica(d, "visitas")["antes"]["origen"] == "sin_dato"


def test_sin_proveedor_la_pagina_queda_como_antes_y_lo_dice(tmp_path):
    c, _ = _cli(tmp_path, proveedor=NingunProveedor())
    sid = _sesion(c)
    a = c.get(_url(sid)).json()["analisis"]
    assert a["puede_analizar"] is False and "proveedor de IA" in a["motivo_analizar"]
    assert c.post(_url(sid, "/analizar")).status_code == 409


def test_sin_licencia_ni_modo_de_pruebas_no_se_analiza(tmp_path):
    c, p = _cli(tmp_path, [_EVIDENCIA, _MEJORAS],
                entorno={"GPMC_IA_PROVEEDOR": "gemini", "GPMC_IA_LLAVE": "k"})
    sid = _sesion(c)
    assert c.get(_url(sid)).json()["analisis"]["puede_analizar"] is False
    assert c.post(_url(sid, "/analizar")).status_code == 409 and p.llamadas == 0


def test_analizar_completa_las_cifras_y_trae_los_puntos_de_mejora(tmp_path):
    c, p = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])
    sid = _sesion(c)
    antes = {n: (tmp_path / sid / n).read_bytes() for n in ("manifiesto.yaml", "huecos.json")}
    r = c.post(_url(sid, "/analizar"))
    assert (r.status_code, r.json()) == (202, {"estado": "analizando"})
    d = c.get(_url(sid)).json()
    assert (d["analisis"]["estado"], d["analisis"]["modelo"], p.llamadas) == ("lista", "falso", 2)
    assert d["analisis"]["terminado"] and len(d["analisis"]["pasos"]) >= 2
    v = _metrica(d, "visitas")
    assert (v["antes"]["texto"], v["antes"]["origen"], v["despues"]["texto"]) == ("2", "propuesto", "0")
    assert v["porcentaje"] == 100.0 and len(v["propuesta_antes"]["evidencia"]) == 2
    assert _metrica(d, "tiempo")["despues"] == {
        "texto": "2 días hábiles", "numero": 2.0, "unidad": "dia habil", "origen": "propuesto"}
    assert [m["titulo"] for m in d["mejoras"]] == ["Validar la CURP"]
    assert any(h["codigo"] == "CMP-06" for h in d["huecos"])
    # El agente no escribe en el manifiesto ni en los huecos del expediente.
    assert antes == {n: (tmp_path / sid / n).read_bytes() for n in antes}
    assert len(_guardado(tmp_path, sid)["analisis"]["propuestas"]) == 3


def test_lo_que_declara_una_persona_gana_a_lo_propuesto(tmp_path):
    c, _ = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])
    sid = _sesion(c)
    c.post(_url(sid, "/analizar"))
    r = c.post(_url(sid, "/declarar"), json={"clave": "visitas", "antes": "5", "despues": ""})
    v = _metrica(r.json(), "visitas")
    assert (v["antes"]["texto"], v["antes"]["origen"]) == ("5", "declarado")
    assert v["propuesta_antes"] is None and v["despues"]["origen"] == "propuesto"
    # Declarar no borra el analisis guardado.
    assert r.json()["analisis"]["estado"] == "lista" and len(r.json()["mejoras"]) == 1


def test_descartar_un_punto_de_mejora_se_guarda_y_se_puede_deshacer(tmp_path):
    c, _ = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])
    sid = _sesion(c)
    c.post(_url(sid, "/analizar"))
    mid = c.get(_url(sid)).json()["mejoras"][0]["id"]
    r = c.post(_url(sid, f"/mejoras/{mid}/descartar"), json={"descartada": True})
    assert r.status_code == 200 and r.json()["mejoras"][0]["descartada"] is True
    assert c.get(_url(sid)).json()["mejoras"][0]["descartada"] is True
    r = c.post(_url(sid, f"/mejoras/{mid}/descartar"), json={"descartada": False})
    assert r.json()["mejoras"][0]["descartada"] is False
    assert c.post(_url(sid, "/mejoras/noexiste/descartar"),
                  json={"descartada": True}).status_code == 404


def test_volver_a_analizar_no_resucita_lo_descartado(tmp_path):
    c, p = _cli(tmp_path, [_EVIDENCIA, _MEJORAS, _EVIDENCIA, _MEJORAS])
    sid = _sesion(c)
    c.post(_url(sid, "/analizar"))
    mid = c.get(_url(sid)).json()["mejoras"][0]["id"]
    c.post(_url(sid, f"/mejoras/{mid}/descartar"), json={"descartada": True})
    assert c.post(_url(sid, "/analizar")).status_code == 202
    d = c.get(_url(sid)).json()
    assert p.llamadas == 4 and d["mejoras"][0]["descartada"] is True


def test_un_analisis_que_falla_no_borra_el_anterior(tmp_path, monkeypatch):
    from gpmc.agentes import comparativa as agente
    monkeypatch.setattr(agente, "ESPERAS_REINTENTO", (0.0, 0.0))
    c, _ = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])       # la segunda corrida se queda sin guion
    sid = _sesion(c)
    c.post(_url(sid, "/analizar"))
    c.post(_url(sid, "/analizar"))
    d = c.get(_url(sid)).json()
    assert (d["analisis"]["estado"], d["analisis"]["motivo"]) == ("error", agente.MOTIVO_RED)
    assert _metrica(d, "visitas")["antes"]["origen"] == "propuesto" and len(d["mejoras"]) == 1


def test_si_ya_esta_analizando_no_se_lanza_otra_vez(tmp_path):
    c, p = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])
    sid = _sesion(c)
    (tmp_path / sid / "comparativa.json").write_text(json.dumps({"analisis": {
        "estado": "analizando", "iniciado": datetime.now(timezone.utc).isoformat()}}),
        encoding="utf-8")
    assert c.post(_url(sid, "/analizar")).status_code == 202 and p.llamadas == 0
    assert c.get(_url(sid)).json()["analisis"]["estado"] == "analizando"


def test_un_analizando_viejo_se_lee_como_interrumpido(tmp_path):
    c, _ = _cli(tmp_path)
    sid = _sesion(c)
    viejo = (datetime.now(timezone.utc) - timedelta(minutes=21)).isoformat()
    (tmp_path / sid / "comparativa.json").write_text(json.dumps({"analisis": {
        "estado": "analizando", "iniciado": viejo}}), encoding="utf-8")
    a = c.get(_url(sid)).json()["analisis"]
    assert a["estado"] == "error" and "interrumpió" in a["motivo"]


def test_sin_as_is_no_hay_que_analizar_y_sesion_inexistente_da_404(tmp_path):
    c, p = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])
    assert c.post(_url(_sesion(c, con_as_is=False), "/analizar")).status_code == 409
    assert p.llamadas == 0
    base = "/api/v1/expedientes/0123456789abcdef/comparativa"
    assert c.post(base + "/analizar").status_code == 404
    assert c.post(base + "/mejoras/abc/descartar", json={"descartada": True}).status_code == 404


def test_un_analisis_guardado_roto_no_tumba_la_lectura(tmp_path):
    c, _ = _cli(tmp_path)
    sid = _sesion(c)
    (tmp_path / sid / "comparativa.json").write_text(json.dumps({"analisis": {
        "estado": "lista", "propuestas": "no es lista", "mejoras": [3, {"id": "x"}]}}),
        encoding="utf-8")
    d = c.get(_url(sid)).json()
    assert d["analisis"]["estado"] == "lista" and d["mejoras"] == []


def test_el_documento_descargable_lleva_la_evidencia_y_las_mejoras_vivas(tmp_path):
    c, _ = _cli(tmp_path, [_EVIDENCIA, _MEJORAS])
    sid = _sesion(c)
    c.post(_url(sid, "/analizar"))
    html = c.get(_url(sid, "/documento")).text
    assert "propuesto por el agente" in html and "Usuario lo lleva a Ventanilla" in html
    assert "Qué más se puede simplificar" in html and "Validar la CURP" in html
    mid = c.get(_url(sid)).json()["mejoras"][0]["id"]
    c.post(_url(sid, f"/mejoras/{mid}/descartar"), json={"descartada": True})
    assert "Validar la CURP" not in c.get(_url(sid, "/documento")).text


def test_analizar_y_descartar_quedan_en_la_auditoria(tmp_path, monkeypatch):
    from gpmc.agentes import comparativa as agente
    from tests.test_api import _cli_usuarios, _entrar
    monkeypatch.setattr(agente, "ESPERAS_REINTENTO", (0.0, 0.0))
    c, usuarios = _cli_usuarios(tmp_path)
    _entrar(c)
    sid = _sesion(c)
    c.post(_url(sid, "/analizar"))
    c.post(_url(sid, "/mejoras/abc/descartar"), json={"descartada": True})
    acciones = {f["accion"] for f in usuarios.auditoria() if f["accion"].startswith("comparativa.")}
    assert acciones == {"comparativa.analizar", "comparativa.descartar"}
