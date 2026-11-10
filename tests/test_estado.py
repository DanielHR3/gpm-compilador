"""Registro persistente `estado.jsonl`: fecha de cada entregable por `ruts_id`
(spec 2026-11-06-api-de-estado-para-simplifica). Lo lee Simplifica por la API."""
import os
import re

from gpmc.web import estado

SIETE = ["as-is", "to-be", "diccionario", "bpmn", "gpm", "aprobacion", "publicado"]


def test_anotar_crea_la_linea_con_siete_claves_y_solo_la_anotada_tiene_fecha(tmp_path):
    assert estado.anotar(tmp_path, "4321", "as-is", "2026-11-10") is True
    [exp] = estado.consultar(tmp_path, "4321")
    assert list(exp["entregables"]) == SIETE
    assert exp["entregables"]["as-is"] == "2026-11-10"
    assert all(v is None for k, v in exp["entregables"].items() if k != "as-is")


def test_anotar_no_reescribe_una_fecha_ya_puesta(tmp_path):
    estado.anotar(tmp_path, "4321", "as-is", "2026-11-10")
    estado.anotar(tmp_path, "4321", "as-is", "2026-12-01")
    assert estado.consultar(tmp_path, "4321")[0]["entregables"]["as-is"] == "2026-11-10"


def test_anotar_rechaza_ruts_invalido_y_entregable_desconocido(tmp_path):
    for malo in ("", "4321&x=1", "../x", "a b", "1" * 21, None):
        assert estado.anotar(tmp_path, malo, "as-is", "2026-11-10") is False, malo
    assert estado.anotar(tmp_path, "4321", "foo", "2026-11-10") is False
    assert not (tmp_path / estado.ARCHIVO).exists()


def test_consultar_sin_linea_devuelve_lista_vacia(tmp_path):
    assert estado.consultar(tmp_path, "4321") == []
    estado.anotar(tmp_path, "1", "as-is", "2026-11-10")
    assert estado.consultar(tmp_path, "4321") == []


def test_consultar_con_ruts_parecido_no_mezcla(tmp_path):
    estado.anotar(tmp_path, "4321", "as-is", "2026-11-01")
    estado.anotar(tmp_path, "43210", "to-be", "2026-11-02")
    estado.anotar(tmp_path, "4321a", "diccionario", "2026-11-03")
    estado.anotar(tmp_path, "4321A", "gpm", "2026-11-04")
    e = estado.consultar(tmp_path, "4321")[0]["entregables"]
    assert e["as-is"] == "2026-11-01" and e["to-be"] is None and e["diccionario"] is None and e["gpm"] is None
    assert estado.consultar(tmp_path, "4321A")[0]["entregables"]["gpm"] == "2026-11-04"
    assert estado.consultar(tmp_path, "4321a")[0]["entregables"]["gpm"] is None


def test_consultar_actualizado_es_la_fecha_mas_reciente(tmp_path):
    estado.anotar(tmp_path, "4321", "diccionario", "2026-11-09")
    estado.anotar(tmp_path, "4321", "as-is", "2026-11-01")
    [exp] = estado.consultar(tmp_path, "4321")
    assert exp == {"analista": "", "actualizado": "2026-11-09", "entregables": {
        "as-is": "2026-11-01", "to-be": None, "diccionario": "2026-11-09", "bpmn": None,
        "gpm": None, "aprobacion": None, "publicado": None}}


def test_leer_salta_linea_corrupta_y_no_revienta(tmp_path, caplog):
    estado.anotar(tmp_path, "4321", "as-is", "2026-11-10")
    with open(tmp_path / estado.ARCHIVO, "a", encoding="utf-8") as f:
        f.write("{basura\n[1,2]\n{\"ruts_id\": 5}\n")
    with caplog.at_level("WARNING", logger="gpmc.web.estado"):
        lineas = estado.leer(tmp_path)
        assert estado.consultar(tmp_path, "4321")[0]["entregables"]["as-is"] == "2026-11-10"
    assert [l["ruts_id"] for l in lineas] == ["4321"]
    assert any("linea 2" in r.getMessage() for r in caplog.records)


def test_la_purga_de_sesiones_no_toca_estado_jsonl(tmp_path):
    import time
    from gpmc.web.sesiones import _purgar_sesiones
    estado.anotar(tmp_path, "4321", "as-is", "2026-11-10")
    viejo = time.time() - 30 * 86400
    os.utime(tmp_path / estado.ARCHIVO, (viejo, viejo))
    _purgar_sesiones(tmp_path)
    assert (tmp_path / estado.ARCHIVO).exists()


def test_anotar_no_deja_archivo_temporal_y_no_pierde_lo_previo_si_falla_la_escritura(tmp_path, monkeypatch, caplog):
    estado.anotar(tmp_path, "4321", "as-is", "2026-11-10")
    assert not (tmp_path / (estado.ARCHIVO + ".tmp")).exists()

    def revienta(*a, **k):
        raise OSError("disco lleno")
    monkeypatch.setattr(os, "replace", revienta)
    with caplog.at_level("ERROR", logger="gpmc.web.estado"):
        assert estado.anotar(tmp_path, "999", "as-is", "2026-11-10") is False
    monkeypatch.undo()
    assert [l["ruts_id"] for l in estado.leer(tmp_path)] == ["4321"]
    assert not (tmp_path / (estado.ARCHIVO + ".tmp")).exists()


def test_hoy_tiene_formato_de_fecha():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", estado.hoy())


def test_anotar_sin_fecha_usa_hoy(tmp_path, monkeypatch):
    monkeypatch.setattr(estado, "hoy", lambda: "2030-01-02")
    estado.anotar(tmp_path, "4321", "to-be")
    assert estado.consultar(tmp_path, "4321")[0]["entregables"]["to-be"] == "2030-01-02"
