import json
from pathlib import Path
from gpmc.web.sesiones import carpeta_de, huecos_vivos, reconocidos_de, escribir_reconocidos


def test_carpeta_de_rechaza_un_sid_invalido(tmp_path):
    assert carpeta_de(tmp_path, "../../etc") is None
    assert carpeta_de(tmp_path, "no-hex") is None
    assert carpeta_de(tmp_path, "a" * 16) is None          # no existe el dir


def test_carpeta_de_acepta_un_sid_valido_y_existente(tmp_path):
    d = tmp_path / ("a" * 16)
    d.mkdir()
    assert carpeta_de(tmp_path, "a" * 16) == d


def test_huecos_vivos_y_reconocidos_ida_y_vuelta(tmp_path):
    d = tmp_path / ("b" * 16)
    d.mkdir()
    (d / "huecos.json").write_text(json.dumps(
        [{"nivel": "falta_dato", "codigo": "META-01", "ubicacion": "metadatos",
          "mensaje": "x", "propuesta": None}]), encoding="utf-8")
    hs = huecos_vivos(d)
    assert len(hs) == 1 and hs[0].codigo == "META-01"

    assert reconocidos_de(d) == set()
    escribir_reconocidos(d, {("DIC-07", "p1")})
    assert reconocidos_de(d) == {("DIC-07", "p1")}


def test_compuertas_json_round_trip(tmp_path):
    from gpmc.web.sesiones import compuertas_de, escribir_compuertas
    assert compuertas_de(tmp_path) == {}
    escribir_compuertas(tmp_path, {"g1": "procede"})
    assert compuertas_de(tmp_path) == {"g1": "procede"}


def test_generados_se_escriben_y_se_leen(tmp_path):
    from gpmc.web.sesiones import escribir_generados, generados_de, ARCHIVO_GENERADOS
    assert generados_de(tmp_path) is None
    escribir_generados(tmp_path, {"estado": "generando", "motivo": None})
    assert (tmp_path / ARCHIVO_GENERADOS).exists()
    assert generados_de(tmp_path) == {"estado": "generando", "motivo": None}


def test_escribir_huecos_usa_el_mismo_json_que_post_expedientes(tmp_path):
    from gpmc.nucleo.huecos import Hueco
    from gpmc.web.sesiones import escribir_huecos
    escribir_huecos(tmp_path, [Hueco("falta_dato", "GEN-01", "requisitos", "m", None)])
    assert [h.codigo for h in huecos_vivos(tmp_path)] == ["GEN-01"]


def test_escribir_generados_es_atomico(tmp_path, monkeypatch):
    """Lo escribe un hilo de BackgroundTasks mientras la SPA lo lee cada 3 s:
    un write_text a medias se leia vacio y daba 500."""
    import os
    from gpmc.web import sesiones
    llamadas = []
    real = os.replace
    monkeypatch.setattr(sesiones.os, "replace", lambda a, b: (llamadas.append((a, b)), real(a, b)))
    sesiones.escribir_generados(tmp_path, {"estado": "listo"})
    assert len(llamadas) == 1 and str(llamadas[0][1]).endswith("generados.json")
    assert sesiones.generados_de(tmp_path) == {"estado": "listo"}
    assert [p.name for p in tmp_path.iterdir()] == ["generados.json"]
