import json

from gpmc.nucleo.formato import escribir, leer, serializar


def test_ida_y_vuelta_byte_a_byte(exports_autenticos):
    """El emisor debe reproducir un export de la plataforma sin un solo byte de diferencia."""
    for ruta in exports_autenticos:
        original = ruta.read_text(encoding="utf-8")
        assert serializar(json.loads(original)) == original, f"difiere: {ruta.name}"


def test_serializar_escapa_diagonales():
    """PHP escapa / como \\/; Python no lo hace por defecto."""
    assert serializar({"url": "https://a.mx/b"}) == r'{"url":"https:\/\/a.mx\/b"}'


def test_serializar_sin_espacios_en_separadores():
    assert serializar({"a": 1, "b": 2}) == '{"a":1,"b":2}'


def test_serializar_escapa_acentos():
    assert serializar({"n": "Vinculación"}) == '{"n":"Vinculaci\\u00f3n"}'


def test_escribir_y_leer_conservan_el_contenido(tmp_path):
    obj = {"nombre": "Trámite de prueba", "url": "https://x.mx/y", "Tareas": []}
    destino = tmp_path / "prueba.gpm"
    escribir(obj, destino)
    assert leer(destino) == obj
    assert destino.read_text(encoding="utf-8") == serializar(obj)
