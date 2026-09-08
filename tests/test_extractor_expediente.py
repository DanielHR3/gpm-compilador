from pathlib import Path

import pytest

from tests.conftest import WIKI, legible as _legible

from gpmc.extractores.expediente import extraer_expediente



EXPEDIENTES = [
    "anita/Alta de Avisos de Testamento",
    "elesvan/Constancia de No Infracción Vehicular Ambiental",
    "elesvan/Vinculación con Organismos Internacionales",
]


@pytest.mark.parametrize("nombre", EXPEDIENTES)
def test_produce_un_manifiesto_valido_de_un_expediente_real(nombre):
    carpeta = WIKI / nombre
    if not _legible(carpeta / "Diccionario de Datos.md"):
        pytest.skip(f"no disponible: {nombre}")
    r = extraer_expediente(carpeta)
    assert r.manifiesto is not None, \
        f"no se produjo manifiesto. huecos: {[str(h) for h in r.huecos][:5]}"
    m = r.manifiesto
    assert m.tramite.nombre
    assert m.actores, "sin actores"
    assert m.pantallas, "sin pantallas"
    assert any(t.inicial for t in m.flujo.tareas)
    assert any(t.terminal for t in m.flujo.tareas)


@pytest.mark.parametrize("nombre", EXPEDIENTES)
def test_el_manifiesto_extraido_compila_a_gpm(nombre):
    from gpmc.compilador.a_gpm import compilar
    from gpmc.nucleo.formato import serializar

    carpeta = WIKI / nombre
    if not _legible(carpeta / "Diccionario de Datos.md"):
        pytest.skip(f"no disponible: {nombre}")
    r = extraer_expediente(carpeta)
    if r.manifiesto is None:
        pytest.skip("sin manifiesto")
    g = compilar(r.manifiesto)
    texto = serializar(g)
    assert texto.startswith('{"id":')
    assert len(g["Formularios"]) == len(r.manifiesto.pantallas)


def test_siempre_reporta_huecos_de_un_expediente_real():
    """Un extractor que no reporta ningun hueco sobre material real esta
    inventando. Los 24 expedientes promedian ~10 huecos por diagrama."""
    carpeta = WIKI / EXPEDIENTES[0]
    if not _legible(carpeta / "Diccionario de Datos.md"):
        pytest.skip("no disponible")
    r = extraer_expediente(carpeta)
    assert r.huecos, "sospechoso: cero huecos sobre material real"


def test_falla_con_gracia_si_falta_un_insumo(tmp_path):
    (tmp_path / "Propuesta TO-BE.md").write_text("# vacio", encoding="utf-8")
    r = extraer_expediente(tmp_path)
    assert r.manifiesto is None
    assert any(h.codigo == "INS-03" for h in r.huecos)


def test_explica_el_bloqueo_de_permisos_de_macos(tmp_path, monkeypatch):
    """Un PermissionError crudo no le dice nada a un analista de proceso."""
    from gpmc.extractores.expediente import SinPermiso
    import gpmc.extractores.expediente as mod

    (tmp_path / "Diccionario de Datos.md").write_text("x", encoding="utf-8")
    original = Path.read_text

    def falla(self, *a, **k):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(Path, "read_text", falla)
    with pytest.raises(SinPermiso) as exc:
        mod.extraer_expediente(tmp_path)
    mensaje = str(exc.value)
    assert "Privacidad" in mensaje
    assert "Documentos" in mensaje
    monkeypatch.setattr(Path, "read_text", original)


_DICC_MINIMO = """### Pantalla 1 — Solicitante — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |
| CURP | Texto | Input de texto | Sí | La CURP del solicitante @@curp |
"""
_TOBE_MINIMO = """# Propuesta TO-BE

```mermaid
flowchart TD
  A([Inicio]):::ciudadano --> T1[Solicitante: Captura]:::ciudadano
  T1 --> F([Fin]):::ciudadano
```
"""


def _expediente(tmp_path, **archivos):
    """archivos: nombre_de_archivo -> contenido. Crea la carpeta y los escribe."""
    carpeta = tmp_path / "exp"
    carpeta.mkdir()
    for nombre, contenido in archivos.items():
        (carpeta / nombre).write_text(contenido, encoding="utf-8")
    return carpeta


