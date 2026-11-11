"""`legible()` decide si una prueba con material real corre o se salta."""
from tests.conftest import legible


def test_una_carpeta_que_se_puede_listar_es_legible(tmp_path):
    # Antes abría la ruta como archivo: con GPMC_WIKI (una carpeta) siempre daba
    # falso y toda prueba que usara el fixture `wiki` se saltaba en silencio.
    assert legible(tmp_path)


def test_un_archivo_que_se_puede_leer_es_legible(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("x")
    assert legible(f)


def test_lo_que_no_existe_no_es_legible(tmp_path):
    assert not legible(tmp_path / "no-existe")
