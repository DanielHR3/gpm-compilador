# Fase A — Catálogos remotos y APIs · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un `select` cuyo Diccionario declara un endpoint conocido compile a un catálogo remoto real —URL, nodo de respuesta y mapeo etiqueta/valor tomados del export auténtico— y que una cascada estado → municipio funcione.

**Architecture:** Un registro de endpoints en `nucleo/` (datos puros, sin red) resuelve lo único que el Diccionario no puede dar. El extractor normaliza lo que ya lee. El compilador traduce contra el registro. El simulador ejecuta los catálogos desde el navegador, que es donde la red está permitida.

**Tech Stack:** Python 3.9+, `dataclasses`, `pytest`. Sin dependencias nuevas. JavaScript sin librerías en el simulador.

**Spec:** `planeacion/specs/2026-08-28-fase-A-apis-y-catalogos.md`

## Global Constraints

- Python 3.9 compatible: nada de `X | None` en anotaciones, usar `Optional[X]`. `list[X]` sí se permite.
- Identificadores, módulos, comentarios y docstrings **en español sin acentos**. Los textos que lee una persona (mensaje de un `Hueco`, etiquetas del simulador) **sí** llevan acentos.
- Los comentarios explican *por qué*, no *qué*. Si un valor viene de un export real, el comentario lo dice.
- **`nucleo/` no importa de `compilador`, `validador`, `web` ni `cli`.** El registro va en `nucleo/` y no puede romper esa regla.
- **`nucleo/` no hace red.** El registro solo *sabe* URLs; ninguna función de Python las llama. Las peticiones ocurren en el navegador.
- No tocar `nucleo/formato.py`, `validador/`, ni `SINTAXIS_ESTRICTA`.
- No sobrescribir ningún `.gpm`. Los archivos de referencia se leen, nunca se modifican.
- Nada se comitea sin que la suite pase: `.venv/bin/pytest -v`. Baseline: **192 passed, 21 skipped, 1 warning** (el warning de `StarletteDeprecationWarning` es previo y no es tuyo).
- Ejecutar con `.venv/bin/pytest` y `.venv/bin/python`, nunca el intérprete global.
- Fixtures **inline**. **Ninguna prueba llama a la red** ni depende de `~/Downloads`, `GPMC_WIKI` o `GPMC_EXPORTS`.
- Rama de trabajo: `fase-0-correccion-campos` (ya contiene el spec).
- **No emitir el componente `api_ajax`.** Está fuera del alcance por el invariante de `CLAUDE.md` y por SEG-04. Se reporta como hueco `API-04` y nada más.

---

### Task 1: El registro de endpoints — `nucleo/integraciones.py`

**Files:**
- Create: `src/gpmc/nucleo/integraciones.py`
- Test: `tests/test_integraciones.py`

**Interfaces:**
- Consumes: nada (solo stdlib).
- Produces:
  - `@dataclass(frozen=True) class Catalogo` con `clave, proveedor, url, nodo, etiqueta, valor, requiere_padre`
  - `CATALOGOS: dict[str, Catalogo]`
  - `resolver(clave: str) -> Optional[Catalogo]` — insensible a mayúsculas y espacios; `None` si no está.
  - `Catalogo.url_para(padre: Optional[str]) -> str` — sustituye `{padre}` por el nombre del campo padre.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_integraciones.py
from gpmc.nucleo.integraciones import CATALOGOS, Catalogo, resolver


def test_los_tres_catalogos_verificados_estan_registrados():
    assert set(CATALOGOS) == {"mgee", "mgem", "zip_codes"}


def test_mgee_trae_la_url_y_el_mapeo_del_export_autentico():
    c = resolver("mgee")
    assert c.url == "https://gaia.inegi.org.mx/wscatgeo/v2/mgee"
    assert c.nodo == "datos"
    assert c.etiqueta == "nomgeo"
    assert c.valor == "cvegeo"
    assert c.requiere_padre is False


