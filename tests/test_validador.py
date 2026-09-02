from gpmc.validador.reglas import revisar, revisar_archivo


def _base():
    return {
        "Tareas": [
            {"id": "1", "inicial": "1", "terminal": "0", "Pasos": []},
            {"id": "2", "inicial": "0", "terminal": "1", "Pasos": []},
        ],
        "Conexiones": [{"id": 1, "tarea_id_origen": 1, "tarea_id_destino": 2,
                        "tipo": "secuencial", "regla": None}],
        "Formularios": [], "Acciones": [], "Documentos": [],
    }


def _codigos(hallazgos):
    return {h.codigo for h in hallazgos}


def test_un_gpm_sano_no_produce_hallazgos():
    assert revisar(_base()) == []


def test_detecta_conexion_a_tarea_inexistente():
    g = _base()
    g["Conexiones"][0]["tarea_id_destino"] = 99
    assert "EST-01" in _codigos(revisar(g))


def test_detecta_ausencia_de_tarea_terminal():
    g = _base()
    g["Tareas"][1]["terminal"] = "0"
    assert "EST-02" in _codigos(revisar(g))


def test_detecta_folio_con_count():
    g = _base()
    g["Acciones"] = [{"nombre": "folio", "tipo": "variable",
                      "extra": '{"variable":"folio","expresion":"$t = X->count(); return $t;"}'}]
    assert "FOLIO-01" in _codigos(revisar(g))


def test_detecta_folio_con_rand():
    g = _base()
    g["Acciones"] = [{"nombre": "folio", "tipo": "variable",
                      "extra": '{"variable":"folio","expresion":"return rand(10000, 99999);"}'}]
    assert "FOLIO-01" in _codigos(revisar(g))


def test_el_folio_autentico_sobre_dato_seguimiento_pasa_limpio():
    """La forma auténtica (dos exports que funcionan) bloquea 'dato_seguimiento'
    columna 'valor'. Es correcta; no debe marcar FOLIO-02. Ver acta 2026-08-30."""
    g = _base()
    g["Acciones"] = [{"nombre": "folio", "tipo": "variable",
                      "extra": '{"variable":"folio","expresion":"\\\\DB::table(\'dato_seguimiento\')->where(\'nombre\', \'folio\')->lockForUpdate()->value(\'valor\');"}'}]
    assert "FOLIO-02" not in _codigos(revisar(g))


def test_detecta_folio_que_bloquea_una_tabla_distinta_de_dato_seguimiento():
    """El contador auténtico vive en dato_seguimiento. El viejo esquema por
    proceso_folio/proceso_id se rompe al importar (la plataforma reasigna el
    proceso_id, PLAT-4); se marca FOLIO-02."""
    g = _base()
    g["Acciones"] = [{"nombre": "folio", "tipo": "variable",
                      "extra": '{"variable":"folio","expresion":"\\\\DB::table(\'proceso_folio\')->where(\'proceso_id\', 59201)->lockForUpdate()->value(\'contador\');"}'}]
    assert "FOLIO-02" in _codigos(revisar(g))


def test_sin_tarea_inicial_es_bloqueante():
    g = _base()
    g["Tareas"][0]["inicial"] = "0"
    assert "EST-03" in _codigos(revisar(g))


def test_varias_tareas_iniciales_son_aviso_no_defecto():
    """El export autentico del un export de referencia tiene dos puntos de entrada: un
    tramite omnicanal donde el ciudadano entra en linea o el funcionario en
    ventanilla. No es un defecto."""
    g = _base()
    g["Tareas"][1]["inicial"] = "1"
    hallazgos = revisar(g)
    assert "EST-03" not in _codigos(hallazgos)
    est04 = [h for h in hallazgos if h.codigo == "EST-04"]
    assert len(est04) == 1
    assert est04[0].gravedad == "aviso"


def test_detecta_documento_sin_escapar():
    g = _base()
    g["Acciones"] = [{"nombre": "oficio", "tipo": "variable",
                      "extra": '{"variable":"html","expresion":"$h = \'<p>\' . $data[\'x\'] . \'</p>\'; return $h;"}'}]
    assert "DOC-01" in _codigos(revisar(g))


def test_reporta_credencial_expuesta_como_aviso_no_como_bloqueante():
    """Decision del area: se reporta, no se bloquea (spec seccion 7)."""
    g = _base()
    g["Formularios"] = [{"id": "1", "Campos": [
        {"nombre": "x", "tipo": "text",
         "extra": '{"apiTrigger":{"headers":{"Authorization":"Bearer abc"}}}'}]}]
    hallazgos = revisar(g)
    seg04 = [h for h in hallazgos if h.codigo == "CRED-01"]
    assert len(seg04) == 1
    assert seg04[0].gravedad == "aviso"


