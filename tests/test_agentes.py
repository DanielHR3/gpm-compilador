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


# ── Tarea 2: contexto DIC-08 ──
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Manifiesto


def _manifiesto_dos_pantallas() -> Manifiesto:
    return Manifiesto(**{
        "tramite": {"nombre": "Prueba", "dependencia": "DGT"},
        "actores": [{"id": "c", "nombre": "Ciudadano"}],
        "pantallas": [
            {"id": "p1", "nombre": "Datos", "actor": "c", "campos": [
                {"nombre": "es_moral", "etiqueta": "¿Persona moral?", "tipo": "radio",
                 "catalogo": [{"etiqueta": "Sí", "valor": "si"}, {"etiqueta": "No", "valor": "no"}]},
                {"nombre": "estado", "etiqueta": "Estado", "tipo": "select",
                 "catalogo": [{"etiqueta": "Hidalgo", "valor": "hidalgo"}, {"etiqueta": "Otro", "valor": "otro"}]},
            ]},
            {"id": "p2", "nombre": "Empresa", "actor": "c", "campos": [
                {"nombre": "rfc", "etiqueta": "RFC", "tipo": "text"},
                {"nombre": "domicilio_fiscal", "etiqueta": "Domicilio fiscal", "tipo": "text"},
            ]},
        ],
        "flujo": {"tareas": [{"id": "t1", "nombre": "Datos", "actor": "c", "inicial": True,
                              "terminal": True, "pantallas": ["p1", "p2"]}], "conexiones": []},
    })


def _dic08(ubicacion: str, etiqueta: str, nombre: str, prosa: str) -> Hueco:
    return Hueco("falta_dato", "DIC-08", ubicacion,
                 f"la condición de visibilidad de '{etiqueta}' ({nombre}) no se "
                 f"pudo interpretar: «{prosa}»; configúrala a mano")


def test_contexto_extrae_la_prosa_y_los_candidatos_anteriores():
    from gpmc.agentes.contexto import contexto_dic08
    m = _manifiesto_dos_pantallas()
    ctx = contexto_dic08(m, [_dic08("p2::rfc", "RFC", "rfc", "Solo si es persona moral")])
    assert len(ctx.huecos) == 1
    h = ctx.huecos[0]
    assert h.prosa == "Solo si es persona moral"
    assert h.campo == "rfc" and h.pantalla == "p2"
    assert set(h.candidatos) == {"es_moral", "estado", "domicilio_fiscal"}


def test_contexto_no_incluye_campos_de_pantallas_posteriores():
    from gpmc.agentes.contexto import contexto_dic08
    m = _manifiesto_dos_pantallas()
    ctx = contexto_dic08(m, [_dic08("p1::estado", "Estado", "estado", "Si es moral")])
    assert set(ctx.huecos[0].candidatos) == {"es_moral"}


def test_contexto_lleva_los_valores_tecnicos_del_catalogo():
    from gpmc.agentes.contexto import contexto_dic08
    m = _manifiesto_dos_pantallas()
    ctx = contexto_dic08(m, [_dic08("p2::rfc", "RFC", "rfc", "x")])
    por_nombre = {c.nombre: c for c in ctx.campos}
    assert por_nombre["es_moral"].valores == ["si", "no"]
    assert por_nombre["domicilio_fiscal"].valores == []


def test_contexto_omite_huecos_sin_prosa_reconocible():
    from gpmc.agentes.contexto import contexto_dic08
    m = _manifiesto_dos_pantallas()
    raro = Hueco("falta_dato", "DIC-08", "p2::rfc", "mensaje sin las comillas esperadas")
    ctx = contexto_dic08(m, [raro])
    assert ctx.huecos == []
    assert ctx.omitidos == [("p2::rfc", "sin_prosa")]


def test_contexto_ignora_huecos_que_no_son_dic08():
    from gpmc.agentes.contexto import contexto_dic08
    m = _manifiesto_dos_pantallas()
    otro = Hueco("falta_dato", "META-01", "metadatos", "falta el tiempo")
    assert contexto_dic08(m, [otro]).huecos == []


def test_contexto_no_lleva_nada_que_parezca_ejemplo_real():
    """El manifiesto no conserva la columna 'Ejemplo Real' del Diccionario; esta
    prueba fija que el contexto solo serializa los atributos permitidos."""
    from gpmc.agentes.contexto import CampoCandidato
    assert set(CampoCandidato.model_fields) == {"nombre", "etiqueta", "tipo", "valores", "pantalla"}


def test_partir_lote_por_presupuesto():
    from gpmc.agentes.contexto import contexto_dic08, partir_lote
    m = _manifiesto_dos_pantallas()
    huecos = [_dic08("p2::rfc", "RFC", "rfc", "a" * 400),
              _dic08("p2::domicilio_fiscal", "Domicilio fiscal", "domicilio_fiscal", "b" * 400)]
    ctx = contexto_dic08(m, huecos)
    # Presupuesto justo por debajo del lote entero: cabe cada mitad, no el todo.
    from gpmc.agentes.contexto import estimar_tokens
    partes = partir_lote(ctx, max_tokens=estimar_tokens(ctx) - 1)
    assert len(partes) == 2 and all(len(p.huecos) == 1 for p in partes)
    # Presupuesto imposible: nada cabe ni solo; se omite con motivo, no revienta.
    solo = partir_lote(ctx, max_tokens=10)
    assert all(p.huecos == [] and p.omitidos[0][1] == "tope_tokens" for p in solo)

