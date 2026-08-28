# Fase 0 — Corrección de campos emitidos y de notas del diagrama · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un `select` compilado sea indistinguible del que produce la plataforma, que el Diccionario híbrido produzca los tipos y etiquetas correctos, y que las notas del diagrama dejen de contarse como tareas.

**Architecture:** Cuatro correcciones independientes entre sí, una por tarea. Dos tocan el compilador (`nucleo/esquema.py` + `compilador/a_gpm.py`), dos el extractor (`extractores/diccionario.py`, `extractores/mermaid.py`). Ninguna cambia una firma pública ni el orden de claves del formato `.gpm`. Las Tareas 2 y 3 tocan el mismo archivo y van en ese orden porque la 3 depende del `nombre` que fija la 2.

**Tech Stack:** Python 3.9+, `pydantic`, `pytest`. Sin dependencias nuevas.

**Spec:** `planeacion/specs/2026-08-28-fase-0-correccion-campos-y-notas.md`

## Global Constraints

- Python 3.9 compatible: nada de `X | None` en anotaciones, usar `Optional[X]`. `list[X]` sí se permite (el repo ya lo usa).
- Identificadores y nombres de módulo en español **sin acentos** (`nucleo`, `huecos`). Los textos dirigidos al usuario **sí** llevan acentos.
- Los comentarios explican *por qué*, no *qué*. Si un valor por omisión viene de un export real, el comentario lo dice.
- Ninguna función de `nucleo/` importa de `compilador`, `validador`, `web` ni `cli`.
- No tocar `nucleo/formato.py`, `validador/`, ni `SINTAXIS_ESTRICTA` en `nucleo/reglas.py`.
- No sobrescribir ningún archivo `.gpm` existente. Los archivos de referencia se leen, nunca se modifican.
- Nada se comitea sin que la suite pase: `.venv/bin/pytest -v`.
- Ejecutar con `.venv/bin/pytest` y `.venv/bin/python`, nunca el intérprete global.
- Los fixtures de prueba van **inline**. Ninguna prueba nueva puede depender de `~/Downloads` ni de `GPMC_WIKI`.
- Rama de trabajo: `fase-0-correccion-campos` (ya creada, ya contiene el spec).

---

### Task 1: El `select` declara su tipo de catálogo

**Files:**
- Modify: `src/gpmc/nucleo/esquema.py:26-61` (firma de `campo()` y la clave `catalogo_id`)
- Modify: `src/gpmc/compilador/a_gpm.py:41-62` (construcción de los campos del formulario)
- Test: `tests/test_compilador.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces:
  - `esquema.campo(..., catalogo_id=None)` — parámetro nuevo, último de la firma, valor por omisión `None`. La clave `"catalogo_id"` conserva su posición en el diccionario devuelto.
  - `a_gpm._campo_gpm(c, posicion, formulario_id, campo_id) -> dict` — función nueva a nivel de módulo que convierte un `Campo` del manifiesto en un campo del Form Builder.

- [ ] **Step 1: Write the failing tests**

Añade al final de `tests/test_compilador.py`:

```python
# Manifiesto minimo e inline: no depende de ejemplos/ ni de material real.
_CON_SELECT = """
tramite: {nombre: T, dependencia: D}
actores: [{id: u, nombre: U}]
pantallas:
- id: p1
  nombre: P
  actor: u
  campos:
  - {nombre: curp, etiqueta: CURP, tipo: text}
  - {nombre: sexo, etiqueta: Sexo, tipo: select, catalogo: [{etiqueta: Hombre, valor: h}]}
flujo:
  tareas:
  - {id: t1, nombre: T1, actor: u, inicial: true, pantallas: [{id: p1}]}
  - {id: tf, nombre: Fin, terminal: true}
  conexiones: [{de: t1, a: tf}]
"""


def _campos_de_prueba():
    import yaml
    from gpmc.nucleo.manifiesto import Manifiesto
    g = compilar(Manifiesto(**yaml.safe_load(_CON_SELECT)))
    return {c["nombre"]: c for c in g["Formularios"][0]["Campos"]}


def test_un_select_declara_su_tipo_de_catalogo():
    sexo = _campos_de_prueba()["sexo"]
    assert sexo["catalogo_id"] == "1"
    assert json.loads(sexo["extra"])["catalog_type"] == "manual"


