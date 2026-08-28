# Fase 0 — Corrección de campos emitidos y de notas del diagrama

- **Fecha:** 2026-08-28
- **Estado:** aprobado, pendiente de plan de implementación
- **Alcance:** `src/gpmc/nucleo/esquema.py`, `src/gpmc/compilador/a_gpm.py`,
  `src/gpmc/extractores/diccionario.py`, `src/gpmc/extractores/mermaid.py`, pruebas.
- **Fuera de alcance:** catálogos remotos y `api_ajax` (Fase A), simulador con APIs
  (Fase B), roles y bandeja del servidor público (Fase C), `SINTAXIS_ESTRICTA`,
  `nucleo/formato.py`, `validador/`.

## 1. Contexto y problema

Cuatro defectos preexistentes salieron a la luz al importar a la plataforma un `.gpm`
generado desde un Diccionario de Datos en formato "híbrido" (el del trámite *Acceso a la
Información*) y al pasar por el extractor una Propuesta TO-BE real de dependencia
(*Declaratoria de Áreas Naturales Protegidas*, SEMARNATH).

Los cuatro son **prerrequisito** del trabajo de integración con APIs: no se puede colgar un
catálogo remoto de un campo que ni siquiera se emite como `select`.

### 1.1 Los `select` se emiten sin metadata de catálogo

`compilador/a_gpm.py` emite para todo campo:

```python
extra={"tamano": ANCHOS[c.ancho]}
```

y `nucleo/esquema.py :: campo()` fija `"catalogo_id": None` sin excepción.

Los **dos** exports auténticos disponibles coinciden, sin una sola excepción, en que un
campo `select`:

- lleva `catalogo_id: "1"` (los demás tipos lo llevan en `null`), y
- lleva `catalog_type` dentro de `extra`.

| Export | tipo | `catalogo_id` | claves de `extra` (sin `tamano`) |
|---|---|---|---|
| acceso-informacion-publica | `select` | `"1"` | `catalog_type` |
| acceso-informacion-publica | `select` | `"1"` | `catalog_type`, `catalog_url`, `object_response`, `key_object`, `dependent_populated`, `populated_by` |
| permiso-para-conducir | `select` | `"1"` | `catalog_type`, `catalog_url`, `object_response`, `key_object`, `accion_id`, `attributes` |
| ambos | `text`, `file`, `textarea`, `radio`, `paragraph`, `api_ajax` | `null` | (varias, nunca `catalog_type`) |

La bitácora del equipo del 2026-08-10 cataloga esto como **error #3 de importación**:
`Undefined property: stdClass::$catalog_url` en `CampoSelect.php`.

**Consecuencia:** todo `.gpm` que este compilador haya producido con un campo `select`
puede reventar la vista al abrirse en la plataforma.

### 1.2 La columna de tipo del Diccionario se ignora

`extractores/diccionario.py :: _tipo_de` resuelve el tipo consultando **solo** la columna
*Componente Sugerido (GPM)*. Su respaldo únicamente detecta la palabra "archivo":

```python
def _tipo_de(componente: str, tipo_dato: str) -> str:
    c = _babel(componente)
    for aguja, tipo in COMPONENTES:
        if _sin_acentos(aguja) in c:
            return tipo
    return "file" if "archivo" in _babel(tipo_dato) else "text"
```

El Diccionario híbrido no trae columna de componente: trae `Tipo (GPM)` con los valores
`select`, `text`, `file` — que es exactamente el vocabulario de la plataforma. Como
`componente` viene vacío, todo cae al respaldo y **todo sale `text`**.

Verificado: `_tipo_de("", "select") == "text"`.

**Consecuencia:** `estado_sol`, `municipio_sol` y `colonia_sol` se importan como cajas de
texto en vez de listas desplegables.

### 1.3 La etiqueta visible es el nombre técnico

En la ruta de rescate del Diccionario híbrido, la etiqueta se toma de la misma celda que el
nombre técnico. El resultado es un formulario cuya etiqueta visible dice
`curp_solicitante`, cuando la plataforma distingue explícitamente los dos conceptos
(**Etiqueta** y **Nombre de la variable**) en su editor de campo.

### 1.4 Las notas del diagrama se cuentan como tareas

`extractores/mermaid.py` ya reconoce el carril de anotación —`SINONIMOS` mapea
`"nota" → "_nota"`— pero nada aguas abajo usa esa marca: los nodos siguen naciendo con
`clase_nodo="tarea"`.

En el TO-BE de SEMARNATH hay 4 nodos `[/Nota importante: …/]` con `:::nota`. El extractor
produce 46 nodos, de los cuales cuenta **37 tareas** cuando las tareas reales son **33**.

**Consecuencia:** las tareas no entran al manifiesto (se construyen desde el Diccionario,
`expediente.py:160`), pero el hueco `FLU-02` reporta una correspondencia falsa entre
diagrama y Diccionario.

## 2. Objetivo

Que lo que el compilador emite coincida con lo que la plataforma produce, y que lo que el
extractor reporta sea cierto. Métricas:

1. Un `select` compilado es indistinguible —en `catalogo_id` y en las claves de `extra`—
   de un select manual del export de referencia.
