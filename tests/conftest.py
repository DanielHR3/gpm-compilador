"""Configuracion de las pruebas.

Las pruebas que necesitan material real (exports autenticos de la plataforma,
expedientes del wiki de reingenieria) se saltan cuando ese material no esta
disponible. Nunca fallan por eso: el material es interno y no vive en el
repositorio.

Para correrlas con material real, apuntar las variables de entorno:

    export GPMC_EXPORTS=~/ruta/a/exports
    export GPMC_GPM=~/ruta/a/archivos-gpm
    export GPMC_WIKI=~/ruta/a/wiki/expedientes
"""

import os
from pathlib import Path

import pytest


def _ruta(variable: str) -> Path:
    """Ruta configurada por entorno. Sin configurar, apunta a un lugar que no
    existe, y las pruebas que dependan de ella se saltan."""
    return Path(os.environ.get(variable, "/__sin_configurar__")).expanduser()


EXPORTS = _ruta("GPMC_EXPORTS")
EQUIPO = _ruta("GPMC_GPM")
WIKI = _ruta("GPMC_WIKI")


def legible(ruta) -> bool:
    """macOS puede negar el acceso a ~/Documents y ~/Desktop (TCC) aunque el
    archivo exista: exists() devuelve True y la lectura revienta."""
    try:
        with open(ruta, "rb") as f:
            f.read(1)
        return True
    except (OSError, PermissionError):
        return False


# Alias historico usado por varias pruebas.
_legible = legible


@pytest.fixture
def exports_autenticos() -> list:
    """Archivos .gpm producidos por la plataforma, no por scripts."""
    if not EXPORTS.is_dir():
        pytest.skip("GPMC_EXPORTS no configurada")
    rutas = [r for r in sorted(EXPORTS.glob("*.gpm")) if legible(r)]
    if len(rutas) < 2:
        pytest.skip(f"se esperaban 2 o mas exports en {EXPORTS}")
    return rutas


@pytest.fixture
def export_referencia(exports_autenticos):
    """Un solo export, para comparar estructuras."""
    return exports_autenticos[0]


@pytest.fixture
def gpm_del_equipo() -> list:
    """Archivos .gpm construidos a mano, para probar el validador."""
    if not EQUIPO.is_dir():
        pytest.skip("GPMC_GPM no configurada")
    rutas = [r for r in sorted(EQUIPO.rglob("*.gpm")) if legible(r)]
    if not rutas:
        pytest.skip(f"sin archivos .gpm legibles en {EQUIPO}")
    return rutas


@pytest.fixture
def wiki() -> Path:
    """Carpeta de expedientes del wiki de reingenieria."""
    if not WIKI.is_dir() or not legible(WIKI):
        pytest.skip("GPMC_WIKI no configurada o sin acceso")
    return WIKI
