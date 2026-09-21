from fastapi.testclient import TestClient
from gpmc.web.app import crear_app
from tests.test_extractor_diccionario import _VIS
from tests.test_extractor_expediente import _DICC_RAMA, _TOBE_RAMA

_DICC = ("### Pantalla 1 — Solicitante — Datos\n\n"
         "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
         "| CURP | Texto | Input | Si | La CURP `@@curp` |\n")


def _cli(tmp_path):
    return TestClient(crear_app(almacen=tmp_path))


def test_post_expedientes_devuelve_json_con_sid_y_huecos(tmp_path):
    r = _cli(tmp_path).post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["sid"]) == 16
    assert body["manifiesto"]["tramite"]["nombre"]
    assert any(h["codigo"] == "INS-01" for h in body["huecos"])
    assert "estimacion" in body and "problemas" in body


def test_get_expediente_recupera_el_estado(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}")
    assert r.status_code == 200
    assert r.json()["sid"] == sid


def test_get_expediente_inexistente_da_404(tmp_path):
    r = _cli(tmp_path).get("/api/v1/expedientes/0123456789abcdef")
    assert r.status_code == 404
    assert "error" in r.json()


def test_post_expedientes_archivo_gigante_da_413(tmp_path):
    r = _cli(tmp_path).post("/api/v1/expedientes", files={
        "diccionario": ("enorme.md", b"x" * (11 * 1024 * 1024), "text/markdown")})
    assert r.status_code == 413
    assert "enorme.md" in r.json()["archivos"]


def test_resolver_aplica_meta01_y_devuelve_el_estado_nuevo(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={
        "resoluciones": [{"tipo": "meta01", "ubicacion": "metadatos", "valor": "5 dias habiles"}]})
    assert r.status_code == 200
    assert not any(h["codigo"] == "META-01" for h in r.json()["huecos"])
    assert "5 dias habiles" in r.json()["manifiesto"]["tramite"]["ruts"]["tiempo_entrega"]


# AS-IS que nombra el trámite (para que la extracción del manifiesto prospere)
# pero no declara tiempo de respuesta → el extractor emite META-01 'metadatos'.
_ASIS_SIN_TIEMPO = ("---\ndependencia: Secretaria X\n---\n\n"
                    "# Analisis AS-IS — Registro de Prueba\n\n"
                    "Texto sin tiempo de respuesta declarado.\n")


def test_resolver_aplica_meta04_y_devuelve_el_estado_nuevo(tmp_path):
    """META-04: no se pudo determinar el nombre del tramite (sin AS-IS/TO-BE
    con titulo reconocible). El resolver de la SPA nunca tuvo un tipo `meta04`
    -- TarjetaHueco.tsx caia al boton generico de reconocer (sin control real
    para escribir el nombre), a diferencia de META-01/META-02 que si tienen
    ControlTexto. Este test fija el contrato que el frontend necesita."""
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    assert any(h["codigo"] == "META-04"
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={
        "resoluciones": [{"tipo": "meta04", "ubicacion": "metadatos",
                          "valor": "Constancia de residencia"}]})
    assert r.status_code == 200
    assert not any(h["codigo"] == "META-04" for h in r.json()["huecos"])
    assert r.json()["manifiesto"]["tramite"]["nombre"] == "Constancia de residencia"


def test_resolver_meta01_purga_el_hueco_aunque_la_ubicacion_no_sea_metadatos(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown"),
        "as_is": ("asis.md", _ASIS_SIN_TIEMPO.encode("utf-8"), "text/markdown"),
    }).json()["sid"]
    # el expediente arranca con un hueco META-01
    assert any(h["codigo"] == "META-01"
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])
    # el cliente manda una ubicacion que NO es "metadatos"
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={
        "resoluciones": [{"tipo": "meta01", "ubicacion": "otra-cosa", "valor": "3 dias"}]})
    assert r.status_code == 200
    # aun asi el hueco se tacha, en la respuesta y en huecos.json (al releer)
    assert not any(h["codigo"] == "META-01" for h in r.json()["huecos"])
    assert not any(h["codigo"] == "META-01"
                   for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])


def test_resolver_dic08_pone_la_condicion_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    # NOTA (Task 7b / Ruling 5): el campo base de la condicion debe estar
    # declarado en el manifiesto de _VIS ("tipo_solicitante", no el
    # "tipo_documento" original — ese nombre no lo declara ningun campo de
    # _VIS y con la validacion de Task 7b pasaria a dar 422, que es
    # justamente el caso que cubre test_resolver_dic08_condicion_con_campo_base_no_declarado_da_422).
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "tipo_solicitante", "igual": "persona_moral", "operador": "==",
                      "y": [{"campo": "es_persona_moral", "igual": "si"}]},
    }]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "DIC-08" and h["ubicacion"] == ubic
                   for h in body["huecos"])
    pantalla_id, campo = ubic.split("::", 1)
    p = next(pp for pp in body["manifiesto"]["pantallas"] if pp["id"] == pantalla_id)
    cv = next(cc for cc in p["campos"] if cc["nombre"] == campo)["condicion_visible"]
    assert cv["campo"] == "tipo_solicitante"
    assert cv["y"][0]["campo"] == "es_persona_moral"


def test_resolver_dic08_campo_inexistente_da_422(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": "p1::no_existe",
        "condicion": {"campo": "x", "igual": "y"}}]})
    assert r.status_code == 422 and "error" in r.json()