2. Un Diccionario híbrido que declara `select` produce un campo `select`.
3. Ninguna etiqueta visible es igual a su nombre técnico sin que se levante un hueco.
4. `FLU-02` cuenta 33 tareas en el diagrama de SEMARNATH, no 37.

## 3. Diseño

### 3.1 `select` con metadata de catálogo

En `nucleo/esquema.py :: campo()`, `catalogo_id` deja de ser una constante y pasa a ser
parámetro con valor por omisión `None`. La posición de la clave en el diccionario **no
cambia**: la firma del export se conserva.

En `compilador/a_gpm.py`, al armar un campo:

```python
extra = {"tamano": ANCHOS[c.ancho]}
catalogo_id = None
if c.tipo == "select":
    # Ambos exports autenticos: un select siempre declara de que tipo es su
    # catalogo y siempre lleva catalogo_id "1". Sin catalog_type, CampoSelect.php
    # revienta con "Undefined property: stdClass::$catalog_url".
    extra["catalog_type"] = "manual"
    catalogo_id = "1"
```

**Solo `manual` en esta fase.** El `catalog_type: "url"` y sus cuatro claves acompañantes
son materia de la Fase A.

**Contradicción documentada, no resuelta.** La bitácora del 2026-08-10 sostiene que
`catalog_url`, `object_response` y `key_object` son *"requeridos aunque estén vacíos"*. El
select manual del export auténtico trae **únicamente** `{"tamano": …, "catalog_type":
"manual"}`. Esta fase sigue al export, por la misma regla que gobierna `nucleo/formato.py`:
cuando la documentación y el archivo de referencia se contradicen, manda el archivo. Si la
plataforma rechaza el resultado, es un hallazgo empírico que se anota y se corrige — no se
anticipa inventando claves que el export no muestra.

### 3.2 `_tipo_de` consulta también la columna de tipo

```python
def _tipo_de(componente: str, tipo_dato: str) -> str:
    """El Diccionario estandar nombra el componente ("Lista desplegable (select)");
    el hibrido nombra directamente el tipo de la plataforma ("select"). Se
    consultan ambas columnas contra la misma tabla antes de caer al respaldo."""
    for celda in (componente, tipo_dato):
        c = _babel(celda)
        for aguja, tipo in COMPONENTES:
            if _sin_acentos(aguja) in c:
                return tipo
    return "file" if "archivo" in _babel(tipo_dato) else "text"
```

**Sin regresión.** El Diccionario estándar trae `Tipo de Dato` con valores `String`,
`Number`, `Archivo`. `String` y `Number` no casan ninguna aguja de `COMPONENTES` y siguen
cayendo en `"text"`; `Archivo` casa la aguja `"archivo"` y devuelve `"file"`, que es lo
mismo que devolvía el respaldo. El orden importa: el componente se consulta primero, así
que cuando ambas columnas existen gana la más específica, como hoy.

### 3.3 Etiqueta legible, propuesta y reportada

En la ruta de rescate de `diccionario.py`, cuando la etiqueta coincide con el nombre
técnico se deriva una legible y se levanta un hueco:

```python
if es_columna_variable and etiqueta == nombre:
    legible = nombre.replace("_", " ").strip().capitalize()
    r.huecos.append(Hueco(
        "por_confirmar", "DIC-05", "p1",
        f"'{nombre}' no trae etiqueta visible en el Diccionario; se propuso "
        f"'{legible}'",
        propuesta=legible,
    ))
    etiqueta = legible
```

La derivación es deliberadamente tonta: guiones bajos a espacios y primera letra en
mayúscula. `curp_solicitante` → `Curp solicitante`. No se intenta reconocer siglas (CURP,
RFC, CP): eso sería inferencia sobre inferencia. El hueco existe precisamente para que una
persona lo corrija.

Es el mismo trato que `DIC-01` da al nombre técnico —proponer algo usable y levantar la
mano—, ahora en el sentido contrario.

**Código nuevo:**

| Código | Origen | Nivel | Nota |
|---|---|---|---|
| `DIC-05` | diccionario | `por_confirmar` | sin etiqueta visible; se propuso una derivada del nombre técnico. `propuesta` = la etiqueta sugerida |

### 3.4 Las notas dejan de ser tareas

`clase_nodo` gana un cuarto valor: `"nota"`. Un nodo es nota si se cumple cualquiera de las
dos señales:

1. su carril normaliza a `_nota` (la marca que `SINONIMOS` ya produce), o
2. su texto viene delimitado por barras — `[/texto/]`, la forma de Mermaid que los
   expedientes usan para anotar.

La segunda señal cubre los diagramas que dibujan la nota sin declararle clase. El texto se
guarda sin las barras.

En `expediente.py`, el conteo de `FLU-02` ya filtra por `clase_nodo == "tarea"`, así que
deja de contarlas sin tocar esa línea.

**Alcance deliberadamente corto.** Los 10 nodos con carril `sistema` del TO-BE de SEMARNATH
tampoco son tareas humanas con pantalla, pero excluirlos es una decisión de diseño del
flujo, no una corrección de un defecto. Queda como limitación conocida.

