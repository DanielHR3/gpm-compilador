from gpmc.extractores.expediente import extraer_expediente
from gpmc.web.sesiones import escribir_compuertas
from gpmc.web.reensamblado import reensamblar_flujo
from tests.test_extractor_expediente import _DICC_RAMA, _TOBE_RAMA


def _expediente_sesion(tmp_path, dicc_md, tobe_md):
    """Igual que `_expediente` de test_extractor_expediente.py, pero con los
    nombres de insumo exactos que usa una sesión web (sin prefijo de orden)."""
    carpeta = tmp_path / "sesion"
    carpeta.mkdir()
    (carpeta / "Diccionario de Datos.md").write_text(dicc_md, encoding="utf-8")
    (carpeta / "Propuesta TO-BE.md").write_text(tobe_md, encoding="utf-8")
    return carpeta


def test_reensamblar_flujo_aplica_el_override_de_compuerta(tmp_path):
    # El TO-BE original ramifica solo (la compuerta ya trae @@procede); para
    # este manifiesto lo que importa son sus pantallas, así que se construye
    # con el TO-BE original y luego, para el reensamblado, se sobre-escribe
    # con la variante MMD-04 (compuerta sin @@campo) que solo ramifica con
    # el override de compuertas.json.
    carpeta = _expediente_sesion(tmp_path, _DICC_RAMA, _TOBE_RAMA)
    m = extraer_expediente(carpeta).manifiesto
    assert m is not None

    tobe_mmd04 = _TOBE_RAMA.replace("{¿@@procede == 'si'?}", "{¿Procede?}")
    (carpeta / "Propuesta TO-BE.md").write_text(tobe_mmd04, encoding="utf-8")
    escribir_compuertas(carpeta, {"G": "procede"})

    resultado = reensamblar_flujo(carpeta, m)

    assert resultado is m
    con_cond = [c for c in resultado.flujo.conexiones if c.cuando is not None]
    assert len(con_cond) == 2
    assert {(c.cuando.campo, c.cuando.igual) for c in con_cond} == {
        ("procede", "si"), ("procede", "no"),
    }


def test_reensamblar_flujo_sin_tobe_devuelve_el_manifiesto_intacto(tmp_path):
    carpeta = tmp_path / "solo_dicc"
    carpeta.mkdir()
    (carpeta / "Diccionario de Datos.md").write_text(_DICC_RAMA, encoding="utf-8")
    m = extraer_expediente(carpeta).manifiesto
    assert m is not None

    flujo_antes = m.flujo
    resultado = reensamblar_flujo(carpeta, m)

    assert resultado is m
    assert resultado.flujo is flujo_antes