def test_encuentra_el_tobe_pese_al_sufijo_uno(tmp_path):
    carpeta = _expediente(
        tmp_path,
        **{"5.-Diccionario de Datos.md": _DICC_MINIMO,
           "3.-Propuesta TO-BE 1.md": _TOBE_MINIMO},
    )
    r = extraer_expediente(carpeta)
    assert not [h for h in r.huecos if h.codigo == "INS-01"], \
        f"no debió reportar TO-BE faltante: {[str(h) for h in r.huecos]}"
    assert r.manifiesto is not None


@pytest.mark.parametrize("nombre_tobe", [
    "Propuesta TO-BE final.md", "propuesta_to_be_v2.md", "TO BE.md",
])
def test_encuentra_insumos_con_acentos_mayusculas_y_version(tmp_path, nombre_tobe):
    base = tmp_path / "c"
    base.mkdir()
    (base / "5.-Diccionario de Datos.md").write_text(_DICC_MINIMO, encoding="utf-8")
    (base / nombre_tobe).write_text(_TOBE_MINIMO, encoding="utf-8")
    r = extraer_expediente(base)
    assert not [h for h in r.huecos if h.codigo == "INS-01"], nombre_tobe


def test_dos_candidatos_de_tobe_no_adivina(tmp_path):
    carpeta = _expediente(
        tmp_path,
        **{"5.-Diccionario de Datos.md": _DICC_MINIMO,
           "Propuesta TO-BE.md": _TOBE_MINIMO,
           "TO-BE borrador.md": _TOBE_MINIMO},
    )
    r = extraer_expediente(carpeta)
    ins02 = [h for h in r.huecos if h.codigo == "INS-02"]
    assert ins02, [str(h) for h in r.huecos]
    assert ins02[0].nivel == "falta_dato"
    # y al no elegir, el flujo se comporta como si faltara: INS-01 bloqueante
    assert any(h.codigo == "INS-01" for h in r.huecos)


def test_sin_tobe_reporta_bloqueante_pero_produce_manifiesto(tmp_path):
    carpeta = _expediente(tmp_path, **{"5.-Diccionario de Datos.md": _DICC_MINIMO})
    r = extraer_expediente(carpeta)
    ins01 = [h for h in r.huecos if h.codigo == "INS-01"]
    assert ins01 and ins01[0].nivel == "bloqueante"
    assert r.manifiesto is not None            # flujo lineal


def test_ignora_pdfs_como_candidatos(tmp_path):
    carpeta = _expediente(
        tmp_path,
        **{"5.-Diccionario de Datos.md": _DICC_MINIMO,
           "Propuesta TO-BE.md": _TOBE_MINIMO},
    )
    (carpeta / "2.-Propuesta TO-BE escaneada.pdf").write_bytes(b"%PDF-1.4 ...")
    r = extraer_expediente(carpeta)
    assert not [h for h in r.huecos if h.codigo == "INS-02"]   # el pdf no cuenta


def test_normalizar_quita_prefijo_sufijo_y_acentos(tmp_path):
    from gpmc.extractores.expediente import _normalizar
    assert _normalizar("3.-Propuesta TO-BE 1.md") == _normalizar("propuesta to be")
    assert _normalizar("1.- Análisis AS-IS.md") == _normalizar("analisis as is")
    assert _normalizar("Diccionario_de_Datos (2).md") == _normalizar("diccionario de datos")


def test_todos_los_huecos_del_expediente_son_Hueco(tmp_path):
    from gpmc.nucleo.huecos import Hueco
    carpeta = _expediente(tmp_path, **{"5.-Diccionario de Datos.md": _DICC_MINIMO})
    r = extraer_expediente(carpeta)
    assert all(isinstance(h, Hueco) for h in r.huecos)


_DICC_API = """### Pantalla 1 — Solicitante — Domicilio

| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `estado_sol` | select | N/A | `mgee` (INEGI) | Catálogo. |
| `municipio_sol` | select | `estado_sol` | `mgem` (INEGI) | Cascada correcta. |
| `huerfano_sol` | select | `no_existe` | `mgem` (INEGI) | Padre inexistente. |
| `sin_padre_sol` | select | N/A | `mgem` (INEGI) | Cascada sin declarar padre. |
| `raro_sol` | select | N/A | `consultarfc` (SAT) | Endpoint no registrado. |
"""


