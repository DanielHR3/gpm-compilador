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