def test_la_regla_de_sintaxis_esta_apagada_por_omision():
    """Spec seccion 9.bis: cuestion abierta, no se afirma un defecto sin evidencia."""
    g = _base()
    g["Conexiones"] = [{"id": 1, "tarea_id_origen": 1, "tarea_id_destino": 2,
                        "tipo": "evaluacion", "regla": "@@x=='si'"}]
    assert "FMT-01" not in _codigos(revisar(g))


def test_detecta_nombre_de_campo_que_desborda_la_columna_de_la_plataforma():
    """La columna 'campo.nombre' corta en 30 y el import entero falla con
    'Data too long for column nombre' (verificado 2026-09-02, expediente de
    Prórroga). El extractor ya lo capa, pero un manifiesto escrito a mano
    puede traer un nombre largo: el validador es la red de seguridad."""
    g = _base()
    g["Formularios"] = [{"id": "10", "Campos": [
        {"nombre": "fecha_vencimiento_certificado_anterior", "tipo": "date"},
    ]}]
    hallazgos = revisar(g)
    assert "EST-05" in _codigos(hallazgos)
    assert any(h.gravedad == "bloqueante" for h in hallazgos if h.codigo == "EST-05")


def test_un_nombre_de_campo_dentro_del_limite_pasa_limpio():
    g = _base()
    g["Formularios"] = [{"id": "10", "Campos": [
        {"nombre": "curp_testador", "tipo": "text"},
    ]}]
    assert "EST-05" not in _codigos(revisar(g))


def test_la_regla_de_sintaxis_se_activa_con_la_constante(monkeypatch):
    from gpmc.nucleo import reglas as nreglas
    monkeypatch.setattr(nreglas, "SINTAXIS_ESTRICTA", True)
    g = _base()
    g["Conexiones"] = [{"id": 1, "tarea_id_origen": 1, "tarea_id_destino": 2,
                        "tipo": "evaluacion", "regla": "@@x=='si'"}]
    assert "FMT-01" in _codigos(revisar(g))


def test_encuentra_los_defectos_reales_de_los_gpm_del_equipo(gpm_del_equipo):
    """Criterio de aceptacion del spec seccion 13."""
    por_archivo = {r.name: _codigos(revisar_archivo(r)) for r in gpm_del_equipo}
    con_folio_malo = [n for n, c in por_archivo.items() if "FOLIO-02" in c or "FOLIO-01" in c]
    con_token = [n for n, c in por_archivo.items() if "CRED-01" in c]

    assert len(con_folio_malo) >= 3, f"esperaba al menos 3 folios defectuosos, hallo {con_folio_malo}"
    assert any("alta-de-avisos-test-ui" in n for n in con_token), \
        f"esperaba el token expuesto en alta-de-avisos-test-ui, hallo {con_token}"


def test_detecta_select_manual_sin_opciones_con_datos_null():
    """radio/display.php y CampoSelect.php hacen foreach($datos): con datos=null
    la vista suelta 'Invalid argument supplied for foreach()' (verificado
    2026-09-02). Un manifiesto a mano puede dejarlo así; el validador lo marca."""
    g = _base()
    g["Formularios"] = [{"id": "10", "Campos": [
        {"nombre": "tipo_holograma", "tipo": "select", "datos": None,
         "extra": '{"catalog_type": "manual", "catalog_url": ""}'},
    ]}]
    hallazgos = revisar(g)
    assert "EST-06" in _codigos(hallazgos)
    assert any(h.gravedad == "bloqueante" for h in hallazgos if h.codigo == "EST-06")


def test_un_select_remoto_con_datos_null_no_dispara_EST_06():
    g = _base()
    g["Formularios"] = [{"id": "10", "Campos": [
        {"nombre": "estado_sol", "tipo": "select", "datos": None,
         "extra": '{"catalog_type": "url", "catalog_url": "https://x/y"}'},
    ]}]
    assert "EST-06" not in _codigos(revisar(g))


def test_un_select_con_lista_vacia_es_solo_aviso():
    g = _base()
    g["Formularios"] = [{"id": "10", "Campos": [
        {"nombre": "tipo_holograma", "tipo": "select", "datos": "[]",
         "extra": '{"catalog_type": "manual", "catalog_url": ""}'},
    ]}]
    hallazgos = [h for h in revisar(g) if h.codigo == "EST-06"]
    assert hallazgos and all(h.gravedad == "aviso" for h in hallazgos)
