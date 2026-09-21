"""Configuracion del registro (log) del asistente web.

Una sola definicion para las lineas propias (`gpmc.*`) y para las de uvicorn
(arranque, errores y peticiones): todas con fecha y hora, porque una anomalia
sin hora no se puede casar con nada.

Con `archivo` se escribe en un archivo que ROTA. launchd redirige stdout/stderr
a `servidor.log` y mantiene ese descriptor abierto, asi que ese archivo no se
puede rotar desde dentro: por eso el registro va aparte y `servidor.log` se
queda solo con el arranque y con lo que reviente antes de configurar nada.
Sin `archivo` (desarrollo, el doble clic del `.command`) va a stderr.

Que se escribe: identificadores y conteos —sesion, codigo de hueco, cuantos
bloquean—. NUNCA el contenido de un expediente.
"""
from pathlib import Path
from typing import Optional

NIVELES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
FORMATO = "%(asctime)s %(levelname)-7s %(name)s  %(message)s"
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

# 5 MB por archivo y cinco respaldos: 30 MB de tope en la maquina que sirve al
# equipo. A ~150 bytes por peticion son del orden de 200 000 peticiones.
MAX_BYTES = 5 * 1024 * 1024
RESPALDOS = 5


def nivel_valido(nivel: Optional[str]) -> str:
    """El nivel viene de una variable de entorno que escribe una persona: una
    errata cae a INFO en vez de impedir que el servicio arranque."""
    n = (nivel or "").strip().upper()
    return n if n in NIVELES else "INFO"


def config_de_logs(nivel: Optional[str] = None, archivo: Optional[Path] = None,
                   max_bytes: int = MAX_BYTES, respaldos: int = RESPALDOS) -> dict:
    """El `dictConfig` del asistente. Sirve tal cual como `log_config` de uvicorn."""
    nivel = nivel_valido(nivel)
    if archivo is not None:
        Path(archivo).parent.mkdir(parents=True, exist_ok=True)
        salida = {"class": "logging.handlers.RotatingFileHandler", "formatter": "con_fecha",
                  "filename": str(archivo), "maxBytes": max_bytes, "backupCount": respaldos,
                  "encoding": "utf-8"}
    else:
        salida = {"class": "logging.StreamHandler", "formatter": "con_fecha",
                  "stream": "ext://sys.stderr"}
    propio = {"handlers": ["salida"], "level": nivel, "propagate": False}
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"con_fecha": {"format": FORMATO, "datefmt": FORMATO_FECHA}},
        "handlers": {"salida": salida},
        "loggers": {nombre: dict(propio)
                    for nombre in ("gpmc", "uvicorn", "uvicorn.error", "uvicorn.access")},
    }
