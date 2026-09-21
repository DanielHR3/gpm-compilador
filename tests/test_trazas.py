"""Las trazas del asistente: que una anomalia se pueda LEER despues.

Hasta el 2026-09-21 el servicio corria con `log_level="warning"`, sin fecha en
ninguna linea y sin `logging` en el codigo: `servidor.log` tenia 17 lineas tras
un mes en marcha y decia que el servicio habia arrancado siete veces, pero no
cuando ni por que se cayo cada vez.
"""
import logging
import logging.config
import re

import pytest

from gpmc.web.trazas import config_de_logs

_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


@pytest.fixture(autouse=True)
def _logging_limpio():
    """`dictConfig` es estado global: se cierran los manejadores al terminar
    para no dejar archivos abiertos ni contaminar otras pruebas."""
    yield
    for nombre in ("gpmc", "uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(nombre)
        for h in list(lg.handlers):
            h.close()
            lg.removeHandler(h)
        # `dictConfig` les quita la propagacion; sin devolverla, las pruebas
        # que leen el registro con `caplog` dejarian de ver nada segun el orden.
        lg.propagate, lg.disabled = True, False
        lg.setLevel(logging.NOTSET)


def _lineas(ruta):
    for h in logging.getLogger("gpmc").handlers:
        h.flush()
    return ruta.read_text(encoding="utf-8").splitlines()


def test_cada_linea_lleva_fecha_y_hora(tmp_path):
    archivo = tmp_path / "asistente.log"
    logging.config.dictConfig(config_de_logs(archivo=archivo))
    logging.getLogger("gpmc.web").info("expediente extraido")
    (linea,) = _lineas(archivo)
    assert _FECHA.match(linea), linea
    assert "INFO" in linea and "gpmc.web" in linea and "expediente extraido" in linea


def test_las_peticiones_quedan_registradas_con_su_codigo(tmp_path):
    # Asi escribe uvicorn cada peticion. Con `log_level="warning"` no quedaba
    # ninguna: ni quien subio que, ni un 422, ni una carga lenta.
    archivo = tmp_path / "asistente.log"
    logging.config.dictConfig(config_de_logs(archivo=archivo))
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "192.168.1.20:5000", "POST", "/api/v1/expedientes", "1.1", 422)
    (linea,) = _lineas(archivo)
    assert _FECHA.match(linea) and "POST /api/v1/expedientes" in linea and "422" in linea


def test_un_error_de_uvicorn_tambien_lleva_fecha(tmp_path):
    # Un 500 ya dejaba su traza, pero sin hora: no se podia casar con nada.
    archivo = tmp_path / "asistente.log"
    logging.config.dictConfig(config_de_logs(archivo=archivo))
    logging.getLogger("uvicorn.error").error("Exception in ASGI application")
    assert _FECHA.match(_lineas(archivo)[0])


def test_el_archivo_rota_y_no_crece_sin_limite(tmp_path):
    # launchd no rota. Con las peticiones registradas, un archivo sin tope
    # acabaria llenando el disco de la maquina que sirve al equipo.
    archivo = tmp_path / "asistente.log"
    logging.config.dictConfig(config_de_logs(archivo=archivo, max_bytes=2000, respaldos=2))
    lg = logging.getLogger("gpmc.web")
    for i in range(400):
        lg.info("linea de relleno numero %d", i)
    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert nombres == ["asistente.log", "asistente.log.1", "asistente.log.2"], nombres
    assert all(p.stat().st_size <= 2200 for p in tmp_path.iterdir())


def test_sin_archivo_las_lineas_van_a_stderr(tmp_path, capsys):
    # El doble clic de `Abrir Compilador GPM.command` y el desarrollo: sin ruta,
    # nada se escribe en disco y la fecha sigue estando.
    logging.config.dictConfig(config_de_logs())
    logging.getLogger("gpmc.web").warning("sin archivo")
    err = capsys.readouterr().err
    assert _FECHA.match(err) and "sin archivo" in err
    assert list(tmp_path.iterdir()) == []


def test_el_nivel_filtra(tmp_path):
    archivo = tmp_path / "asistente.log"
    logging.config.dictConfig(config_de_logs(nivel="WARNING", archivo=archivo))
    lg = logging.getLogger("gpmc.web")
    lg.info("esto no")
    lg.warning("esto si")
    assert [("esto si" in l) for l in _lineas(archivo)] == [True]


def test_un_nivel_mal_escrito_no_tumba_el_arranque(tmp_path):
    # Viene de una variable de entorno que escribe una persona. Un servicio que
    # no arranca por una errata en el nivel de log seria el colmo.
    archivo = tmp_path / "asistente.log"
    logging.config.dictConfig(config_de_logs(nivel="ruidoso", archivo=archivo))
    logging.getLogger("gpmc.web").info("cae a INFO")
    assert "cae a INFO" in _lineas(archivo)[0]