def test_mgem_requiere_padre_e_interpola_su_nombre():
    c = resolver("mgem")
    assert c.requiere_padre is True
    assert c.url_para("estado_sol") == (
        "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@estado_sol"
    )


def test_zip_codes_interpola_en_el_query_string():
    c = resolver("zip_codes")
    assert c.url_para("cp_sol") == (
        "https://sepomex.kurenn.dev/api/v1/zip_codes?zip_code=@@cp_sol"
    )
    assert c.nodo == "zip_codes"
    assert c.etiqueta == c.valor == "d_asenta"


def test_resolver_tolera_mayusculas_y_espacios():
    assert resolver("  MGEE ") is CATALOGOS["mgee"]


def test_un_endpoint_desconocido_devuelve_none_sin_reventar():
    assert resolver("consultarfc") is None
    assert resolver("") is None
    assert resolver(None) is None


def test_un_catalogo_sin_padre_ignora_el_argumento():
    assert resolver("mgee").url_para(None) == resolver("mgee").url_para("lo_que_sea")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_integraciones.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpmc.nucleo.integraciones'`

- [ ] **Step 3: Write the implementation**

```python
# src/gpmc/nucleo/integraciones.py
"""Endpoints de catalogo conocidos del gobierno de Hidalgo.

Datos puros: este modulo SABE urls, nunca las llama. La red vive en el
navegador, que es donde la plataforma tambien la hace. Asi el nucleo conserva
su invariante de no tener dependencias de red.

Cada entrada esta verificada dos veces: su forma sale del export autentico
'acceso-informacion-publica.gpm', y su respuesta se comprobo contra la API viva
el 2026-08-28.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Catalogo:
    clave: str            # como lo nombra el Diccionario: "mgem"
    proveedor: str        # informativo: "INEGI"
    url: str              # con {padre} si es en cascada
    nodo: str             # donde vive el arreglo en la respuesta
    etiqueta: str         # la clave que se MUESTRA
    valor: str            # la clave que se GUARDA
    requiere_padre: bool = False

    def url_para(self, padre: Optional[str]) -> str:
        """La URL lista para el .gpm. La plataforma interpola @@campo en tiempo
        de ejecucion, asi que aqui solo se sustituye el nombre del campo."""
        if not self.requiere_padre:
            return self.url
        return self.url.replace("{padre}", padre or "")


# La distincion etiqueta/valor es la que hace funcionar la cascada: estado_sol
# muestra "Hidalgo" pero guarda "13", y mgem/13 devuelve sus 84 municipios.
CATALOGOS = {
    c.clave: c
    for c in (
        Catalogo(
            clave="mgee", proveedor="INEGI",
            url="https://gaia.inegi.org.mx/wscatgeo/v2/mgee",
            nodo="datos", etiqueta="nomgeo", valor="cvegeo",
        ),
        Catalogo(
            clave="mgem", proveedor="INEGI",
            url="https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@{padre}",
            nodo="datos", etiqueta="nomgeo", valor="cvegeo",
            requiere_padre=True,
        ),
        Catalogo(
            clave="zip_codes", proveedor="SEPOMEX",
            url="https://sepomex.kurenn.dev/api/v1/zip_codes?zip_code=@@{padre}",
            nodo="zip_codes", etiqueta="d_asenta", valor="d_asenta",
            requiere_padre=True,
        ),
    )
}


def resolver(clave: Optional[str]) -> Optional[Catalogo]:
    """Un endpoint no registrado devuelve None: el compilador lo reporta como
    hueco API-01 en vez de inventar una URL."""
    return CATALOGOS.get((clave or "").strip().lower())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_integraciones.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Verificar que no rompiste la regla de dependencias**

Run: `grep -n "^from gpmc\|^import gpmc" src/gpmc/nucleo/integraciones.py`
Expected: sin salida. `nucleo/` no importa nada de `gpmc`.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/gpmc/nucleo/integraciones.py tests/test_integraciones.py
git commit -m "feat: registro de endpoints de catalogo conocidos en nucleo"
```