def test_resolver_dic08_condicion_con_campo_base_no_declarado_da_422(tmp_path):
    # La Condicion referencia un campo que NO esta declarado en el manifiesto
    # (spec 5.1: "422 ... si una Condicion referencia un campo no declarado").
    # No debe fijarse condicion_visible ni tacharse el hueco.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "campo_fantasma", "igual": "x"},
    }]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    assert "campo_fantasma" in r.json()["error"]
    # el hueco DIC-08 sigue vivo: la resolucion invalida no se aplico
    assert any(h["codigo"] == "DIC-08" and h["ubicacion"] == ubic
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])


def test_resolver_dic08_condicion_con_clausula_y_no_declarada_da_422(tmp_path):
    # El campo base SI esta declarado, pero una clausula `y` referencia un
    # campo que no lo esta.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")}).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "es_persona_moral", "igual": "si",
                      "y": [{"campo": "campo_fantasma", "igual": "x"}]},
    }]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    assert "campo_fantasma" in r.json()["error"]


# TO-BE con la compuerta G sin @@campo (variante MMD-04 de _TOBE_RAMA, igual
# que test_no_ramifica_si_la_compuerta_no_nombra_campo en
# test_extractor_expediente.py): el Diccionario declara "procede" en la
# Pantalla 2, así que "mmd04campo" con ese campo puede reensamblar el flujo.
_TOBE_MMD04 = _TOBE_RAMA.replace("{¿@@procede == 'si'?}", "{¿Procede?}")
_INSUMOS_CON_MMD04 = {
    "diccionario": ("dd.md", _DICC_RAMA.encode("utf-8"), "text/markdown"),
    "to_be": ("tobe.md", _TOBE_MMD04.encode("utf-8"), "text/markdown"),
}

# Variante de _TOBE_MMD04 sin `:::clase` en T1 (tarea) ni en G (compuerta):
# ambos disparan MMD-03. Con el gate sin @@campo, el flujo se queda en el
# respaldo lineal -- ahi la Tarea real de T1 es "t_p1" (por pantalla), no
# "T1" (el id del diagrama). Hallazgo post-sprint: resolver "mmd03" con
# ubicacion="T1" buscaba `t.id == "T1"` en `m.flujo.tareas`, nunca casaba, y
# devolvia 200 sin cambiar nada ni tachar el hueco -- un "exito" falso.
# Sin carril Y sin prefijo de actor en la etiqueta: desde que el extractor lee
# el prefijo («Solicitante: ...») como respaldo del carril, dejar el prefijo ya
# no produce hueco -- que es justo el punto. Para seguir probando la traduccion
# de ids hace falta una tarea de la que de verdad no se sepa quien la ejecuta.
_TOBE_MMD03 = (
    _TOBE_MMD04
    .replace("T1[Solicitante: Captura la solicitud]:::solicitante",
             "T1[Captura la solicitud]")
    .replace("G{¿Procede?}:::area", "G{¿Procede?}")
)
_INSUMOS_CON_MMD03 = {
    "diccionario": ("dd.md", _DICC_RAMA.encode("utf-8"), "text/markdown"),
    "to_be": ("tobe.md", _TOBE_MMD03.encode("utf-8"), "text/markdown"),
}


def test_mmd03_llega_colapsado_en_un_hueco_que_no_bloquea(tmp_path):
    """Desde que el carril del diagrama dejo de ser bloqueante (el actor de
    cada Tarea sale del Diccionario, no del `:::clase`), MMD-03 llega como un
    solo hueco `por_confirmar` sobre el flujo, no uno `falta_dato` por nodo.
    Ver `_colapsar_mmd03` en `extractores/expediente.py`."""
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD03).json()
    mmd03 = [h for h in est["huecos"] if h["codigo"] == "MMD-03"]
    assert len(mmd03) == 1, mmd03
    assert mmd03[0]["nivel"] == "por_confirmar"
    assert mmd03[0]["ubicacion"] == "flujo"
    # nombra el nodo, para poder revisarlo en el diagrama. La compuerta G no
    # aparece: desde f522eae una compuerta ya no pide actor.
    assert "T1" in mmd03[0]["mensaje"]
    assert "G" not in mmd03[0]["mensaje"].split(":")[1]
    # el .gpm ya no se atasca por el carril: MMD-03 no aparece entre los
    # bloqueantes de la puerta 409.
    g = c.get(f"/api/v1/expedientes/{est['sid']}/gpm")
    if g.status_code == 409:
        assert not any(h["codigo"] == "MMD-03" for h in g.json()["bloqueantes"])


def test_resolver_mmd03_traduce_el_id_del_diagrama_a_la_tarea_real(tmp_path):
    """El endpoint sigue aceptando un id de nodo del diagrama y escribiendo el
    actor en la Tarea real ("t_p1"), aunque el flujo haya salido lineal. Ya no
    hay un hueco por nodo que tachar, pero el contrato de `/resolver` no
    cambio: es la via para corregir a mano un actor mal leido."""
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD03).json()
    sid = est["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd03", "ubicacion": "T1", "valor": "solicitante"}]})
    assert r.status_code == 200, r.text
    tarea = next(t for t in r.json()["manifiesto"]["flujo"]["tareas"]
                 if t["id"] == "t_p1")
    assert tarea["actor"] == "solicitante"


def test_una_compuerta_ya_no_pide_actor(tmp_path):
    """Una compuerta es un punto de decision, no una tarea: nadie la 'ejecuta'.
    Preguntar quien la hace era un hueco imposible de contestar --  en
    Publicacion en el Periodico Oficial eran 3 de 42."""
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD03).json()

    assert not any(h["codigo"] == "MMD-03" and h["ubicacion"] == "G"
                   for h in est["huecos"]), est["huecos"]


