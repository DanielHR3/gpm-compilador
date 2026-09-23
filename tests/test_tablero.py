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
    # Los archivos ya cuentan como requisitos; «campos» son los datos que se capturan.
    assert linea["campos"] == ["curp", "estado"]
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
           ["curp", "nombre"], {"FLU-01": 1}, nivel="Complejo",
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
    assert d["campos_compartidos"] == [{"nombre": "curp", "etiqueta": "curp", "tramites": 3, "porcentaje": 100}]


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
    assert [(c["clave"], c["tramites"]) for c in d["catalogos"]] == [("mgee", 2), ("zip_codes", 1)]


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


# --- revision final: registro lateral, permanente y tolerante -----------------

def test_registrar_no_pierde_lo_que_habia_si_la_escritura_falla(tmp_path, monkeypatch, caplog):
    """El archivo es la memoria del tablero: un corte a mitad de escritura no
    puede dejarlo vacio. Se escribe aparte y se reemplaza de golpe."""
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Uno"), [], ahora=AHORA))
    import os
    def revienta(*a, **k):
        raise OSError("disco lleno")
    monkeypatch.setattr(os, "replace", revienta)
    with caplog.at_level("ERROR", logger="gpmc.web.tablero"):
        ok = tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Dos"), [], ahora=AHORA))
    assert ok is False
    assert [l["nombre"] for l in tablero.leer(tmp_path)] == ["Uno"]
    assert any("tablero" in r.getMessage() for r in caplog.records)


def test_registrar_no_deja_archivo_temporal(tmp_path):
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(), [], ahora=AHORA))
    assert [p.name for p in tmp_path.iterdir()] == [tablero.ARCHIVO]


def test_leer_salta_una_linea_bien_formada_pero_degradada(tmp_path, caplog):
    """Una linea de una version anterior del esquema, o editada a mano, no
    puede tumbar el endpoint entero: se salta y se anota, como la ilegible."""
    tablero.registrar(tmp_path, tablero.resumir(_manifiesto(nombre="Uno"), [], ahora=AHORA))
    with (tmp_path / tablero.ARCHIVO).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"clave": "x", "nombre": "X", "registrado": "ayer"}) + "\n")
        f.write(json.dumps({"clave": "y", "registrado": AHORA.isoformat()}) + "\n")
        f.write(json.dumps(["no", "es", "dict"]) + "\n")
    with caplog.at_level("WARNING", logger="gpmc.web.tablero"):
        lineas = tablero.leer(tmp_path)
    assert [l["nombre"] for l in lineas] == ["Uno"]
    assert sum(1 for r in caplog.records if "se salta" in r.getMessage()) == 3
    d = tablero.agregar(lineas, hoy=HOY)
    assert d["total_tramites"] == 1


def test_actualizar_rotulos_cambia_dependencia_y_conserva_huecos(tmp_path):
    linea = tablero.resumir(_manifiesto(), [Hueco("falta_dato", "META-02", "metadatos", "dep")], ahora=AHORA)
    tablero.registrar(tmp_path, linea)
    nueva = tablero.resumir(_manifiesto(dependencia="SEGOB"), [], ahora=AHORA)
    assert tablero.actualizar_rotulos(tmp_path, nueva) is True
    (l,) = tablero.leer(tmp_path)
    assert l["dependencia"] == "SEGOB"
    assert l["huecos"] == {"META-02": 1} and l["registrado"] == AHORA.isoformat()
    assert tablero.actualizar_rotulos(tmp_path, tablero.resumir(_manifiesto(nombre="Otro"), [], ahora=AHORA)) is False


# --- rediseno visual: indicadores, matrices y distribucion --------------------

def test_agregar_indicadores_promedios_y_conteos():
    d = tablero.agregar(TRES, hoy=HOY)
    i = d["indicadores"]
    assert i["requisitos_distintos"] == 3          # identificacion (x2), tarjeta, acta
    assert i["promedio_campos"] == 2.0
    assert i["promedio_huecos"] == round((21 + 2 + 1) / 3, 1)
    assert i["con_integracion"] == 2


def test_agregar_matriz_huecos_tramite_por_codigo():
    d = tablero.agregar(TRES, hoy=HOY)
    m = d["matriz_huecos"]
    # Filas en el orden de complejidad; columnas en el orden de la lista de huecos.
    assert m["filas"] == ["Testamento", "Reposición", "Prórroga"]
    assert m["columnas"] == ["DIC-08", "FLU-01", "DIC-06"]
    assert m["celdas"] == [[0, 1, 0], [20, 0, 1], [1, 1, 0]]
    assert m["maximo"] == 20


def test_agregar_matriz_requisitos_presencia_por_tramite():
    d = tablero.agregar(TRES, hoy=HOY)
    m = d["matriz_requisitos"]
    assert m["filas"] == ["Identificación Oficial", "Acta de nacimiento", "Tarjeta de Circulación"]
    assert m["columnas"] == ["Testamento", "Reposición", "Prórroga"]
    assert m["celdas"] == [[0, 1, 1], [1, 0, 0], [0, 1, 0]]


def test_agregar_niveles_y_maximos_de_metricas():
    d = tablero.agregar(TRES, hoy=HOY)
    # Los nombres son los del estimador (Complejo/Medio/Bajo), no «Alto».
    assert d["niveles"] == [{"nivel": "Complejo", "tramites": 1}, {"nivel": "Medio", "tramites": 1},
                            {"nivel": "Bajo", "tramites": 1}]
    assert d["metricas_max"]["campos"] == 2 and d["metricas_max"]["integraciones"] == 2