---

### Task 2: Normalizar lo que el extractor ya lee

**Files:**
- Modify: `src/gpmc/extractores/diccionario.py:204-235` (el bloque "Fase A: Parse dependencias y endpoint")
- Test: `tests/test_extractor_diccionario.py`

**Interfaces:**
- Consumes: nada de Task 1.
- Produces: `Campo.endpoint` con la clave desnuda (`"mgem"`), `Campo.dependencia_campo` sin acentos graves ni `@@`, y `dependencia_tipo == "api_ajax"` cuando la celda dice `api_ajax`. Hueco `API-04`, `por_confirmar`.

- [ ] **Step 1: Write the failing test**

`_DICC_HIBRIDO` ya existe como constante de módulo en ese archivo. Añade:

```python
def test_el_endpoint_queda_desnudo_sin_acentos_graves_ni_proveedor():
    # El Diccionario escribe "`mgem` (INEGI)"; el registro se busca por "mgem".
    r = extraer(_DICC_HIBRIDO)
    por_nombre = {c.nombre: c for c in r.pantallas[0].campos}
    assert por_nombre["estado_sol"].endpoint == "mgee"
    assert por_nombre["municipio_sol"].endpoint == "mgem"
    assert por_nombre["colonia_sol"].endpoint == "zip_codes"


def test_la_dependencia_de_campo_queda_desnuda():
    r = extraer(_DICC_HIBRIDO)
    municipio = {c.nombre: c for c in r.pantallas[0].campos}["municipio_sol"]
    assert municipio.dependencia_tipo == "campo"
    assert municipio.dependencia_campo == "estado_sol"


def test_api_ajax_es_su_propio_tipo_de_dependencia_no_un_campo():
    # 'api_ajax' en la columna Dependencia significa "lo llena una API", no
    # "depende de un campo llamado api_ajax".
    dicc = """# Hibrido

| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `nombres_sol` | text | `api_ajax` | `consultacurpn` (SIPUBEH) | Del nodo data.nombres. |
"""
    c = extraer(dicc).pantallas[0].campos[0]
    assert c.dependencia_tipo == "api_ajax"
    assert c.dependencia_campo is None
    assert c.endpoint == "consultacurpn"


def test_api_ajax_levanta_API_04():
    dicc = """# Hibrido

| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `nombres_sol` | text | `api_ajax` | `consultacurpn` (SIPUBEH) | Del nodo data.nombres. |
"""
    r = extraer(dicc)
    api04 = [h for h in r.huecos if h.codigo == "API-04"]
    assert api04, r.huecos
    assert api04[0].nivel == "por_confirmar"


def test_na_y_vacio_no_producen_dependencia():
    r = extraer(_DICC_HIBRIDO)
    estado = {c.nombre: c for c in r.pantallas[0].campos}["estado_sol"]
    assert estado.dependencia_tipo is None
    assert estado.dependencia_campo is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_extractor_diccionario.py -v`
Expected: FAIL — `assert '`mgee` (INEGI)' == 'mgee'` y `assert 'campo' == 'api_ajax'`.

- [ ] **Step 3: Write the implementation**

Añade estos dos ayudantes a nivel de módulo, junto a `_babel`:

```python
_ENDPOINT = re.compile(r"`?([\w/-]+)`?")


def _limpiar_celda(celda: str) -> str:
    """Quita acentos graves, asteriscos y espacios. El Diccionario escribe los
    identificadores entre acentos graves por costumbre de markdown."""
    return re.sub(r"[`*]", "", celda or "").strip()