def test_resolver_mmd03_sobre_una_compuerta_sigue_sin_reventar(tmp_path):
    """Ya no se emiten, pero una sesion vieja puede traer el hueco guardado en
    disco: el resolver tiene que seguir aceptandolo sin romperse."""
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD03).json()

    r = c.post(f"/api/v1/expedientes/{est['sid']}/resolver", json={"resoluciones": [{
        "tipo": "mmd03", "ubicacion": "G", "valor": "area"}]})

    assert r.status_code in (200, 422), r.text


def test_resolver_mmd03_id_desconocido_da_422(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD03).json()
    sid = est["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd03", "ubicacion": "no_existe", "valor": "solicitante"}]})
    assert r.status_code == 422
    assert "no_existe" in r.json()["error"]


def test_resolver_mmd04campo_reensambla_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "procede"}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "MMD-04" for h in body["huecos"])
    assert any(cx.get("cuando", {}).get("campo") == "procede"
               for cx in body["manifiesto"]["flujo"]["conexiones"])


def test_resolver_mmd04campo_campo_inexistente_da_422(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "no_existe"}]})
    assert r.status_code == 422


# ── Task 9: GET /compuerta/{gate_id} + resolver tipo mmd04rama ──


def test_leer_compuerta_devuelve_predecesora_y_ramas(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["predecesora"]
    assert len(body["ramas"]) >= 2 and all("a_nombre" in x for x in body["ramas"])
    assert c.get(f"/api/v1/expedientes/{sid}/compuerta/no_existe").status_code == 404


def test_leer_compuerta_sid_inexistente_da_404(tmp_path):
    r = _cli(tmp_path).get("/api/v1/expedientes/0123456789abcdef/compuerta/g1")
    assert r.status_code == 404
    assert "error" in r.json()


def test_resolver_mmd04rama_inyecta_condiciones_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    ramas = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}").json()["ramas"]
    payload = {"tipo": "mmd04rama", "ubicacion": gate, "ramas": [
        {"a": ramas[0]["a"], "condicion": {"campo": "procede", "igual": "si"}},
        {"a": ramas[1]["a"], "condicion": {"campo": "procede", "igual": "no"}},
    ]}
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [payload]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "MMD-04" for h in body["huecos"])
    cx = body["manifiesto"]["flujo"]["conexiones"]
    assert sum(1 for x in cx if x.get("cuando")) >= 2


def test_resolver_mmd04rama_rama_invalida_da_422(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04rama", "ubicacion": gate, "ramas": [
            {"a": "no_es_una_rama", "condicion": {"campo": "procede", "igual": "si"}},
        ]}]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    assert "no_es_una_rama" in r.json()["error"]
    # el hueco MMD-04 sigue vivo: la resolucion invalida no se aplico
    assert any(h["codigo"] == "MMD-04" and h["ubicacion"] == gate
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])


def test_resolver_mmd04rama_condicion_con_campo_no_declarado_da_422(tmp_path):
    # Ruling 5 (spec 5.1): una Condicion por rama que referencia un campo no
    # declarado en el manifiesto -> 422, sin mutar el flujo ni tachar el hueco.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    ramas = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}").json()["ramas"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04rama", "ubicacion": gate, "ramas": [
            {"a": ramas[0]["a"], "condicion": {"campo": "campo_fantasma", "igual": "si"}},
            {"a": ramas[1]["a"], "condicion": {"campo": "procede", "igual": "no"}},
        ]}]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    assert "campo_fantasma" in r.json()["error"]
    assert any(h["codigo"] == "MMD-04" and h["ubicacion"] == gate
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])


# ── T9b: Hallazgo 1 (traduccion de ids sin red de seguridad) + Hallazgo 2
# (tramo residual entre ramas hermanas) — review de Task 9 ──

# Variante de _TOBE_MMD04 donde el nodo T2 del Mermaid ya NO casa por nombre
# con ninguna pantalla del Diccionario (_DICC_RAMA sigue declarando "Cotiza").
# Reproduce exactamente el escenario que encontro el reviewer de T9:
# `_mapear_nodos_a_pantallas` falla (no 1:1), asi que la traduccion de
# CUALQUIER id (empezando por la predecesora) debe fallar.
_TOBE_MMD04_DESINCRONIZADO = _TOBE_MMD04.replace(
    "T2[Area: Cotiza]", "T2[Area: Cotizacion distinta]")
_INSUMOS_CON_MMD04_DESINCRONIZADO = {
    "diccionario": ("dd.md", _DICC_RAMA.encode("utf-8"), "text/markdown"),
    "to_be": ("tobe.md", _TOBE_MMD04_DESINCRONIZADO.encode("utf-8"), "text/markdown"),
}


def test_resolver_mmd04rama_con_id_no_traducible_da_422_sin_corromper(tmp_path):
    # Hallazgo 1 (review de T9): si `_mapear_nodos_a_pantallas` falla, la
    # traduccion NO puede caer en silencio al id crudo del Mermaid — eso deja
    # conexiones colgantes que se persisten a disco y revientan el siguiente
    # GET con una ValidationError no manejada. Debe dar 422 antes de mutar
    # `m.flujo.conexiones` o tachar el hueco.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04_DESINCRONIZADO).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    # GET /compuerta no traduce (solo expone ids del Mermaid): sigue en 200.
    ramas = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}").json()["ramas"]
    payload = {"tipo": "mmd04rama", "ubicacion": gate, "ramas": [
        {"a": ramas[0]["a"], "condicion": {"campo": "procede", "igual": "si"}},
        {"a": ramas[1]["a"], "condicion": {"campo": "procede", "igual": "no"}},
    ]}
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [payload]})
    assert r.status_code == 422, r.text
    assert "error" in r.json()
    # el hueco MMD-04 sigue vivo: la resolucion invalida no se aplico
    assert any(h["codigo"] == "MMD-04" and h["ubicacion"] == gate
               for h in c.get(f"/api/v1/expedientes/{sid}").json()["huecos"])
    # la sesion sigue siendo legible: el manifiesto NO se corrompio en disco
    r2 = c.get(f"/api/v1/expedientes/{sid}")
    assert r2.status_code == 200, r2.text


