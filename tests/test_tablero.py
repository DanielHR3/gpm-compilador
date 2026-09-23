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


# --- agregar -----------------------------------------------------------------

from datetime import date  # noqa: E402

from gpmc.planeacion.registro import clave  # noqa: E402


def _linea(nombre, dependencia, requisitos, campos, huecos, nivel="Bajo",
           catalogos=(), registrado="2026-09-23T18:00:00+00:00"):
    return {
        "clave": clave(nombre), "nombre": nombre, "dependencia": dependencia,
        "homoclave": "", "registrado": registrado, "requisitos": list(requisitos),
        "campos": list(campos), "huecos": dict(huecos),
        "metricas": {"tareas": 3, "bifurcaciones": 0, "vistas": 2, "campos": len(campos),
                     "acciones": 1, "integraciones": len(catalogos)},
        "nivel": nivel, "catalogos": list(catalogos), "actores": 2, "documentos": 1,
    }


TRES = [
    _linea("Reposición", "SEMARNATH", ["Identificación Oficial", "Tarjeta de Circulación"],
           ["curp", "placa"], {"DIC-08": 20, "DIC-06": 1}, nivel="Medio", catalogos=["mgee"],
           registrado="2026-09-23T18:00:00+00:00"),
    _linea("Prórroga", "SEMARNATH", ["identificación oficial"],
           ["curp", "folio_anterior"], {"DIC-08": 1, "FLU-01": 1}, catalogos=["mgee", "zip_codes"],
           registrado="2026-09-16T10:00:00+00:00"),
    _linea("Testamento", "IIFEH", ["Acta de nacimiento"],
           ["curp", "nombre"], {"FLU-01": 1}, nivel="Alto",
           registrado="2026-06-01T10:00:00+00:00"),
]
HOY = date(2026, 9, 23)


def test_agregar_cuenta_requisitos_agrupando_variantes_por_clave():
    d = tablero.agregar(TRES, hoy=HOY)
    assert d["total_tramites"] == 3
    assert d["requisitos"][0] == {"nombre": "Identificación Oficial", "tramites": 2, "porcentaje": 67}
    assert [r["nombre"] for r in d["requisitos"]] == [
        "Identificación Oficial", "Acta de nacimiento", "Tarjeta de Circulación"]


def test_agregar_campos_compartidos_solo_los_de_dos_o_mas():
    d = tablero.agregar(TRES, hoy=HOY)
    assert d["campos_compartidos"] == [{"nombre": "curp", "tramites": 3, "porcentaje": 100}]


def test_agregar_ordena_huecos_por_tramites_no_por_total():
    d = tablero.agregar(TRES, hoy=HOY)
    assert d["huecos"][0] == {"codigo": "DIC-08", "tramites": 2, "total": 21}
    assert d["huecos"][1] == {"codigo": "FLU-01", "tramites": 2, "total": 2}
    assert d["huecos"][2] == {"codigo": "DIC-06", "tramites": 1, "total": 1}


def test_agregar_complejidad_ordenada_por_nivel_y_dependencias_con_cuenta():
    d = tablero.agregar(TRES, hoy=HOY)
    assert [c["nombre"] for c in d["complejidad"]] == ["Testamento", "Reposición", "Prórroga"]
    assert d["complejidad"][0]["metricas"]["tareas"] == 3
    assert d["dependencias"] == [{"nombre": "SEMARNATH", "tramites": 2}, {"nombre": "IIFEH", "tramites": 1}]
    assert d["ultimo_registro"] == "2026-09-23T18:00:00+00:00"
    assert d["catalogos"] == [{"clave": "mgee", "tramites": 2}, {"clave": "zip_codes", "tramites": 1}]


def test_agregar_actividad_son_doce_semanas_con_ceros():
    d = tablero.agregar(TRES, hoy=HOY)
    assert len(d["actividad"]) == 12
    assert d["actividad"][-1] == {"semana": "2026-W39", "tramites": 1}
    assert d["actividad"][-2] == {"semana": "2026-W38", "tramites": 1}
    assert sum(a["tramites"] for a in d["actividad"]) == 2   # junio queda fuera (12 semanas = desde el 6-jul)


def test_agregar_filtra_por_dependencia_y_recalcula_porcentajes():
    d = tablero.agregar(TRES, dependencia="IIFEH", hoy=HOY)
    assert d["total_tramites"] == 1
    assert d["requisitos"] == [{"nombre": "Acta de nacimiento", "tramites": 1, "porcentaje": 100}]
    assert d["campos_compartidos"] == []


def test_agregar_dependencia_inexistente_o_sin_lineas_da_vacio_sin_error():
    for d in (tablero.agregar(TRES, dependencia="NADIE", hoy=HOY), tablero.agregar([], hoy=HOY)):
        assert d["total_tramites"] == 0 and d["ultimo_registro"] is None
        assert d["requisitos"] == [] and d["huecos"] == [] and d["complejidad"] == []
        assert len(d["actividad"]) == 12