## 4. Plan de pruebas (TDD: primero la prueba que falla)

Todos los fixtures van **inline**. Ninguna prueba de esta fase depende de material en
`~/Downloads` ni de `GPMC_WIKI`.

### 4.1 `tests/test_compilador.py`

- Un manifiesto con un campo `select` y catálogo manual compila a un campo con
  `catalogo_id == "1"` y `json.loads(extra)["catalog_type"] == "manual"`.
- Un campo `text` del mismo manifiesto conserva `catalogo_id is None` y **no** trae
  `catalog_type`.
- Comparación contra material real (se salta si no está disponible): las claves de `extra`
  de un select compilado son un subconjunto de las del select manual del export de
  referencia.

### 4.2 `tests/test_extractor_diccionario.py`

- `_tipo_de("", "select") == "select"`; `("", "file") == "file"`; `("", "text") == "text"`.
- Regresión: `_tipo_de("Lista desplegable (select)", "String") == "select"` y
  `_tipo_de("", "String") == "text"`.
- Un Diccionario híbrido con `Tipo (GPM) = select` produce campos con `tipo == "select"`.
- La etiqueta de un campo del Diccionario híbrido **no** es igual a su nombre, y existe un
  `DIC-05` `por_confirmar` con `propuesta` no vacía.

### 4.3 `tests/test_extractor_mermaid.py`

- Un diagrama con `classDef nota` y un nodo `N1[/Nota importante: x/]:::nota` produce ese
  nodo con `clase_nodo == "nota"`, y el texto sin las barras.
- Un nodo `[/texto/]` **sin** clase declarada también sale como `"nota"`.
- El conteo de `clase_nodo == "tarea"` excluye las notas.

### 4.4 Regresión

- Suite completa verde, incluida la prueba de ida y vuelta byte-exacta de
  `nucleo/formato.py` (esta fase no la toca): `.venv/bin/pytest -v`.

## 5. Riesgos

- **`catalog_type: "manual"` podría no bastar.** La documentación interna pide cuatro
  claves; el export solo muestra una. Mitigación: se sigue el export y se anota la
  contradicción; la prueba empírica es importar un `.gpm` con un select a la plataforma.
- **`_tipo_de` consultando dos columnas podría cambiar un tipo ya correcto.** Mitigación:
  el componente se consulta primero, y las pruebas de regresión fijan el comportamiento del
  Diccionario estándar antes de tocar la función.
- **La señal `[/…/]` podría marcar como nota un nodo que no lo es.** En Mermaid esa forma
  también se usa para entrada/salida. Mitigación: en los expedientes disponibles solo
  aparece para anotaciones; el riesgo se acepta y se documenta.
- **`catalogo_id` como parámetro nuevo en `esquema.campo()`.** Mitigación: valor por
  omisión `None`, posición de la clave intacta; ningún llamador existente cambia de
  comportamiento.

## 6. Criterios de aceptación

1. Un `select` compilado trae `catalogo_id == "1"` y `catalog_type == "manual"` en `extra`;
   un `text` del mismo manifiesto no trae ninguno de los dos.
2. Un Diccionario híbrido con `Tipo (GPM) = select` produce campos `select`.
3. Ninguna etiqueta visible del Diccionario híbrido es igual a su nombre técnico; cada caso
   derivado levanta un `DIC-05` con `propuesta`.
4. Un nodo `[/Nota …/]` sale con `clase_nodo == "nota"` y no se cuenta como tarea.
5. Sobre el TO-BE de *Declaratoria de Áreas Naturales Protegidas*: 33 tareas, 4 notas.
6. `.venv/bin/pytest -v` en verde.

## 7. Lo que sigue (fuera de esta fase)

Diseño ya acordado con el responsable técnico, pendiente de spec propio:

- **Fase A** — el manifiesto aprende de APIs: registro de endpoints conocidos en
  `nucleo/integraciones.py` (INEGI `mgee`/`mgem`, SEPOMEX `zip_codes`, SIPUBEH
  `consultacurpn`, los cuatro verificados contra las APIs vivas), `Campo` gana
  `catalogo_remoto` y `consulta`, el extractor lee las columnas `Dependencia` y
  `Endpoint / API`, y el compilador emite `catalog_type: "url"` y `api_ajax`.
  **Regla de seguridad:** solo se emiten endpoints públicos; uno que requiera credencial
  —RENAPO, SAT— se reporta como hueco y se manda a una Acción PHP, por SEG-04
  ("fuga de secretos en las peticiones AJAX del navegador").
- **Fase B** — el simulador ejecuta esos catálogos y autollenados. Los tres endpoints
  verificados responden `Access-Control-Allow-Origin: *`, así que la página autocontenida
  puede llamarlos sin proxy.
- **Fase C** — el simulador separa roles: cambio de sombrero, bandeja de folios del
  servidor público, datos del ciudadano en solo lectura.

Fase A exige revisar el renglón de `CLAUDE.md` que prohíbe emitir componentes de API. Ese
cambio requiere aprobación humana explícita y no se toca en esta fase.