def _clave_endpoint(celda: str) -> Optional[str]:
    """'`mgem` (INEGI)' -> 'mgem'. El proveedor entre parentesis es informativo:
    el registro de nucleo/integraciones ya sabe de quien es cada endpoint."""
    limpio = _limpiar_celda(celda)
    if not limpio or limpio.upper() == "N/A":
        return None
    m = _ENDPOINT.match(limpio)
    return m.group(1) if m else None
```

Y sustituye el bloque de las líneas ~204-222 por:

```python
        # Fase A: dependencia y endpoint, normalizados.
        dep_tipo = None
        dep_campo = None
        endpoint = None

        if i_dep is not None and i_dep < len(celdas):
            val_dep = _limpiar_celda(celdas[i_dep]).lstrip("@")
            if val_dep and val_dep.upper() != "N/A":
                if val_dep == "api_ajax":
                    # No es un campo padre: marca que a este campo lo llena una
                    # peticion. Esta fase no emite el componente (ver spec §6).
                    dep_tipo = "api_ajax"
                    r.huecos.append(Hueco(
                        "por_confirmar", "API-04", pantalla.id,
                        f"'{nombre}' se autocompleta por API; esta versión no emite "
                        f"el componente y el campo queda de captura manual",
                    ))
                else:
                    dep_tipo = "campo"
                    dep_campo = val_dep

        if i_end is not None and i_end < len(celdas):
            endpoint = _clave_endpoint(celdas[i_end])
```

> El resto del bloque (la construcción de `Campo(...)` con `dependencia_tipo=dep_tipo` etc.) no cambia.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_extractor_diccionario.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/extractores/diccionario.py tests/test_extractor_diccionario.py
git commit -m "fix: normaliza endpoint y dependencia; api_ajax es su propio tipo (API-04)"
```

---

### Task 3: Emitir el catálogo remoto contra el export auténtico

**Files:**
- Modify: `src/gpmc/compilador/a_gpm.py`, función `_campo_gpm`
- Test: `tests/test_compilador.py`

**Interfaces:**
- Consumes: `from gpmc.nucleo.integraciones import resolver` (Task 1); `Campo.endpoint` y `Campo.dependencia_campo` ya normalizados (Task 2).
- Produces: un `select` con endpoint conocido emite `catalog_type:"url"`, `catalog_url`, `object_response`, `key_object`, y `catalogo_id:"1"`. En cascada añade `dependent_populated:"1"` y `populated_by:[padre]`. Huecos `API-01`, `API-02`, `API-03` — **pero los emite el extractor, no el compilador**; ver la nota al final de esta tarea.

**Lo que hay que corregir.** `_campo_gpm` ya intenta emitir catálogos remotos, con cinco desviaciones del export auténtico, verificadas:

| | Hoy emite | Export auténtico |
|---|---|---|
| `catalogo_id` | `None` | `"1"` |
| `catalog_url` | la celda cruda, `` `mgee` (INEGI) `` | la URL real |
| `object_response` | `"data"` | `"datos"` |
| `key_object` | `"valor"` | `"nomgeo, cvegeo"` |
| `value_object` | clave inventada | no existe en ningún export |

El `catalogo_id: None` **regresa la garantía que fijó la Fase 0** ("un select siempre lleva `catalogo_id` 1", verificado contra los dos exports auténticos).

- [ ] **Step 1: Write the failing tests**