def test_un_campo_que_no_es_select_no_declara_catalogo():
    curp = _campos_de_prueba()["curp"]
    assert curp["catalogo_id"] is None
    assert "catalog_type" not in json.loads(curp["extra"])


def test_el_select_conserva_el_ancho_y_sus_opciones():
    sexo = _campos_de_prueba()["sexo"]
    assert json.loads(sexo["extra"])["tamano"] == "col-xs-12 col-md-6"
    assert json.loads(sexo["datos"]) == [{"etiqueta": "Hombre", "valor": "h"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_compilador.py -v`
Expected: FAIL — `test_un_select_declara_su_tipo_de_catalogo` con `assert None == '1'`; el de `catalog_type` con `KeyError: 'catalog_type'`.

- [ ] **Step 3: Añadir `catalogo_id` a `esquema.campo()`**

En `src/gpmc/nucleo/esquema.py`, línea 26, agregar el parámetro al final de la firma:

```python
def campo(
    id, nombre, tipo, etiqueta, formulario_id, posicion,
    validacion="", datos=None, extra=None, readonly=False,
    valor_default="", ayuda=None, documento_id=None,
    dependiente_tipo=None, dependiente_campo="", dependiente_valor=None,
    catalogo_id=None,
):
```

Y en el diccionario devuelto (línea 53), sustituir la constante por el parámetro. **La clave no cambia de posición:**

```python
        "catalogo_id": catalogo_id,
```

- [ ] **Step 4: Extraer `_campo_gpm` en el compilador**

En `src/gpmc/compilador/a_gpm.py`, añadir esta función a nivel de módulo, junto a `_validacion_de`:

```python
def _campo_gpm(c, posicion, formulario_id, campo_id):
    """Un Campo del manifiesto -> un campo del Form Builder.

    Un select siempre declara de que tipo es su catalogo y siempre lleva
    catalogo_id "1": asi lo traen los dos exports autenticos, sin una sola
    excepcion. Sin catalog_type la vista de la plataforma revienta con
    "Undefined property: stdClass::$catalog_url" (CampoSelect.php).
    """
    extra = {"tamano": ANCHOS[c.ancho]}
    catalogo_id = None
    if c.tipo == "select":
        extra["catalog_type"] = "manual"
        catalogo_id = "1"
    return esquema.campo(
        id=str(campo_id),
        nombre=c.nombre,
        tipo=c.tipo,
        etiqueta=c.etiqueta or c.nombre,
        formulario_id=formulario_id,
        posicion=str(posicion),
        validacion=_validacion_de(c),
        datos=[o.model_dump() for o in c.catalogo] or None,
        extra=extra,
        readonly=c.solo_lectura,
        ayuda=c.ayuda,
        catalogo_id=catalogo_id,
    )
```

Luego sustituir la comprensión de las líneas 46-62 por:

```python
        campos = [
            _campo_gpm(c, i, fid, next(ids))
            for i, c in enumerate(pantalla.campos, start=1)
        ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_compilador.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS. Presta atención a `tests/test_esquema.py` y `tests/test_acciones.py`, que también llaman a `esquema.campo()`.

- [ ] **Step 7: Commit**

```bash
git add src/gpmc/nucleo/esquema.py src/gpmc/compilador/a_gpm.py tests/test_compilador.py
git commit -m "fix: el select emitido declara catalog_type y catalogo_id"
```

- [ ] **Step 8: Comprobación empírica en la plataforma (requiere una persona)**

**No bloquea el commit ni el resto del plan.** Es la única forma de cerrar una pregunta que no se resuelve leyendo archivos.

No tenemos el código de GPM: no podemos leer `CampoSelect.php` ni saber qué exige. Lo que sí tenemos es lo que la plataforma *produce*, y ahí la evidencia se contradice con la documentación interna:

| Fuente | Dice |
|---|---|
| Export auténtico (select manual) | `{"tamano": …, "catalog_type": "manual"}` — una sola clave |
| Bitácora del equipo, 2026-08-10 | `catalog_type`, `catalog_url`, `object_response`, `key_object` "requeridos aunque estén vacíos" |

Esta fase sigue al export. Para confirmarlo:

```bash
.venv/bin/gpmc compilar <un manifiesto con al menos un select> -o /tmp/prueba-select.gpm
```

Importar ese `.gpm` en `modelador.hidalgo.gob.mx` y abrir la pestaña **Vistas**.

- **Si el select se dibuja bien** → el export tenía razón; anotar el resultado en el spec y cerrar la contradicción.
- **Si aparece `Undefined property: stdClass::$catalog_url`** → la bitácora tenía razón; añadir `catalog_url`, `object_response` y `key_object` como cadenas vacías en `_campo_gpm`, con una prueba que lo fije y un comentario citando este hallazgo.

Es el mismo tipo de pregunta que `SINTAXIS_ESTRICTA`: se decide con una prueba en la plataforma, no con código. Mientras no exista esa prueba, el comportamiento actual es el que muestran los exports.

---

### Task 2: El tipo se lee también de la columna de tipo

**Files:**
- Modify: `src/gpmc/extractores/diccionario.py:78-83` (`_tipo_de`)
- Test: `tests/test_extractor_diccionario.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `_tipo_de(componente: str, tipo_dato: str) -> str` — misma firma, mismo nombre. Ahora consulta la tabla `COMPONENTES` contra ambas columnas, el componente primero.

- [ ] **Step 1: Write the failing tests**

Añade a `tests/test_extractor_diccionario.py`. El import de `_tipo_de` va junto a los que ya existen arriba del archivo:

```python
from gpmc.extractores.diccionario import extraer, _tipo_de


def test_el_tipo_se_lee_tambien_de_la_columna_de_tipo():
    # El Diccionario hibrido no trae columna de componente: su columna
    # "Tipo (GPM)" nombra directamente el tipo de la plataforma.
    assert _tipo_de("", "select") == "select"
    assert _tipo_de("", "file") == "file"
    assert _tipo_de("", "textarea") == "textarea"


def test_el_componente_gana_sobre_la_columna_de_tipo():
    # Cuando ambas columnas existen manda la mas especifica, como hasta hoy.
    assert _tipo_de("Lista desplegable (select)", "String") == "select"
    assert _tipo_de("Campo de texto (input)", "String") == "text"


def test_los_tipos_del_diccionario_estandar_no_cambian():
    # Guarda de regresion: los valores de la columna "Tipo de Dato" del
    # Diccionario estandar deben resolver igual que antes de este cambio.
    assert _tipo_de("", "String") == "text"
    assert _tipo_de("", "Number") == "text"
    assert _tipo_de("", "Archivo") == "file"


def test_el_diccionario_hibrido_produce_selects():
    r = extraer(_DICC_HIBRIDO)
    tipos = {c.nombre: c.tipo for c in r.pantallas[0].campos}
    assert tipos["estado_sol"] == "select"
    assert tipos["municipio_sol"] == "select"
    assert tipos["cp_sol"] == "text"
```

> Nota para el implementador: `_DICC_HIBRIDO` ya existe como constante de módulo en este archivo. Su columna es `| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |`, y declara `estado_sol` y `municipio_sol` como `select`, `cp_sol` como `text`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_extractor_diccionario.py -v`
Expected: FAIL — `test_el_tipo_se_lee_tambien_de_la_columna_de_tipo` con `assert 'text' == 'select'`.

- [ ] **Step 3: Write the implementation**

En `src/gpmc/extractores/diccionario.py`, sustituir `_tipo_de` completa:

```python
def _tipo_de(componente: str, tipo_dato: str) -> str:
    """El Diccionario estandar nombra el componente ("Lista desplegable
    (select)"); el hibrido nombra directamente el tipo de la plataforma
    ("select"). Se consultan ambas columnas contra la misma tabla, el
    componente primero para que la mas especifica gane."""
    for celda in (componente, tipo_dato):
        c = _babel(celda)
        for aguja, tipo in COMPONENTES:
            if _sin_acentos(aguja) in c:
                return tipo
    return "file" if "archivo" in _babel(tipo_dato) else "text"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_extractor_diccionario.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS. Si `tests/test_extractor_expediente.py` o `tests/test_web.py` cambian de resultado, es que un tipo se movió: investiga antes de seguir, no ablandes la aserción.

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/extractores/diccionario.py tests/test_extractor_diccionario.py
git commit -m "fix: el tipo de campo se lee tambien de la columna de tipo"
```

---

### Task 3: Etiqueta legible, propuesta y reportada (`DIC-05`)

**Files:**
- Modify: `src/gpmc/extractores/diccionario.py` (ruta de rescate, el bloque que decide `nombre` a partir de `etiqueta`)
- Test: `tests/test_extractor_diccionario.py`

**Interfaces:**
- Consumes: la variable local `es_columna_variable` y el `nombre` que fija la ruta de rescate (ya existentes en el archivo).
- Produces: hueco `DIC-05`, `nivel="por_confirmar"`, `ubicacion="p1"`, `propuesta=<etiqueta sugerida>`.

- [ ] **Step 1: Write the failing tests**

Añade a `tests/test_extractor_diccionario.py`:

```python
def test_la_etiqueta_visible_no_es_el_nombre_tecnico():
    # La plataforma distingue "Etiqueta" (lo que ve la persona) de "Nombre de
    # la variable". Con el Diccionario hibrido ambas salian iguales.
    r = extraer(_DICC_HIBRIDO)
    por_nombre = {c.nombre: c for c in r.pantallas[0].campos}
    assert por_nombre["estado_sol"].etiqueta == "Estado sol"
    assert por_nombre["estado_sol"].nombre == "estado_sol"


def test_la_etiqueta_derivada_se_reporta_como_DIC_05():
    r = extraer(_DICC_HIBRIDO)
    dic05 = [h for h in r.huecos if h.codigo == "DIC-05"]
    assert dic05, r.huecos
    assert dic05[0].nivel == "por_confirmar"
    assert dic05[0].propuesta
    assert dic05[0].ubicacion == "p1"


def test_el_diccionario_estandar_conserva_su_etiqueta():
    # Guarda de regresion: ahi la etiqueta ya es legible y no se toca.
    r = extraer(MUESTRA)
    assert r.pantallas[0].campos[0].etiqueta == "CURP"
    assert not [h for h in r.huecos if h.codigo == "DIC-05"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_extractor_diccionario.py -v`
Expected: FAIL — `assert 'estado_sol' == 'Estado sol'`.

- [ ] **Step 3: Write the implementation**

En `src/gpmc/extractores/diccionario.py`, ruta de rescate: **justo después** del bloque `if es_columna_variable ... elif tecnicos: ... else: ...` que fija `nombre`, y **antes** de la línea que lee `limite`, insertar:

```python
                # La plataforma distingue la etiqueta visible del nombre de la
                # variable. El Diccionario hibrido solo trae la segunda, asi que
                # se propone una legible y se levanta la mano — mismo trato que
                # DIC-01 le da al nombre tecnico, en el sentido contrario.
                if es_columna_variable and etiqueta == nombre:
                    legible = nombre.replace("_", " ").strip().capitalize()
                    r.huecos.append(Hueco(
                        "por_confirmar", "DIC-05", "p1",
                        f"'{nombre}' no trae etiqueta visible en el Diccionario; "
                        f"se propuso '{legible}'",
                        propuesta=legible,
                    ))
                    etiqueta = legible
```

La derivación es deliberadamente tonta: guiones bajos a espacios y primera letra en mayúscula. No se intentan reconocer siglas (CURP, RFC, CP) — eso sería inferencia sobre inferencia, y para eso está el hueco.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_extractor_diccionario.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/extractores/diccionario.py tests/test_extractor_diccionario.py
git commit -m "feat: etiqueta legible propuesta y reportada como DIC-05"
```

---

### Task 4: Las notas del diagrama dejan de ser tareas

**Files:**
- Modify: `src/gpmc/extractores/mermaid.py:56` (comentario de `clase_nodo`), `:88-110` (el bucle de nodos), `:139-143` (el hueco `MMD-03`)
- Test: `tests/test_extractor_mermaid.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `Nodo.clase_nodo` gana un cuarto valor, `"nota"`. `extraer()` conserva su firma. `expediente.py` no se toca: su conteo de `FLU-02` ya filtra por `clase_nodo == "tarea"`.

- [ ] **Step 1: Write the failing tests**

Añade a `tests/test_extractor_mermaid.py`:

```python
CON_NOTAS = """
flowchart TD
    classDef ciudadano fill:#E4EFEA
    classDef nota fill:#FFF8DC

    Start([Inicia]):::ciudadano --> C1[Ciudadano: Capturar]:::ciudadano
    C1 --> N1[/Nota importante: no existe recurso de revision/]:::nota
    N1 --> F1[Ciudadano: Concluir]:::ciudadano
    F1 -.-> N2[/Nota sin clase declarada/]
"""


def test_una_nota_no_es_una_tarea():
    r = extraer(CON_NOTAS)
    por_id = {n.id: n for n in r.nodos}
    assert por_id["N1"].clase_nodo == "nota"
    assert por_id["C1"].clase_nodo == "tarea"


def test_una_nota_se_reconoce_por_su_forma_aunque_no_declare_clase():
    r = extraer(CON_NOTAS)
    assert {n.id: n for n in r.nodos}["N2"].clase_nodo == "nota"


def test_el_texto_de_la_nota_pierde_las_barras():
    r = extraer(CON_NOTAS)
    texto = {n.id: n for n in r.nodos}["N1"].texto
    assert texto.startswith("Nota importante:")
    assert "/" not in texto


def test_las_notas_no_se_cuentan_como_tareas():
    r = extraer(CON_NOTAS)
    assert [n.id for n in r.nodos if n.clase_nodo == "tarea"] == ["C1", "F1"]


def test_una_nota_no_reclama_carril():
    # MMD-03 pide carril para saber que actor ejecuta el paso. Una anotacion
    # no la ejecuta nadie.
    r = extraer(CON_NOTAS)
    assert not [h for h in r.huecos if h.codigo == "MMD-03" and h.ubicacion == "N2"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_extractor_mermaid.py -v`
Expected: FAIL — `assert 'tarea' == 'nota'`.

- [ ] **Step 3: Write the implementation**

En `src/gpmc/extractores/mermaid.py`:

1. Línea 56, actualizar el comentario del campo:

```python
    clase_nodo: str          # "tarea" | "compuerta" | "inicio_fin" | "nota"
```

2. En el bucle de `extraer()`, sustituir la cadena `if/elif/else` que decide `clase_nodo` y la construcción del `Nodo` (líneas 88-110) por:

```python
    vistos: dict[str, Nodo] = {}
    for m in _NODO.finditer(bloque):
        if m["inicio"] is not None:
            clase_nodo, crudo = "inicio_fin", m["inicio"]
        elif m["compuerta"] is not None:
            clase_nodo, crudo = "compuerta", m["compuerta"]
        else:
            crudo = m["tarea"]
            # Los expedientes anotan el diagrama con la forma [/texto/] y el
            # carril 'nota'. Se aceptan ambas senales: la clase la declara
            # SINONIMOS, la forma cubre las notas que no declaran clase.
            recortado = (crudo or "").strip()
            es_nota = (
                normalizar_actor(m["clase"] or "") == "_nota"
                or (recortado.startswith("/") and recortado.endswith("/"))
            )
            clase_nodo = "nota" if es_nota else "tarea"

        nid = m["id"]
        if nid in vistos:
            if m["clase"] and not vistos[nid].actor:
                vistos[nid].actor = normalizar_actor(m["clase"])
            continue

        # A la nota no se le quita el prefijo de actor: "Nota importante:" no
        # nombra a quien ejecuta, y _limpiar se lo comeria.
        if clase_nodo == "nota":
            texto = (crudo or "").strip().strip("/").strip()
        else:
            texto = _limpiar(crudo)

        nodo = Nodo(
            id=nid,
            texto=texto,
            clase_nodo=clase_nodo,
            actor=normalizar_actor(m["clase"]) if m["clase"] else None,
            campos=_CAMPO.findall(crudo or ""),
        )
        vistos[nid] = nodo
        r.nodos.append(nodo)
```

3. En el bloque de huecos, el `MMD-03` (línea 139) debe saltarse las notas:

```python
    for n in r.nodos:
        if n.actor is None and n.clase_nodo not in ("inicio_fin", "nota"):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_extractor_mermaid.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 6: Verify against real material**

El archivo no vive en el repo, así que esto es una comprobación manual, no una prueba. Si el archivo no está, se salta el paso y se anota.

```bash
.venv/bin/python - <<'PY'
import re
from collections import Counter
from gpmc.extractores import mermaid as ext
ruta = "/Users/danielhernandezrubio/Downloads/Propuesta TO-BE (1).md"
bloque = re.search(r"```mermaid\n(.*?)```", open(ruta, encoding="utf-8").read(), re.S).group(1)
r = ext.extraer(bloque)
print(Counter(n.clase_nodo for n in r.nodos))
PY
```

Expected: `Counter({'tarea': 33, 'sistema...': ..., 'nota': 4, 'compuerta': 5, 'inicio_fin': 4})` — lo que importa es **`tarea: 33` y `nota: 4`**. Antes de este cambio decía `tarea: 37`.

- [ ] **Step 7: Commit**

```bash
git add src/gpmc/extractores/mermaid.py tests/test_extractor_mermaid.py
git commit -m "fix: las notas del diagrama no se cuentan como tareas"
```

---

## Self-Review

**1. Spec coverage:**

| Sección del spec | Task |
|---|---|
| §3.1 `select` con `catalog_type` y `catalogo_id` | Task 1 |
| §3.2 `_tipo_de` consulta ambas columnas | Task 2 |
| §3.3 etiqueta legible + `DIC-05` | Task 3 |
| §3.4 `clase_nodo == "nota"`, dos señales, `MMD-03` la salta | Task 4 |
| §4.1 pruebas del compilador | Task 1 steps 1-2 |
| §4.2 pruebas del diccionario (tipo y etiqueta) | Tasks 2 y 3, steps 1-2 |
| §4.3 pruebas de mermaid | Task 4 step 1 |
| §4.4 suite completa verde | Tasks 1-4, step "Run the full suite" |
| §6 criterios de aceptación 1-6 | 1→T1; 2→T2; 3→T3; 4→T4; 5→T4 step 6; 6→todas |
| §5 riesgo "`catalog_type: manual` podría no bastar" | Task 1 step 8 (comprobación empírica) |

Sin huecos de cobertura.

**Sobre trabajar sin el código de GPM.** Dos tasks descansan en inferencias sobre una
caja negra: Task 1 (qué exige la plataforma de un `select`) y Task 4 (qué significa la
forma `[/…/]`). Ninguna se puede cerrar leyendo archivos de este repo. Cada una lleva su
paso de comprobación contra material real —Task 1 step 8 contra la plataforma, Task 4
step 6 contra el TO-BE de SEMARNATH— y hasta que esos pasos se ejecuten, el criterio es
el mismo que gobierna `nucleo/formato.py`: manda lo que la plataforma **produce**, no lo
que la documentación **dice**.

**Nota sobre §4.1.** El spec pedía además una comparación contra el export de referencia ("las claves de `extra` de un select compilado son un subconjunto de las del select manual del export"). No se incluyó como prueba: `tests/test_compilador.py` no tiene hoy una fixture de exports auténticos, y montarla exigiría material bajo `GPMC_EXPORTS` que en un checkout limpio no está. La equivalencia queda fijada por los valores literales `"1"` y `"manual"` de la prueba de Task 1, que son exactamente los que muestra el export. Se anota como deuda menor, no como hueco de cobertura.

**2. Placeholder scan:** ningún `TBD`, ningún "añade manejo de errores" sin mostrar el código. Los tres pasos que dicen "sustituir X por Y" traen el bloque completo, no un fragmento. Las dos constantes reutilizadas de pruebas existentes (`_DICC_HIBRIDO` en Tasks 2-3, `MUESTRA` en Task 3) se nombran explícitamente con nota al implementador, incluida la forma de sus columnas.

**3. Type consistency:**
- `esquema.campo(..., catalogo_id=None)` — definido en Task 1 step 3, usado en Task 1 step 4. Último parámetro, coherente en ambos.
- `a_gpm._campo_gpm(c, posicion, formulario_id, campo_id)` — definido y usado solo en Task 1, mismo orden en definición y llamada.
- `_tipo_de(componente, tipo_dato) -> str` — firma intacta entre Tasks 2 y 3.
- `es_columna_variable` — variable local ya existente en `diccionario.py`; Task 3 la consume sin redefinirla.
- `clase_nodo` — el valor `"nota"` se introduce en Task 4 step 3 y se consume en las cinco pruebas del mismo step 1; `expediente.py` filtra por `"tarea"` y no requiere cambio.
- Códigos de hueco: `DIC-05` (nuevo, Task 3) no choca con `DIC-00..04`, `INS-*`, `META-*`, `FLU-*` ni `MMD-*` existentes.

---

## Execution Handoff

Plan completo y guardado en `planeacion/planes/2026-08-28-fase-0-correccion-campos-y-notas.md`. Dos formas de ejecutarlo:

1. **Subagente por tarea (recomendado)** — un subagente fresco por Task, con revisión entre tareas.
2. **En esta sesión** — ejecución por lotes con puntos de control (skill `executing-plans`).