def test_agregar_vacio_trae_indicadores_en_cero_y_matrices_vacias():
    d = tablero.agregar([], hoy=HOY)
    assert d["indicadores"] == {"requisitos_distintos": 0, "promedio_campos": 0.0,
                                "promedio_huecos": 0.0, "con_integracion": 0}
    assert d["matriz_huecos"] == {"filas": [], "columnas": [], "celdas": [], "maximo": 0}
    assert d["matriz_requisitos"] == {"filas": [], "columnas": [], "celdas": []}
    assert d["niveles"] == [{"nivel": "Complejo", "tramites": 0}, {"nivel": "Medio", "tramites": 0},
                            {"nivel": "Bajo", "tramites": 0}]


def test_agregar_ordena_complejo_primero_con_el_nombre_real_del_estimador():
    lineas = [_linea("B", "D", [], ["a"], {}, nivel="Bajo"), _linea("C", "D", [], ["a"], {}, nivel="Complejo"),
              _linea("M", "D", [], ["a"], {}, nivel="Medio")]
    d = tablero.agregar(lineas, hoy=HOY)
    assert [c["nombre"] for c in d["complejidad"]] == ["C", "M", "B"]
    assert d["niveles"][0] == {"nivel": "Complejo", "tramites": 1}


def test_resumir_no_cuenta_la_vista_de_solo_lectura_como_requisito():
    """La fila «Vista de solo lectura (Origen → Destino)» del Diccionario es de
    tipo N/A y nombra una pantalla; el extractor la clasifica como archivo por
    el «visor de archivos», pero no es un documento que entregue el ciudadano."""
    campos = [
        Campo(nombre="vista_p1", etiqueta="Vista de solo lectura (Ciudadano → Funcionario)", tipo="file"),
        Campo(nombre="doc_ine", etiqueta="Documento: Identificación Oficial", tipo="file"),
    ]
    linea = tablero.resumir(_manifiesto(campos=campos), [], ahora=AHORA)
    assert linea["requisitos"] == ["Identificación Oficial"]


# --- lenguaje llano: etiquetas humanas y proveedores con descripcion ------------

def test_resumir_guarda_la_etiqueta_humana_de_cada_campo():
    campos = [Campo(nombre="curp_propietario", etiqueta="CURP del propietario"),
              Campo(nombre="placa")]
    linea = tablero.resumir(_manifiesto(campos=campos), [], ahora=AHORA)
    assert linea["etiquetas"] == {"curp_propietario": "CURP del propietario"}
    # Sigue sin salir nada del contenido: la etiqueta es el rotulo del campo, no un valor.
    assert "Hidalgo" not in json.dumps(linea, ensure_ascii=False)


def test_agregar_campos_compartidos_traen_etiqueta_humana():
    a = _linea("A", "D", [], ["curp_propietario", "placa"], {})
    b = _linea("B", "D", [], ["curp_propietario"], {})
    a["etiquetas"] = {"curp_propietario": "CURP del propietario"}
    d = tablero.agregar([a, b], hoy=HOY)
    (c,) = d["campos_compartidos"]
    assert c == {"nombre": "curp_propietario", "etiqueta": "CURP del propietario", "tramites": 2, "porcentaje": 100}
    # Sin etiqueta en ninguna linea, la etiqueta es el nombre tecnico.
    d2 = tablero.agregar([_linea("A", "D", [], ["placa"], {}), _linea("B", "D", [], ["placa"], {})], hoy=HOY)
    assert d2["campos_compartidos"][0]["etiqueta"] == "placa"


def test_agregar_catalogos_traen_proveedor_y_descripcion():
    d = tablero.agregar(TRES, hoy=HOY)
    assert d["catalogos"][0] == {"clave": "mgee", "proveedor": "INEGI", "descripcion": "Lista de estados",
                                 "tramites": 2}
    assert d["catalogos"][1]["proveedor"] == "SEPOMEX"
    # Una clave que ya no este en el catalogo no revienta: sale tal cual.
    l = _linea("Z", "D", [], ["a"], {}, catalogos=["viejo"])
    d = tablero.agregar([l], hoy=HOY)
    assert d["catalogos"][0] == {"clave": "viejo", "proveedor": "viejo", "descripcion": "", "tramites": 1}


def test_resumir_solo_cuenta_como_datos_capturados_lo_que_escribe_el_ciudadano():
    """«Datos que se capturan en varios tramites» son entradas: un archivo ya
    cuenta como requisito, y un parrafo, subtitulo, vista de solo lectura o
    documento generado no se capturan."""
    campos = [
        Campo(nombre="curp", etiqueta="CURP"),
        Campo(nombre="estado", etiqueta="Estado", tipo="select"),
        Campo(nombre="doc_tc", etiqueta="Documento: Tarjeta de Circulación", tipo="file"),
        Campo(nombre="aviso", etiqueta="Aviso de privacidad", tipo="paragraph"),
        Campo(nombre="titulo", etiqueta="Datos del vehículo", tipo="subtitle"),
        Campo(nombre="vista_p1", etiqueta="Vista de solo lectura (Ciudadano → Funcionario)", tipo="text"),
        Campo(nombre="oficio", etiqueta="Oficio", tipo="documento"),
    ]
    linea = tablero.resumir(_manifiesto(campos=campos), [], ahora=AHORA)
    assert linea["campos"] == ["curp", "estado"]
    assert linea["requisitos"] == ["Tarjeta de Circulación"]
    # La metrica del estimador sigue contando todos los campos, como siempre.
    assert linea["metricas"]["campos"] == 7