```python
_CON_REMOTO = """
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: estado_sol, etiqueta: Estado, tipo: select, endpoint: mgee}
  - {nombre: municipio_sol, etiqueta: Municipio, tipo: select, endpoint: mgem,
     dependencia_tipo: campo, dependencia_campo: estado_sol}
  - {nombre: sexo, etiqueta: Sexo, tipo: select, catalogo: [{etiqueta: H, valor: h}]}
  - {nombre: raro, etiqueta: Raro, tipo: select, endpoint: consultarfc}
flujo:
  tareas:
  - {id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]}
  - {id: tf, nombre: Fin, terminal: true}
  conexiones: [{de: t1, a: tf}]
"""


def _campos_remotos():
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    g = compilar(Manifiesto(**yaml.safe_load(_CON_REMOTO)))
    return {c["nombre"]: c for c in g["Formularios"][0]["Campos"]}


def test_un_catalogo_remoto_usa_la_url_del_registro():
    e = json.loads(_campos_remotos()["estado_sol"]["extra"])
    assert e["catalog_type"] == "url"
    assert e["catalog_url"] == "https://gaia.inegi.org.mx/wscatgeo/v2/mgee"
    assert e["object_response"] == "datos"
    assert e["key_object"] == "nomgeo, cvegeo"
    assert "value_object" not in e          # esa clave no existe en ningun export


def test_un_catalogo_remoto_conserva_catalogo_id():
    # La Fase 0 fijo que todo select lleva catalogo_id "1". Un catalogo remoto
    # sigue siendo un select.
    assert _campos_remotos()["estado_sol"]["catalogo_id"] == "1"


def test_una_cascada_interpola_el_padre_y_lo_declara():
    e = json.loads(_campos_remotos()["municipio_sol"]["extra"])
    assert e["catalog_url"] == (
        "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@estado_sol"
    )
    assert e["dependent_populated"] == "1"
    assert e["populated_by"] == ["estado_sol"]


def test_un_endpoint_desconocido_cae_a_catalogo_manual():
    c = _campos_remotos()["raro"]
    e = json.loads(c["extra"])
    assert e["catalog_type"] == "manual"
    assert "catalog_url" not in e
    assert c["catalogo_id"] == "1"


def test_el_catalogo_manual_sigue_igual_que_en_la_fase_0():
    c = _campos_remotos()["sexo"]
    assert json.loads(c["extra"])["catalog_type"] == "manual"
    assert c["catalogo_id"] == "1"


def test_las_claves_coinciden_con_el_export_autentico():
    # Comparado contra municipio_sol del export real, que es la cascada. Se
    # excluye 'accion_id': lo asigna la plataforma, no lo emitimos nosotros.
    e = json.loads(_campos_remotos()["municipio_sol"]["extra"])
    esperadas = {"tamano", "catalog_type", "catalog_url", "object_response",
                 "key_object", "dependent_populated", "populated_by"}
    assert set(e) == esperadas
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_compilador.py -v`
Expected: FAIL — `assert '`mgee` (INEGI)' == 'https://...'` y `assert None == '1'`.

- [ ] **Step 3: Write the implementation**

Import junto a los demás en `a_gpm.py`:

```python
from gpmc.nucleo.integraciones import resolver as _resolver_catalogo
```

Y sustituye el bloque `if c.tipo == "select": ...` de `_campo_gpm` por:

```python
    if c.tipo == "select":
        # Un select siempre lleva catalogo_id "1", sea manual o remoto: asi lo
        # traen los dos exports autenticos, sin excepcion.
        catalogo_id = "1"
        cat = _resolver_catalogo(c.endpoint) if c.endpoint else None
        if cat is None:
            extra["catalog_type"] = "manual"
        else:
            # Forma copiada de acceso-informacion-publica.gpm. 'key_object' es
            # una sola cadena "etiqueta, valor", no dos claves: se reproduce tal
            # cual en vez de "mejorarla".
            extra["catalog_type"] = "url"
            extra["catalog_url"] = cat.url_para(c.dependencia_campo)
            extra["object_response"] = cat.nodo
            extra["key_object"] = f"{cat.etiqueta}, {cat.valor}"
            if cat.requiere_padre and c.dependencia_campo:
                extra["dependent_populated"] = "1"
                extra["populated_by"] = [c.dependencia_campo]
```