def test_reporta_los_huecos_de_integracion(tmp_path):
    carpeta = tmp_path / "exp"
    carpeta.mkdir()
    (carpeta / "5.-Diccionario de Datos.md").write_text(_DICC_API, encoding="utf-8")
    r = extraer_expediente(carpeta)
    por_codigo = {}
    for h in r.huecos:
        por_codigo.setdefault(h.codigo, []).append(h)

    assert [h.mensaje for h in por_codigo.get("API-01", [])], "falta API-01 (endpoint desconocido)"
    assert [h.mensaje for h in por_codigo.get("API-02", [])], "falta API-02 (padre inexistente)"
    assert [h.mensaje for h in por_codigo.get("API-03", [])], "falta API-03 (cascada sin padre)"
    assert all(h.nivel == "falta_dato"
               for c in ("API-01", "API-02", "API-03") for h in por_codigo.get(c, []))


def test_una_cascada_bien_declarada_no_levanta_huecos_de_integracion(tmp_path):
    carpeta = tmp_path / "exp"
    carpeta.mkdir()
    (carpeta / "5.-Diccionario de Datos.md").write_text(_DICC_API, encoding="utf-8")
    r = extraer_expediente(carpeta)
    culpables = [h.ubicacion for h in r.huecos
                 if h.codigo in ("API-01", "API-02", "API-03")]
    assert "municipio_sol" not in culpables
    assert "estado_sol" not in culpables


def test_el_tramite_compila_pese_a_los_huecos_de_integracion(tmp_path):
    # Los huecos avisan; nunca tumban la extraccion.
    carpeta = tmp_path / "exp"
    carpeta.mkdir()
    (carpeta / "5.-Diccionario de Datos.md").write_text(_DICC_API, encoding="utf-8")
    r = extraer_expediente(carpeta)
    assert r.manifiesto is not None
    assert len(r.manifiesto.pantallas[0].campos) == 5


# ── Ramificación del flujo desde el Mermaid (spec 2026-09-03, Parte 2) ──

_DICC_RAMA = """### Pantalla 1 — SOLICITANTE — Captura la solicitud

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 | N/A | X | [Captura] `@@curp` |

### Pantalla 2 — AREA — Cotiza

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| ¿Procede? | Boolean | Radio Sí-No | Sí | Siempre visible | Sí · No | N/A | Sí | [Captura] `@@procede` |

### Pantalla 3 — AREA — Oficio de improcedencia

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| Motivo | String | Área de texto (textarea) | Sí | Siempre visible | 300 | N/A | X | [Captura] `@@motivo` |
"""

_TOBE_RAMA = """# Propuesta TO-BE

```mermaid
flowchart TD
    classDef solicitante fill:#eee
    classDef area fill:#eee
    Inicio([Inicio]):::solicitante --> T1[Solicitante: Captura la solicitud]:::solicitante
    T1 --> G{¿@@procede == 'si'?}:::area
    G -->|Sí| T2[Area: Cotiza]:::area
    G -->|No| T3[Area: Oficio de improcedencia]:::area
    T2 --> Fin([Fin]):::area
    T3 --> Fin
```
"""


def _cod(r):
    return {h.codigo for h in r.huecos}


def test_ramifica_el_flujo_cuando_la_compuerta_nombra_el_campo(tmp_path):
    carpeta = _expediente(tmp_path, **{
        "5.-Diccionario de Datos.md": _DICC_RAMA,
        "3.-Propuesta TO-BE.md": _TOBE_RAMA,
    })
    r = extraer_expediente(carpeta)
    assert "FLU-01" not in _cod(r), [str(h) for h in r.huecos]
    assert "FLU-03" in _cod(r)  # se ramificó; confírmese a mano
    m = r.manifiesto
    con_cond = [c for c in m.flujo.conexiones if c.cuando is not None]
    assert len(con_cond) == 2
    valores = {(c.cuando.campo, c.cuando.igual) for c in con_cond}
    assert valores == {("procede", "si"), ("procede", "no")}
    # las dos ramas salen de la misma tarea (la que precede a la compuerta)
    assert len({c.de for c in con_cond}) == 1