# Diccionario/TO-BE con 4 pantallas despues de la compuerta (2 por rama,
# encadenadas), para que el residuo entre ramas hermanas del respaldo lineal
# sea observable con mas de un salto: T2->T4->Fin (rama "si"),
# T3->T5->Fin (rama "no").
_DICC_RAMA2 = """### Pantalla 1 — SOLICITANTE — Captura la solicitud

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 | N/A | X | [Captura] `@@curp` |

### Pantalla 2 — AREA — Cotiza

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| ¿Procede? | Boolean | Radio Sí-No | Sí | Siempre visible | Sí · No | N/A | Sí | [Captura] `@@procede` |

### Pantalla 3 — AREA — Oficio de improcedencia

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| Motivo | String | Área de texto (textarea) | Sí | Siempre visible | 300 | N/A | X | [Captura] `@@motivo` |

### Pantalla 4 — AREA — Notifica aprobacion

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| Folio | String | Campo de texto (input) | Sí | Siempre visible | 20 | N/A | X | [Captura] `@@folio_aprobacion` |

### Pantalla 5 — AREA — Notifica rechazo

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| Folio | String | Campo de texto (input) | Sí | Siempre visible | 20 | N/A | X | [Captura] `@@folio_rechazo` |
"""

_TOBE_RAMA2 = """# Propuesta TO-BE

```mermaid
flowchart TD
    classDef solicitante fill:#eee
    classDef area fill:#eee
    Inicio([Inicio]):::solicitante --> T1[Solicitante: Captura la solicitud]:::solicitante
    T1 --> G{¿Procede?}:::area
    G -->|Sí| T2[Area: Cotiza]:::area
    G -->|No| T3[Area: Oficio de improcedencia]:::area
    T2 --> T4[Area: Notifica aprobacion]:::area
    T3 --> T5[Area: Notifica rechazo]:::area
    T4 --> Fin([Fin]):::area
    T5 --> Fin
```
"""

_INSUMOS_CON_MMD04_RAMA2 = {
    "diccionario": ("dd.md", _DICC_RAMA2.encode("utf-8"), "text/markdown"),
    "to_be": ("tobe.md", _TOBE_RAMA2.encode("utf-8"), "text/markdown"),
}


def test_resolver_mmd04rama_no_deja_residuo_entre_ramas_hermanas(tmp_path):
    # Hallazgo 2 (review de T9): el respaldo lineal conecta TODAS las
    # pantallas en el orden del Diccionario, ignorando el grafo Mermaid real.
    # Con ramas asimetricas encadenadas (T2->T4->Fin, T3->T5->Fin), si solo
    # se quita la conexion que salia de la predecesora, queda un tramo
    # residual que encadena tareas de ramas distintas entre si
    # (t_p2->t_p3->t_p4->t_p5) — exactamente el patron que documento la
    # review. Verifica el grafo resultante COMPLETO, no solo que el hueco MMD-04
    # se fue.
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04_RAMA2).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    ramas = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}").json()["ramas"]
    payload = {"tipo": "mmd04rama", "ubicacion": gate, "ramas": [
        {"a": ramas[0]["a"], "condicion": {"campo": "procede", "igual": "si"}},
        {"a": ramas[1]["a"], "condicion": {"campo": "procede", "igual": "no"}},
    ]}
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [payload]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "MMD-04" for h in body["huecos"])

    m = body["manifiesto"]

    def _tarea_de_pantalla(nombre_pantalla):
        pid = next(p["id"] for p in m["pantallas"] if p["nombre"] == nombre_pantalla)
        return next(t["id"] for t in m["flujo"]["tareas"]
                    if pid in [pp["id"] for pp in t["pantallas"]])

    rama_si = {_tarea_de_pantalla("Cotiza"), _tarea_de_pantalla("Notifica aprobacion")}
    rama_no = {_tarea_de_pantalla("Oficio de improcedencia"),
               _tarea_de_pantalla("Notifica rechazo")}

    for cx in m["flujo"]["conexiones"]:
        cruza = ((cx["de"] in rama_si and cx["a"] in rama_no)
                 or (cx["de"] in rama_no and cx["a"] in rama_si))
        assert not cruza, f"conexion residual entre ramas: {cx}"

    # las conexiones aguas abajo dentro de cada rama SI deben existir
    # (T2->T4, T3->T5 del grafo real), sin condicion.
    pares = {(cx["de"], cx["a"]) for cx in m["flujo"]["conexiones"]}
    assert (_tarea_de_pantalla("Cotiza"), _tarea_de_pantalla("Notifica aprobacion")) in pares
    assert (_tarea_de_pantalla("Oficio de improcedencia"),
            _tarea_de_pantalla("Notifica rechazo")) in pares


# ── T9c: tareas cuyo unico destino real es "Fin" deben quedar terminal=True ──