Y **borra** el bloque que fijaba `dependiente_tipo` / `dependiente_campo` a nivel del campo: en el export auténtico esas claves van vacías incluso en la cascada. La dependencia viaja dentro de `extra`, no en la raíz del campo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_compilador.py -v`
Expected: PASS

- [ ] **Step 5: Comparar contra el export auténtico (se salta si no está)**

```bash
.venv/bin/python - <<'PY'
import json, pathlib
ruta = pathlib.Path.home() / "Desktop/Projects/GPM/Acceso a la Informacion/acceso-informacion-publica.gpm"
if not ruta.exists():
    print("export de referencia no disponible — paso omitido"); raise SystemExit
d = json.load(open(ruta))
for f in d["Formularios"]:
    for c in (f.get("campos") or f.get("Campos") or []):
        if c["nombre"] == "municipio_sol":
            print("referencia:", sorted(json.loads(c["extra"])))
PY
```

Expected: las claves de la referencia son las de la prueba más `tamano`. Anota cualquier diferencia en el reporte.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/gpmc/compilador/a_gpm.py tests/test_compilador.py
git commit -m "fix: el catalogo remoto se emite con la forma del export autentico"
```

> **Nota sobre `API-01`, `API-02` y `API-03`.** El compilador no levanta huecos —los `Hueco` nacen en los extractores, y `a_gpm.py` no tiene un `Resultado` donde ponerlos. Esos tres códigos se emiten en `extractores/expediente.py`, que sí tiene la lista de campos y la lista de pantallas para comprobarlos. Va en la Task 4.

---

### Task 4: Los huecos de integración — `API-01`, `API-02`, `API-03`

**Files:**
- Modify: `src/gpmc/extractores/expediente.py` (tras construir `pantallas`, antes de armar el flujo)
- Test: `tests/test_extractor_expediente.py`

**Interfaces:**
- Consumes: `from gpmc.nucleo.integraciones import resolver` (Task 1); los campos ya normalizados (Task 2).
- Produces: tres huecos nuevos, todos `falta_dato`, con `ubicacion` = el id de la pantalla.

- [ ] **Step 1: Write the failing test**

```python
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
```

