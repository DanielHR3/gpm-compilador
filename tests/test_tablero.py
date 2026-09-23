import json
from datetime import datetime, timezone

from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import (
    Actor, Campo, Flujo, Manifiesto, OpcionCatalogo, Pantalla, Tarea, Tramite,
)
from gpmc.web import tablero


def _manifiesto(nombre="Reposición de Certificado", dependencia="SEMARNATH", campos=None):
    campos = campos if campos is not None else [
        Campo(nombre="curp", etiqueta="CURP"),
        Campo(nombre="doc_ine", etiqueta="Documento: Identificación Oficial", tipo="file"),
        Campo(nombre="doc_tc", etiqueta="Documento: Tarjeta de Circulación", tipo="file"),
        Campo(nombre="estado", etiqueta="Estado", tipo="select",
              catalogo=[OpcionCatalogo(etiqueta="Hidalgo", valor="13")], origen="inegi"),
    ]
    return Manifiesto(
        tramite=Tramite(nombre=nombre, dependencia=dependencia),
        actores=[Actor(id="c", nombre="Ciudadano")],
        pantallas=[Pantalla(id="p1", nombre="Datos", actor="c", campos=campos)],
        flujo=Flujo(tareas=[Tarea(id="t1", nombre="T1", actor="c", inicial=True, terminal=True)],
                    conexiones=[]),
    )


AHORA = datetime(2026, 9, 23, 18, 0, tzinfo=timezone.utc)


def test_resumir_saca_solo_agregados_y_nada_del_contenido():
    huecos = [Hueco("falta_dato", "DIC-08", "p1", "cond"), Hueco("falta_dato", "DIC-08", "p1", "x"),
              Hueco("bloqueante", "FLU-01", "flujo", "lineal")]
    linea = tablero.resumir(_manifiesto(), huecos, ahora=AHORA)
    assert linea["clave"] == "reposicion de certificado"
    assert linea["nombre"] == "Reposición de Certificado" and linea["dependencia"] == "SEMARNATH"
    assert linea["registrado"] == "2026-09-23T18:00:00+00:00"
    assert linea["requisitos"] == ["Identificación Oficial", "Tarjeta de Circulación"]
    assert linea["campos"] == ["curp", "doc_ine", "doc_tc", "estado"]
    assert linea["huecos"] == {"DIC-08": 2, "FLU-01": 1}
    assert linea["metricas"]["campos"] == 4 and linea["nivel"]
    assert linea["catalogos"] == ["mgee"]
    assert linea["actores"] == 1 and linea["documentos"] == 0
    # Nada del contenido: ni el valor del catalogo ni su etiqueta.
    texto = json.dumps(linea, ensure_ascii=False)
    assert "Hidalgo" not in texto and '"13"' not in texto and "sid" not in linea


def test_resumir_sin_nombre_devuelve_none():
    assert tablero.resumir(_manifiesto(nombre="[por confirmar]"), [], ahora=AHORA) is None
    assert tablero.resumir(_manifiesto(nombre="  "), [], ahora=AHORA) is None


def test_resumir_sin_requisitos_ni_huecos_da_listas_vacias():
    linea = tablero.resumir(_manifiesto(campos=[Campo(nombre="curp")]), [], ahora=AHORA)
    assert linea["requisitos"] == [] and linea["huecos"] == {} and linea["catalogos"] == []


def test_registrar_reemplaza_la_linea_de_la_misma_clave(tmp_path):
    a = tablero.resumir(_manifiesto(), [], ahora=AHORA)
    b = tablero.resumir(_manifiesto(dependencia="OTRA"), [], ahora=AHORA)
    tablero.registrar(tmp_path, a)
    tablero.registrar(tmp_path, b)
    lineas = (tmp_path / tablero.ARCHIVO).read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 1
    assert json.loads(lineas[0])["dependencia"] == "OTRA"


def test_registrar_conserva_los_otros_tramites(tmp_path):
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Uno"), [], ahora=AHORA))
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Dos"), [], ahora=AHORA))
    assert [l["nombre"] for l in tablero.leer(tmp_path)] == ["Uno", "Dos"]


def test_leer_salta_una_linea_corrupta_y_lo_dice_en_el_log(tmp_path, caplog):
    # La linea corrupta va al final: `registrar` reescribe el archivo entero
    # y la tiraria si se escribiera antes de un registro.
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Uno"), [], ahora=AHORA))
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Dos"), [], ahora=AHORA))
    with (tmp_path / tablero.ARCHIVO).open("a", encoding="utf-8") as f:
        f.write("{esto no es json\n")
    with caplog.at_level("WARNING", logger="gpmc.web.tablero"):
        lineas = tablero.leer(tmp_path)
    assert [l["nombre"] for l in lineas] == ["Uno", "Dos"]
    assert any("linea 3" in r.getMessage() for r in caplog.records)


def test_leer_sin_archivo_devuelve_lista_vacia(tmp_path):
    assert tablero.leer(tmp_path) == []


def test_la_purga_de_sesiones_no_toca_el_registro(tmp_path):
    import os, time
    from gpmc.web.sesiones import _purgar_sesiones
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(), [], ahora=AHORA))
    viejo = time.time() - 30 * 86400
    os.utime(tmp_path / tablero.ARCHIVO, (viejo, viejo))
    _purgar_sesiones(tmp_path)
    assert (tmp_path / tablero.ARCHIVO).exists()