def test_resolver_mmd04rama_marca_terminal_las_tareas_sin_salida_real(tmp_path):
    # Hallazgo pendiente de T9b (confirmado Important por el reviewer): el
    # BFS aguas abajo hace `continue` sin generar Conexion cuando una arista
    # real llega a un nodo inicio_fin ("Fin"), pero no marca la Tarea de
    # origen como terminal=True. Resultado: esa Tarea queda sin ninguna
    # Conexion saliente Y con terminal=False (conserva el flag del armado
    # lineal original) — un callejon sin salida que pasa Manifiesto.
    # model_validate, compilar() y reglas.revisar() sin ningun aviso (la
    # tarea terminal sintetica t_fin, desconectada del grafo real, sigue
    # satisfaciendo la unica regla que exige "alguna" tarea terminal).
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04_RAMA2).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    ramas = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}").json()["ramas"]
    payload = {"tipo": "mmd04rama", "ubicacion": gate, "ramas": [
        {"a": ramas[0]["a"], "condicion": {"campo": "procede", "igual": "si"}},
        {"a": ramas[1]["a"], "condicion": {"campo": "procede", "igual": "no"}},
    ]}
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [payload]})
    assert r.status_code == 200, r.text
    m = r.json()["manifiesto"]

    tareas = m["flujo"]["tareas"]
    conexiones = m["flujo"]["conexiones"]
    ids_con_salida = {cx["de"] for cx in conexiones}

    # Invariante general: toda tarea alcanzable sin conexion saliente debe
    # ser terminal (nadie queda en un callejon sin salida).
    for t in tareas:
        if t["id"] not in ids_con_salida:
            assert t["terminal"] is True, (
                f"tarea '{t['id']}' ({t['nombre']}) no tiene conexion "
                f"saliente y no esta marcada terminal")

    # Assert explicito y nombrado: las dos tareas reales que terminan cada
    # rama ("Notifica aprobacion", "Notifica rechazo") van directo a Fin en
    # el diagrama, asi que deben quedar terminal=True.
    def _tarea_de_pantalla(nombre_pantalla):
        pid = next(p["id"] for p in m["pantallas"] if p["nombre"] == nombre_pantalla)
        return next(t for t in tareas if pid in [pp["id"] for pp in t["pantallas"]])

    assert _tarea_de_pantalla("Notifica aprobacion")["terminal"] is True
    assert _tarea_de_pantalla("Notifica rechazo")["terminal"] is True


def test_reconocer_marca_el_hueco_y_lo_devuelve(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/reconocer", json={"codigo": "INS-01", "ubicacion": ""})
    assert r.status_code == 200
    assert ["INS-01", ""] in r.json()["reconocidos"]


def test_leer_expediente_devuelve_lo_reconocido(tmp_path):
    """Sin esto la SPA pierde de vista lo reconocido en cuanto se recarga la
    pagina: el servidor lo conserva (la puerta del .gpm se levanta) pero el
    wizard vuelve a pintar el hueco como pendiente, y el analista cree que
    perdio su trabajo."""
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    c.post(f"/api/v1/expedientes/{sid}/reconocer", json={"codigo": "INS-01", "ubicacion": ""})

    r = c.get(f"/api/v1/expedientes/{sid}")

    assert r.status_code == 200
    assert ["INS-01", ""] in r.json()["reconocidos"]


def test_expediente_recien_creado_no_trae_nada_reconocido(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]

    assert c.get(f"/api/v1/expedientes/{sid}").json()["reconocidos"] == []


# ── Descarga del .gpm (puerta del linter) y del manifiesto ──

try:
    from tests.test_cli import _ASIS_LIMPIO, _TOBE_LIMPIO
except Exception:  # pragma: no cover - fallback si el import de paquete falla
    _ASIS_LIMPIO = ("---\ndependencia: Secretaría de Prueba\n---\n"
                    "# Análisis AS-IS — Trámite Limpio\n\n"
                    "**Tiempo de respuesta:** 5 días hábiles\n")
    _TOBE_LIMPIO = ("# Propuesta TO-BE — Trámite Limpio\n\n"
                    "```mermaid\nflowchart TD\n"
                    "    classDef solicitante fill:#eee\n"
                    "    Start([Inicio]):::solicitante --> T1[Solicitante: Datos]:::solicitante\n"
                    "    T1 --> Fin([Fin]):::solicitante\n```\n")

_DICC_LIMPIO = ("### Pantalla 1 — Solicitante — Datos\n\n"
                "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
                "| CURP | Texto | Input | Sí | La CURP `@@curp` |\n")


def test_gpm_bloqueado_da_409_con_lista(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 409
    assert any(b["codigo"] == "INS-01" for b in r.json()["bloqueantes"])


def test_gpm_se_descarga_cuando_no_hay_bloqueantes(tmp_path):
    # Diccionario + TO-BE lineal + AS-IS con dependencia y tiempo -> sin bloqueantes
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC_LIMPIO.encode("utf-8"), "text/markdown"),
        "as_is": ("asis.md", _ASIS_LIMPIO.encode("utf-8"), "text/markdown"),
        "to_be": ("tobe.md", _TOBE_LIMPIO.encode("utf-8"), "text/markdown"),
    }).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 200, r.text
    assert ".gpm" in r.headers["content-disposition"]
    assert len(r.content) > 0