> Nota para el implementador: en esas pruebas la `ubicacion` del hueco es el **nombre del campo**, no el id de la pantalla — así el analista sabe cuál revisar. Ajusta el mensaje para que nombre el campo y el endpoint.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_extractor_expediente.py -v`
Expected: FAIL — `falta API-01 (endpoint desconocido)`.

- [ ] **Step 3: Write the implementation**

Import en `expediente.py`:

```python
from gpmc.nucleo.integraciones import resolver as _resolver_catalogo
```

Y tras el bucle que construye `pantallas` (justo antes de armar `tareas`):

```python
    # Huecos de integracion: se comprueban aqui y no en el compilador porque
    # aqui estan a la vez el campo, su pantalla y sus vecinos.
    for p in pantallas:
        nombres = {c.nombre for c in p.campos}
        for c in p.campos:
            if not c.endpoint:
                continue
            cat = _resolver_catalogo(c.endpoint)
            if cat is None:
                r.huecos.append(Hueco(
                    "falta_dato", "API-01", c.nombre,
                    f"el endpoint '{c.endpoint}' no está en el registro de catálogos "
                    f"conocidos; el campo se emite como lista vacía",
                ))
                continue
            if cat.requiere_padre and not c.dependencia_campo:
                r.huecos.append(Hueco(
                    "falta_dato", "API-03", c.nombre,
                    f"el catálogo '{cat.clave}' se puebla a partir de otro campo, "
                    f"pero no se declaró de cuál depende",
                ))
            elif c.dependencia_campo and c.dependencia_campo not in nombres:
                r.huecos.append(Hueco(
                    "falta_dato", "API-02", c.nombre,
                    f"depende del campo '{c.dependencia_campo}', que no existe en "
                    f"la pantalla '{p.nombre}'",
                ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_extractor_expediente.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/extractores/expediente.py tests/test_extractor_expediente.py
git commit -m "feat: huecos de integracion API-01, API-02 y API-03"
```

---

### Task 5: El simulador ejecuta los catálogos

**Files:**
- Modify: `src/gpmc/simulador/html.py` (el diccionario `pantallas` de `generar`, y el guion JS)
- Test: `tests/test_simulador.py`

**Interfaces:**
- Consumes: `from gpmc.nucleo.integraciones import resolver` (Task 1).
- Produces: cada campo del JSON del navegador gana `catalogo_url`, `catalogo_nodo`, `catalogo_etiqueta`, `catalogo_valor` y `depende_de` cuando su endpoint resuelve. Un `select` sin catálogo resoluble se dibuja `<select disabled>`.

- [ ] **Step 1: Write the failing test**

```python
def test_el_simulador_lleva_la_url_del_catalogo_remoto():
    m = _manifiesto_con_catalogo_remoto()      # helper del step 3
    html = generar(m)
    assert "https://gaia.inegi.org.mx/wscatgeo/v2/mgee" in html
    assert '"catalogo_nodo": "datos"' in html or '"catalogo_nodo":"datos"' in html


def test_el_simulador_declara_de_quien_depende_una_cascada():
    html = generar(_manifiesto_con_catalogo_remoto())
    assert "estado_sol" in html
    assert "depende_de" in html


def test_un_select_sin_catalogo_resoluble_sale_deshabilitado_no_como_texto():
    # El simulador no puede mentir sobre lo que hara la plataforma: un campo
    # que es un desplegable se dibuja como desplegable, aunque este vacio.
    html = generar(_manifiesto_con_select_sin_catalogo())
    assert "disabled" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_simulador.py -v`
Expected: FAIL — la URL no aparece en el HTML.

- [ ] **Step 3: Write the implementation**

En `generar`, al construir el dict `pantallas`, añade por campo:

```python
                 **_catalogo_de_campo(c),
```

con este ayudante a nivel de módulo:

```python
def _catalogo_de_campo(c) -> dict:
    """Lo que el navegador necesita para poblar un select remoto. Sin endpoint
    resoluble devuelve un dict vacio y el campo se dibuja deshabilitado."""
    cat = resolver(c.endpoint) if c.endpoint else None
    if cat is None:
        return {}
    return {
        "catalogo_url": cat.url_para(c.dependencia_campo).replace(
            f"@@{c.dependencia_campo}", "{padre}"
        ) if cat.requiere_padre else cat.url,
        "catalogo_nodo": cat.nodo,
        "catalogo_etiqueta": cat.etiqueta,
        "catalogo_valor": cat.valor,
        "depende_de": c.dependencia_campo,
    }
```

Y en el guion JS, tras `pintar()`, añade el poblado:

```javascript
async function poblar(campo, el, valorPadre){
  if(!campo.catalogo_url){return}
  let url=campo.catalogo_url;
  if(campo.depende_de){
    if(!valorPadre){el.disabled=true;return}
    url=url.replace("{padre}",encodeURIComponent(valorPadre));
  }
  el.disabled=true;
  try{
    const res=await fetch(url);
    const datos=(await res.json())[campo.catalogo_nodo]||[];
    el.innerHTML='<option value="">— elegir —</option>'+datos.map(o=>
      `<option value="${o[campo.catalogo_valor]}">${o[campo.catalogo_etiqueta]}</option>`
    ).join("");
    el.disabled=false;
  }catch(e){
    el.innerHTML='<option value="">(no se pudo consultar el catálogo)</option>';
  }
}
function conectarCatalogos(campos){
  campos.forEach(c=>{
    const el=document.querySelector(`[name="${c.nombre}"]`);
    if(!el||!c.catalogo_url){return}
    if(c.depende_de){
      const padre=document.querySelector(`[name="${c.depende_de}"]`);
      if(padre){padre.addEventListener("change",()=>poblar(c,el,padre.value))}
      poblar(c,el,padre?padre.value:"");
    }else{
      poblar(c,el,null);
    }
  });
}
```

Llama a `conectarCatalogos(campos_de_la_tarea)` al final de `pintar()`, y en el renderizado de campos dibuja `<select>` —no `<input>`— cuando `c.tipo === "select"`, con `disabled` si no hay opciones ni `catalogo_url`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_simulador.py -v`
Expected: PASS

- [ ] **Step 5: Comprobación manual en el navegador**

```bash
.venv/bin/gpmc servir --puerto 8011 &
```

Subir el expediente de *Acceso a la Información* y abrir el simulador. Verificar: `estado_sol` se puebla solo con los 32 estados; al elegir "Hidalgo", `municipio_sol` se puebla con sus 84 municipios. Anotar el resultado real en el reporte, incluido el caso de fallo si la red no responde.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/gpmc/simulador/html.py tests/test_simulador.py
git commit -m "feat: el simulador puebla los catalogos remotos y encadena las cascadas"
```

---

## Self-Review

**1. Spec coverage:**

| Sección del spec | Task |
|---|---|
| §3 registro de endpoints en `nucleo/` | Task 1 |
| §4 normalización de las dos columnas | Task 2 |
| §5 emisión al `.gpm`, catálogo remoto y cascada | Task 3 |
| §5 huecos `API-01/02/03` | Task 4 |
| §5 hueco `API-04` | Task 2 |
| §6 `api_ajax` fuera de alcance | Task 2 (solo levanta `API-04`, no emite el componente) |
| §7 el simulador ejecuta los catálogos; cierra P-02 | Task 5 |
| §8 plan de pruebas | Tasks 1-5, cada una con las suyas |
| §10 criterios 1-6 | 1→T3; 2→T3 step 1 y step 5; 3→T3+T4; 4→T2; 5→T5; 6→todas |

Sin huecos de cobertura.

**2. Placeholder scan:** ningún `TBD`. Los cinco pasos que dicen "sustituye X por Y" traen el bloque completo. La constante `_DICC_HIBRIDO` reutilizada en Task 2 se nombra explícitamente con nota al implementador. Los dos helpers de Task 5 (`_manifiesto_con_catalogo_remoto`, `_manifiesto_con_select_sin_catalogo`) los escribe el implementador en el step 3 — se señala así en el propio step, no se dan por existentes.

**3. Type consistency:**
- `Catalogo(clave, proveedor, url, nodo, etiqueta, valor, requiere_padre)` — definido en Task 1, consumido en Tasks 3, 4 y 5 con esos nombres.
- `resolver(clave) -> Optional[Catalogo]` — misma firma en las cuatro tasks que la usan; importada con alias `_resolver_catalogo` en `a_gpm.py` y `expediente.py` para no chocar con nombres locales.
- `Catalogo.url_para(padre)` — definido en Task 1, usado en Tasks 3 y 5.
- `Campo.endpoint` / `Campo.dependencia_campo` / `Campo.dependencia_tipo` — ya existen en `manifiesto.py`; Task 2 cambia su *contenido*, no su tipo.
- Códigos de hueco: `API-01/02/03` (Task 4) y `API-04` (Task 2) no chocan con `INS-*`, `DIC-*`, `META-*`, `FLU-*` ni `MMD-*`.

**4. Riesgo de orden:** Task 3 y Task 4 importan el registro de Task 1, así que Task 1 va primero. Task 3 depende de que Task 2 haya desnudado el `endpoint` (si no, `resolver("`mgee` (INEGI)")` devuelve `None` y todo cae a manual). El orden 1 → 2 → 3 → 4 → 5 no es negociable.

---

## Execution Handoff

Plan completo y guardado en `planeacion/planes/2026-08-29-fase-A-apis-y-catalogos.md`. Dos formas de ejecutarlo:

1. **Subagente por tarea (recomendado)** — un subagente fresco por Task, con revisión entre tareas.
2. **En esta sesión** — ejecución por lotes con puntos de control (skill `executing-plans`).
