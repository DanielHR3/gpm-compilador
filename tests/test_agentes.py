"""agentes/: el unico modulo del sistema que habla con un modelo de lenguaje.

Ninguna prueba de este archivo toca la red: todo pasa por ProveedorFalso.
"""
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "gpmc"


def test_el_nucleo_no_importa_agentes():
    """Invariante del repo: sin red en el nucleo. Se garantiza por la direccion
    de las importaciones, no por costumbre."""
    for archivo in (SRC / "nucleo").glob("*.py"):
        assert not re.search(r"^\s*(from|import)\s+gpmc\.agentes",
                             archivo.read_text(encoding="utf-8"), re.M), archivo


def test_sin_variables_no_hay_proveedor():
    from gpmc.agentes.proveedor import crear_proveedor, NingunProveedor, hay_proveedor
    assert isinstance(crear_proveedor(entorno={}), NingunProveedor)
    assert hay_proveedor(entorno={}) is False


def test_ningun_proveedor_no_llama_a_nada():
    from gpmc.agentes.proveedor import NingunProveedor, ProveedorNoDisponible
    with pytest.raises(ProveedorNoDisponible):
        NingunProveedor().completar("i", "c", {})


def test_proveedor_falso_devuelve_guion_en_orden():
    from gpmc.agentes.proveedor import ProveedorFalso
    p = ProveedorFalso(['{"a":1}', '{"a":2}'])
    r1 = p.completar("i", "c", {})
    r2 = p.completar("i", "c", {})
    assert r1.texto == '{"a":1}' and r2.texto == '{"a":2}'
    assert r1.modelo == "falso" and r1.duracion_ms >= 0
    assert p.llamadas == 2


def test_proveedor_falso_agotado_es_error_de_red():
    """Un guion que se acaba simula un fallo del servicio: asi se prueban los
    reintentos sin red."""
    from gpmc.agentes.proveedor import ProveedorFalso, ErrorDeRed
    p = ProveedorFalso([])
    with pytest.raises(ErrorDeRed):
        p.completar("i", "c", {})


def test_proveedor_desconocido_no_se_adivina():
    from gpmc.agentes.proveedor import crear_proveedor, NingunProveedor
    p = crear_proveedor(entorno={"GPMC_IA_PROVEEDOR": "otro", "GPMC_IA_LLAVE": "x"})
    assert isinstance(p, NingunProveedor)