def test_el_flujo_ramificado_compila_y_valida(tmp_path):
    from gpmc.compilador.a_gpm import compilar
    from gpmc.validador.reglas import revisar
    carpeta = _expediente(tmp_path, **{
        "5.-Diccionario de Datos.md": _DICC_RAMA,
        "3.-Propuesta TO-BE.md": _TOBE_RAMA,
    })
    m = extraer_expediente(carpeta).manifiesto
    gpm = compilar(m)
    assert not [h for h in revisar(gpm) if h.gravedad == "bloqueante"]


def test_no_ramifica_si_la_compuerta_no_nombra_campo(tmp_path):
    tobe = _TOBE_RAMA.replace("{¿@@procede == 'si'?}", "{¿Procede?}")
    carpeta = _expediente(tmp_path, **{
        "5.-Diccionario de Datos.md": _DICC_RAMA, "3.-Propuesta TO-BE.md": tobe,
    })
    r = extraer_expediente(carpeta)
    assert "FLU-01" in _cod(r)
    assert all(c.cuando is None for c in r.manifiesto.flujo.conexiones)


def test_no_ramifica_si_el_campo_de_la_compuerta_no_existe(tmp_path):
    tobe = _TOBE_RAMA.replace("@@procede", "@@no_existe")
    carpeta = _expediente(tmp_path, **{
        "5.-Diccionario de Datos.md": _DICC_RAMA, "3.-Propuesta TO-BE.md": tobe,
    })
    r = extraer_expediente(carpeta)
    assert "FLU-01" in _cod(r)


def test_no_ramifica_si_una_etiqueta_de_arista_no_es_un_valor(tmp_path):
    tobe = _TOBE_RAMA.replace("|No|", "|Quizás|")
    carpeta = _expediente(tmp_path, **{
        "5.-Diccionario de Datos.md": _DICC_RAMA, "3.-Propuesta TO-BE.md": tobe,
    })
    r = extraer_expediente(carpeta)
    assert "FLU-01" in _cod(r)


def test_un_md_en_latin1_no_revienta_la_extraccion(tmp_path):
    """Un Diccionario guardado en Latin-1 (Word, editores viejos) se recuperaba
    con un traceback criptico. Ahora se lee con reemplazo y el flujo sigue."""
    carpeta = tmp_path / "exp"
    carpeta.mkdir()
    # 'ñ' y 'ó' existen en Latin-1 pero su byte 0xF1/0xF3 no es UTF-8 valido.
    contenido = ("### Pantalla 1 - Solicitante - Datos\n\n"
                 "| CURP | Texto | Input | Si | La CURP `@@curp` de la peticion, ano y nino |\n")
    (carpeta / "5.-Diccionario de Datos.md").write_bytes(
        contenido.replace("ano", "a\xf1o").replace("nino", "ni\xf1o").encode("latin-1"))
    r = extraer_expediente(carpeta)
    assert r.manifiesto is not None


def test_un_endpoint_con_token_se_reporta_como_API_05_no_API_01(tmp_path):
    """El diseño §7 contemplaba emitir el token en cliente; el CLAUDE.md lo
    revirtió (SEG-04). Un endpoint autenticado se reporta como API-05 con la
    vía correcta (Acción PHP a mano), no como 'endpoint desconocido'."""
    dicc = ("### Pantalla 1 — Solicitante — Datos\n\n"
            "| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| `rfc_sol` | select | N/A | `tlaloc_curp` | Autocompletar por CURP. |\n")
    carpeta = _expediente(tmp_path, **{"5.-Diccionario de Datos.md": dicc})
    r = extraer_expediente(carpeta)
    cods = {h.codigo for h in r.huecos}
    assert "API-05" in cods
    assert "API-01" not in cods
    a05 = next(h for h in r.huecos if h.codigo == "API-05")
    assert "token" in a05.mensaje.lower() and "SEG-04" in a05.mensaje