def test_manifiesto_devuelve_el_yaml(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/manifiesto")
    assert r.status_code == 200
    assert "text/yaml" in r.headers["content-type"]
    assert "tramite:" in r.text


# ── Task 14: integración "cero clics" end-to-end (DIC-08 + MMD-04 juntos) ──

# Diccionario de _DICC_RAMA (T5/T9: 3 pantallas, compuerta "¿Procede?" sobre
# `@@procede`) con una fila adicional en la Pantalla 1 cuya condición de
# visibilidad no se puede interpretar (mismo texto que "Nota rara" de _VIS,
# ver test_extractor_diccionario.py) -> produce DIC-08 ademas de MMD-04.
_DICC_RAMA_CON_DIC08 = _DICC_RAMA.replace(
    "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 | N/A | X | [Captura] `@@curp` |",
    "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 | N/A | X | [Captura] `@@curp` |\n"
    "| Nota rara | String | Campo de texto | Condicional | Visible y obligatoria "
    "cuando `@@tipo_documento` ∈ {Acuerdo, Decreto, Ley} | N/A | N/A | N/A | "
    "[Captura] Campo `@@nota_rara`. |",
)

# TO-BE con la compuerta sin @@campo (misma variante que _TOBE_MMD04).
_TOBE_CON_DIC08_Y_MMD04 = _TOBE_RAMA.replace("{¿@@procede == 'si'?}", "{¿Procede?}")

# AS-IS con dependencia + tiempo de respuesta (mismo patron que _ASIS_LIMPIO
# de test_cli.py) para que META-01/META-02 no queden como huecos residuales
# `falta_dato` y tapen la puerta del linter con ruido ajeno a DIC-08/MMD-04.
_ASIS_CON_DIC08_Y_MMD04 = (
    "---\ndependencia: Secretaria de Prueba\n---\n"
    "# Analisis AS-IS - Cotizacion de Tramite\n\n"
    "**Tiempo de respuesta:** 5 dias habiles\n"
)

_INSUMOS_CON_DIC08_Y_MMD04 = {
    "diccionario": ("dd.md", _DICC_RAMA_CON_DIC08.encode("utf-8"), "text/markdown"),
    "as_is": ("asis.md", _ASIS_CON_DIC08_Y_MMD04.encode("utf-8"), "text/markdown"),
    "to_be": ("tobe.md", _TOBE_CON_DIC08_Y_MMD04.encode("utf-8"), "text/markdown"),
}


def test_cero_clics_dic08_y_mmd04_compila_gpm_completo(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_DIC08_Y_MMD04).json()
    sid = est["sid"]
    assert any(h["codigo"] == "DIC-08" for h in est["huecos"])
    assert any(h["codigo"] == "MMD-04" for h in est["huecos"])
    ub = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")

    # `curp` y no `procede`: `nota_rara` esta en la Pantalla 1 y `procede` se
    # captura en la 2, asi que esa condicion no se puede evaluar nunca. La
    # prueba la armaba asi desde el principio y pasaba porque nadie lo
    # comprobaba; con la validacion nueva da 422, que es lo correcto.
    r1 = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ub,
        "condicion": {"campo": "curp", "igual": "X", "operador": "=="}}]})
    assert r1.status_code == 200, r1.text
    assert not any(h["codigo"] == "DIC-08" for h in r1.json()["huecos"])

    r2 = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "procede"}]})
    assert r2.status_code == 200, r2.text
    huecos_tras_resolver = r2.json()["huecos"]
    assert not any(h["codigo"] == "MMD-04" for h in huecos_tras_resolver)
    assert not any(h["codigo"] == "DIC-08" for h in huecos_tras_resolver)
    # Ambos huecos resueltos y ningun `falta_dato` residual (solo quedan, si
    # acaso, huecos `por_confirmar` de metadatos, que nunca bloquean).
    assert not any(h["nivel"] == "falta_dato" for h in huecos_tras_resolver)

    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 200, r.text          # la puerta del linter ya deja pasar
    assert ".gpm" in r.headers["content-disposition"]
    assert len(r.content) > 0


def test_clasificar_reparte_una_carpeta_sin_subir_los_bytes(tmp_path):
    """`POST /clasificar` recibe solo nombres: es lo que permite que el
    navegador pinte el reparto antes de subir nada."""
    c = _cli(tmp_path)
    r = c.post("/api/v1/clasificar", json={"archivos": [
        "1.-Análisis AS-IS.md",
        "2.-As Is hasta media y una plana.pdf",
        "3.-Propuesta TO-BE.md",
        "5.-Diccionario de Datos.md",
        "Documentos/Oficio de improcedencia.pdf",
        "build_full_gpm.py",
    ]})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["as_is"] == "1.-Análisis AS-IS.md"
    assert b["to_be"] == "3.-Propuesta TO-BE.md"
    assert b["diccionario"] == "5.-Diccionario de Datos.md"
    # el PDF gemelo y el oficio escaneado son apoyo; el script se ignora
    assert "2.-As Is hasta media y una plana.pdf" in b["adjuntos"]
    assert "Documentos/Oficio de improcedencia.pdf" in b["adjuntos"]
    assert b["ignorados"] == ["build_full_gpm.py"]
    assert b["avisos"] == []


def test_clasificar_avisa_de_lo_que_no_pudo_decidir(tmp_path):
    c = _cli(tmp_path)
    r = c.post("/api/v1/clasificar", json={"archivos": ["notas sueltas.txt"]})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["diccionario"] is None
    assert any("Diccionario" in a for a in b["avisos"]), b["avisos"]


# ── Fase 2: propuestas de IA para DIC-08 ──
#
# Se usa `_VIS` (ya importado arriba), el Diccionario del repo que produce un
# DIC-08 real: `p1::nota_rara`, con `tipo_solicitante` (persona_fisica /
# persona_moral) capturado en la misma pantalla como candidato.
import json as _json

_UBIC = "p1::nota_rara"


def _respuesta_ok_api():
    return _json.dumps({"propuestas": [
        {"ubicacion": _UBIC,
         "condicion": {"campo": "tipo_solicitante", "operador": "==", "igual": "Persona moral", "y": []},
         "motivo": None, "confianza": "alta"}]})


def _cli_con_proveedor(tmp_path, respuestas):
    from gpmc.agentes.proveedor import ProveedorFalso
    return TestClient(crear_app(almacen=tmp_path, proveedor=ProveedorFalso(respuestas)))


def _subir(c):
    return c.post("/api/v1/expedientes", files={"diccionario": ("dd.md", _VIS.encode("utf-8"), "text/markdown")})


def test_sin_proveedor_no_hay_propuestas_y_el_estado_no_cambia(tmp_path):
    c = _cli(tmp_path)
    r = _subir(c)
    assert r.status_code == 201
    assert r.json()["propuestas_pendientes"] is False
    sid = r.json()["sid"]
    assert not (tmp_path / sid / "propuestas.json").exists()
    g = c.get(f"/api/v1/expedientes/{sid}/propuestas")
    assert g.status_code == 200 and g.json() == {"estado": "sin_proveedor", "motivo": None, "propuestas": []}


def test_con_proveedor_se_generan_en_segundo_plano_y_se_leen(tmp_path):
    c = _cli_con_proveedor(tmp_path, [_respuesta_ok_api()])
    r = _subir(c)
    assert r.status_code == 201, r.text
    assert any(h["codigo"] == "DIC-08" and h["ubicacion"] == _UBIC for h in r.json()["huecos"])
    assert r.json()["propuestas_pendientes"] is True
    sid = r.json()["sid"]
    # TestClient corre BackgroundTasks antes de devolver: ya esta listo
    g = c.get(f"/api/v1/expedientes/{sid}/propuestas").json()
    assert g["estado"] == "listo", g
    assert len(g["propuestas"]) == 1
    p = g["propuestas"][0]
    assert p["ubicacion"] == _UBIC and p["veredicto"] == "aceptable"
    assert p["cita"]["texto"].startswith("Visible y obligatoria cuando")
    assert p["cita"]["campo"] == "nota_rara" and p["cita"]["pantalla_nombre"] == "Datos"
    # normalizado al valor tecnico del catalogo, no a lo que escribio el modelo
    assert p["condicion"] == {"campo": "tipo_solicitante", "igual": "persona_moral", "operador": "==", "y": []}


def test_respuesta_invalida_deja_estado_error_sin_bloquear(tmp_path):
    c = _cli_con_proveedor(tmp_path, ["no json"])
    sid = _subir(c).json()["sid"]
    g = c.get(f"/api/v1/expedientes/{sid}/propuestas").json()
    assert g["estado"] == "error" and g["propuestas"] == [] and g["motivo"]
    # y el flujo normal sigue: resolver a mano funciona
    rr = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": _UBIC, "condicion": {"campo": "es_persona_moral", "igual": "si"}}]})
    assert rr.status_code == 200, rr.text


def test_decision_se_anota_y_no_toca_el_manifiesto(tmp_path):
    c = _cli_con_proveedor(tmp_path, [_respuesta_ok_api()])
    sid = _subir(c).json()["sid"]
    pid = c.get(f"/api/v1/expedientes/{sid}/propuestas").json()["propuestas"][0]["id"]
    antes = c.get(f"/api/v1/expedientes/{sid}").json()["manifiesto"]
    d = c.post(f"/api/v1/expedientes/{sid}/propuestas/{pid}/decision",
               json={"decision": "descartada", "condicion_final": None})
    assert d.status_code == 200 and d.json() == {"ok": True}
    assert c.get(f"/api/v1/expedientes/{sid}").json()["manifiesto"] == antes
    assert c.get(f"/api/v1/expedientes/{sid}/propuestas").json()["propuestas"] == []
    assert c.post(f"/api/v1/expedientes/{sid}/propuestas/{pid}/decision",
                  json={"decision": "aceptada", "condicion_final": None}).status_code == 409
    assert c.post(f"/api/v1/expedientes/{sid}/propuestas/no-existe/decision",
                  json={"decision": "aceptada", "condicion_final": None}).status_code == 404


def test_propuestas_rechazadas_por_filtro_no_se_listan(tmp_path):
    malo = _json.dumps({"propuestas": [
        {"ubicacion": _UBIC, "condicion": {"campo": "no_existe", "operador": "==", "igual": "x", "y": []},
         "motivo": None, "confianza": "alta"}]})
    c = _cli_con_proveedor(tmp_path, [malo])
    sid = _subir(c).json()["sid"]
    g = c.get(f"/api/v1/expedientes/{sid}/propuestas").json()
    assert g["estado"] == "listo" and g["propuestas"] == []


_DOS_PANTALLAS = """
### Pantalla 1 — CIUDADANO — Solicitud

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tipo de Solicitante | Select | Lista desplegable | Sí | Siempre visible | N/A | Persona física · Persona moral | Persona física | [Captura] Campo `@@tipo_solicitante`. |
| Vista de observaciones | String | Solo lectura | No | Visible solo si "¿Documentación Conforme?" = No | N/A | N/A | N/A | [Solo lectura] Campo `@@vista_observaciones`. |

### Pantalla 2 — DIRECCIÓN — Revisión

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ¿Documentación Conforme? | Boolean | Switch | Sí | Siempre visible | Sí / No | N/A | Sí | [Captura] Campo `@@documentacion_conforme`. |
"""


def _sid_dos_pantallas(c):
    return c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DOS_PANTALLAS.encode("utf-8"), "text/markdown"),
    }).json()["sid"]


def test_resolver_dic08_con_campo_de_pantalla_posterior_da_422(tmp_path):
    """Es el caso que trajo el expediente de Reposicion de Certificado: el campo
    de la pantalla 1 se condiciona contra uno que el funcionario captura en la
    pantalla 2. Cuando el ciudadano llena la primera, ese dato no existe todavia,
    asi que la regla no se puede evaluar nunca. El servidor la aceptaba: solo
    comprobaba que el campo estuviera declarado en ALGUNA pantalla."""
    c = _cli(tmp_path)
    sid = _sid_dos_pantallas(c)

    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": "p1::vista_observaciones",
        "condicion": {"campo": "documentacion_conforme", "igual": "no",
                      "operador": "==", "y": []}}]})

    assert r.status_code == 422, r.text
    assert "captura despu" in r.json()["error"]


def test_resolver_dic08_autorreferencia_da_422(tmp_path):
    """Un campo no puede decidir su propia visibilidad: la regla se muerde la
    cola. El filtro del generador de IA ya lo rechazaba; la via manual no."""
    c = _cli(tmp_path)
    sid = _sid_dos_pantallas(c)

    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": "p1::vista_observaciones",
        "condicion": {"campo": "vista_observaciones", "igual": "x",
                      "operador": "==", "y": []}}]})

    assert r.status_code == 422, r.text
    assert "mismo campo" in r.json()["error"]


def test_resolver_dic08_con_campo_de_la_misma_pantalla_sigue_valiendo(tmp_path):
    """El contrapeso: la validacion nueva no puede cerrar el caso normal."""
    c = _cli(tmp_path)
    sid = _sid_dos_pantallas(c)

    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": "p1::vista_observaciones",
        "condicion": {"campo": "tipo_solicitante", "igual": "persona_moral",
                      "operador": "==", "y": []}}]})

    assert r.status_code == 200, r.text


# ── El registro: que una anomalia se pueda leer despues ──
import logging as _logging


def test_un_defecto_nuestro_al_generar_propuestas_deja_su_traza(tmp_path, caplog):
    """`generar_propuestas` captura CUALQUIER excepcion para no tumbar la
    entrega, y solo guardaba el nombre de la clase en `propuestas.json`. Un
    fallo del proveedor deja detalle en `bitacora-ia.jsonl`; un defecto nuestro
    no dejaba traza en ningun sitio."""
    from gpmc.agentes.proveedor import ProveedorFalso

    class Roto(ProveedorFalso):
        def completar(self, instrucciones, contexto, esquema):
            raise RuntimeError("defecto nuestro, no del proveedor")

    c = TestClient(crear_app(almacen=tmp_path, proveedor=Roto([])))
    with caplog.at_level(_logging.INFO, logger="gpmc"):
        sid = _subir(c).json()["sid"]
    assert c.get(f"/api/v1/expedientes/{sid}/propuestas").json()["estado"] == "error"
    (rec,) = [r for r in caplog.records if r.levelno >= _logging.ERROR]
    assert rec.name.startswith("gpmc.") and sid in rec.getMessage()
    assert rec.exc_info is not None and "defecto nuestro" in str(rec.exc_info[1])


def test_extraer_deja_una_linea_con_la_sesion_y_los_conteos(tmp_path, caplog):
    c = _cli(tmp_path)
    with caplog.at_level(_logging.INFO, logger="gpmc"):
        r = _subir(c).json()
    lineas = [x.getMessage() for x in caplog.records if "extraido" in x.getMessage()]
    assert len(lineas) == 1, caplog.text
    assert f"sid={r['sid']}" in lineas[0]
    assert f"huecos={len(r['huecos'])}" in lineas[0] and "bloquean=" in lineas[0]


def test_el_registro_no_lleva_el_contenido_del_expediente(tmp_path, caplog):
    # El contrapeso: registrar «todo por si acaso» meteria en un archivo de
    # texto plano la prosa de un expediente. Van identificadores y conteos.
    c = _cli_con_proveedor(tmp_path, [_respuesta_ok_api()])
    with caplog.at_level(_logging.DEBUG, logger="gpmc"):
        _subir(c)
    assert "Visible y obligatoria cuando" in _VIS, "la prosa que NO debe aparecer"
    assert "Visible y obligatoria" not in caplog.text


def test_una_regla_rechazada_deja_su_motivo(tmp_path, caplog):
    c = _cli(tmp_path)
    sid = _sid_dos_pantallas(c)
    with caplog.at_level(_logging.INFO, logger="gpmc"):
        r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
            "tipo": "dic08", "ubicacion": "p1::vista_observaciones",
            "condicion": {"campo": "vista_observaciones", "igual": "x",
                          "operador": "==", "y": []}}]})
    assert r.status_code == 422
    (rec,) = [x for x in caplog.records if "rechazada" in x.getMessage()]
    assert rec.levelno == _logging.WARNING
    assert f"sid={sid}" in rec.getMessage() and "p1::vista_observaciones" in rec.getMessage()


def test_las_propuestas_generadas_dejan_sus_conteos(tmp_path, caplog):
    c = _cli_con_proveedor(tmp_path, [_respuesta_ok_api()])
    with caplog.at_level(_logging.INFO, logger="gpmc"):
        sid = _subir(c).json()["sid"]
    (linea,) = [x.getMessage() for x in caplog.records if "propuestas" in x.getMessage()]
    assert f"sid={sid}" in linea and "generadas=1" in linea and "aceptables=1" in linea
