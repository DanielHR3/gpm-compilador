# SP2 — Constructor visual de reglas (MMD-04 + DIC-08)

**Goal:** que un expediente con una condición de visibilidad no interpretable
(`DIC-08`) y/o una compuerta sin `@@campo` (`MMD-04`) se pueda resolver
enteramente desde el wizard de la SPA, sin que el analista toque el modelador —
un paso hacia "cero clics post-importación".

**Architecture:** la `Condicion` del manifiesto gana cláusulas "Y" opcionales
(retrocompatible, sin migración). El compilador ya emite `Condicion` vía
`reglas.emitir`, así que solo cambia el emisor. El extractor gana un parámetro
de override de compuerta y un helper que expone las ramas de una compuerta
cuando la ramificación automática falla. La API extiende `resolver` con tres
`tipo` nuevos y añade un read de compuerta. En la SPA, un constructor de reglas
reutilizable reemplaza el botón "Lo configuro a mano" para esos dos códigos.

**Tech Stack:** Python 3.9+ (Pydantic v2), FastAPI, Vite 8 + React 19 + TS 6 +
Tailwind v4 + shadcn (base-ui) — el stack que dejó SP1.

**Relación con SP1:** SP2 se apoya en la fundación de SP1
(`docs/superpowers/specs/2026-09-09-sp1-fundacion-spa-design.md`): el wizard
(`frontend/src/features/huecos/`), el cliente tipado (`frontend/src/lib/`), la
superficie `/api/v1` (`src/gpmc/web/api.py`) y el patrón de control-por-código en
`TarjetaHueco`.

---

## Global Constraints

- Python 3.9-safe: `Optional[X]` / `list[X]` (el repo ya usa `list[...]` en
  `manifiesto.py`), nada de `X | None`. Identificadores en español sin acentos.
- `nucleo/formato.py` y `SINTAXIS_ESTRICTA` **no se tocan**. `SINTAXIS_ESTRICTA`
  sigue en `False`.
- Retrocompatibilidad de formato: todo `.gpm` y todo `manifiesto.yaml` existente
  (con `Condicion` de una sola comparación) debe seguir parseando y compilando
  sin cambios. Cero migración.
- Ningún `.gpm` de `~/Desktop/Projects/GPM/` se sobrescribe.
- La suite Python nunca baja de **329 passed** (el estado al cierre de SP1) —
  solo sube con las pruebas nuevas.
- Frontend: `bash scripts/check-frontend.sh` verde (tsc `-b --noEmit` +
  `vitest run` + `vite build`). Sin dependencias nuevas. Colores desde los
  tokens ya cableados (`--action-primary`, `--alert-error`, …), sin literales
  hex nuevos en el código.
- CSP del SPA intacta (`default-src 'self'`…); `/vistas/{sid}` conserva su
  `sandbox`.
- Commits con los trailers `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
  y `Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP`.

---

## 1. Contexto y objetivo

El hallazgo #7 de `Hallazgos_UX_y_Mejoras_Pendientes.md` ("cero clics
post-importación"): ante un hueco complejo el asistente solo ofrece "Lo
configuraré a mano en la plataforma", genera un `.gpm` incompleto y delega
trabajo tedioso y riesgoso al analista dentro del modelador real.

De los cuatro códigos de ese hallazgo (`MMD-04`, `DIC-08`, `FLU-01`, `API-05`),
**SP2 aborda solo `MMD-04` y `DIC-08`** — los dos que el modelo del manifiesto
ya soporta de fondo (el primitivo `Condicion` existe y el compilador lo emite),
así que son la pieza más barata y de más valor. `FLU-01` (editor de topología
de flujo) y `API-05` (Acciones PHP) van a sub-proyectos posteriores con su
propio spec.

Descubrimiento clave del escaneo del código:

- `Condicion` (`nucleo/manifiesto.py:53`) es una sola comparación:
  `campo` / `igual` / `operador` (`==` | `!=`).
- `Campo.condicion_visible: Optional[Condicion]` y `Conexion.cuando:
  Optional[Condicion]` **ya existen** en el modelo.
- El compilador (`compilador/a_gpm.py:120,253`) ya enruta ambos por
  `reglas.emitir`.
- `reglas.py` ya sabe **evaluar** `&&` (tiene `_SEPARADOR_AND`); lo que no existe
  es emitir "Y" desde una `Condicion` estructurada.
- `_flujo_ramificado` (`extractores/expediente.py:62`) es todo-o-nada: basta que
  una compuerta no nombre exactamente un `@@campo` (condición 2 de sus 4
  reglas de seguridad) para que devuelva `None` y el flujo salga lineal,
  descartando toda la topología de ramas — que sí está en el parse crudo del
  Mermaid (`rm.nodos`, `rm.aristas`).

**Objetivo medible:** un expediente con (a) una condición de visibilidad que
el parser no interpreta y (b) una compuerta sin `@@campo` cuyas etiquetas de
arista sí resuelven a valores de catálogo, tras usar el wizard compila a un
`.gpm` completo — `bloquean(...)` vacío, `GET /gpm` → 200 — y ese `.gpm` importa
a `modelador.hidalgo.gob.mx` con la visibilidad y la rama disparando sin tocar
el modelador.

---

## 2. Alcance

**Dentro:**

- `Condicion` gana cláusulas "Y" (comparación simple + AND plano; sin "O", sin
  anidar).
- DIC-08: constructor de reglas en el wizard → `Campo.condicion_visible`.
- MMD-04: (fase 1) elegir el `@@campo` de la compuerta → el servidor re-ejecuta
  la ramificación; (fase 2, respaldo) si alguna rama no resuelve sola, un
  constructor de condición por rama → `Conexion.cuando`.
- Extensión del emisor (`reglas.emitir`), el validador cruzado y —si consume el
  objeto y no el string— el simulador, para el "Y".
- API: `resolver` con `tipo` `dic08` / `mmd04campo` / `mmd04rama`; read
  `GET /expedientes/{sid}/compuerta/{gate_id}`.
- Componentes React: `ConstructorRegla`, `ControlVisibilidad`, `ControlCompuerta`;
  cableado en `TarjetaHueco`.
- Persistencia de sesión: `compuertas.json` (overrides de compuerta), análogo a
  `reconocidos.json`.

**Fuera (con su propio spec después):**

- `FLU-01` — editor visual de topología de flujo (crear/mover/unir tareas).
  SP2 solo toca ramas de compuertas que **ya existen** en el Mermaid.
- `API-05` — formulario de endpoint con token + emisión de Acción PHP. Sigue
  vigente el invariante de `CLAUDE.md` ("no se emiten Acciones PHP").
- El "O" (disyunción) en condiciones. Si aparece un caso real, se amplía
  entonces.
- El backlog de UX de SP1 (agrupar huecos por nivel, ficha de estimación,
  `reconocidos` en el payload del deep-link, vendorizar `tokens.json`, etc.).

---

## 3. Modelo (`nucleo/manifiesto.py`, `nucleo/reglas.py`)

### 3.1 `Condicion` gana `y`

```python
class Clausula(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campo: str
    igual: str
    operador: Literal["==", "!="] = "=="

class Condicion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campo: str
    igual: str
    operador: Literal["==", "!="] = "=="
    y: list[Clausula] = []          # NUEVO — cláusulas AND; [] = comportamiento de hoy
```

- `Clausula` no tiene `y`: el "Y" es plano, sin anidar.
- `y` tiene default `[]`, así que `extra="forbid"` se respeta y un
  `manifiesto.yaml` / `.gpm` sin `y` parsea idéntico. **Sin migración.**
- La cláusula base (`campo`/`igual`/`operador` de la `Condicion`) más las de `y`
  forman la conjunción completa.

### 3.2 `reglas.emitir`

Hoy emite una comparación. Pasa a unir la cláusula base y las de `y` con `&&`:

```
@@estado != 'hidalgo' && @@tipo_solicitante == 'foraneo'
```

- Se extrae un helper interno `_emitir_clausula(campo, operador, igual)` que
  produce `@@campo == 'valor'` / `@@campo != 'valor'` (respetando
  `SINTAXIS_ESTRICTA`, que sigue en `False`).
- `emitir(cond)` = `" && ".join(_emitir_clausula(...) for c in [cond, *cond.y])`.
- El separador es exactamente `" && "`, que es lo que `_SEPARADOR_AND` ya parsea.

### 3.3 `reglas.evaluar` / simulador

`evaluar(regla_str, valores)` ya trocea por `_SEPARADOR_AND` y exige que todas
las sub-condiciones se cumplan. Si el simulador evalúa el **string emitido**
(vía `emitir` → `evaluar`), no cambia nada de lógica; el ejecutor solo lo
confirma leyendo `simulador/`. Si en algún punto el simulador leyera el objeto
`Condicion` directo, se le añade el loop `[cond, *cond.y]`.

### 3.4 Validador cruzado

El check de "condición usa un campo no declarado" (`manifiesto.py`, alrededor
de la línea 194, `cx.cuando.campo not in nombres_campo`) pasa a recorrer
`[cond.campo] + [c.campo for c in cond.y]`. Mismo mensaje por cada cláusula
ofensora. Aplica igual al check equivalente de `condicion_visible` si existe.

---

## 4. Extractor y compilador

### 4.1 Compilador — sin cambios

`a_gpm.py:120` (`dependiente_campo = reglas.emitir(c.condicion_visible)`) y
`a_gpm.py:253` (`regla=reglas.emitir(cx.cuando)`) ya delegan en `emitir`. Con
la Sección 3.2, el `.gpm` lleva el "Y" sin tocar el compilador.

### 4.2 DIC-08 — identificar el campo (`extractores/diccionario.py`)

Hoy el hueco `DIC-08` lleva `ubicacion = pantalla.id` y el nombre del campo solo
va en el texto del mensaje. Cambio: el hueco pasa a llevar
`ubicacion = f"{pantalla.id}::{nombre_campo}"` (estructurado). Los dos sitios
que emiten `DIC-08` (`diccionario.py:486` y `:492`) usan la misma forma. El
mensaje se mantiene legible.

### 4.3 MMD-04 — re-ejecutar la ramificación con override

- `_flujo_ramificado(rm, pantallas, overrides=None)` gana
  `overrides: Optional[dict[str, str]]` (id de compuerta → nombre de campo).
  Antes del check de la condición 2
  (`if len(set(g.campos)) != 1 or g.campos[0] not in campos`), si
  `g.id in overrides`, sustituye `g.campos` por `[overrides[g.id]]` para ese
  nodo (copia local, no muta `rm`).
- Nuevo helper `ramas_de_compuerta(rm, pantallas, gate_id) ->
  {"predecesora": str, "ramas": [{"a": str, "a_nombre": str, "etiqueta": str}]}`
  o `None` si el `gate_id` no es una compuerta. Lee `rm.aristas` / `rm.nodos`;
  `a_nombre` sale del texto del nodo destino o de la pantalla mapeada.
- La orquestación de re-splice vive en `web/` (es lógica de sesión: lee
  `compuertas.json`, re-parsea el TO-BE de la carpeta, muta el manifiesto de la
  sesión). `expediente.py` solo aporta el param `overrides` y el helper
  `ramas_de_compuerta` — funciones puras, sin I/O de sesión. La orquestación
  re-parsea el Mermaid del TO-BE de la carpeta, aplica **todos** los overrides
  acumulados de `compuertas.json`, corre `_flujo_ramificado`; si devuelve un
  `Flujo`, reemplaza `manifiesto.flujo` y quita de `huecos.json` los `MMD-04` /
  `FLU-01` / `FLU-02` que ya no apliquen; si devuelve `None`, deja el `MMD-04` de
  esa compuerta.

### 4.4 Persistencia

`compuertas.json` en la carpeta de sesión: `{ "<gate_id>": "<nombre_campo>" }`.
Helpers análogos a los de `reconocidos.json` en `web/sesiones.py`
(`compuertas_de(carpeta)`, `escribir_compuertas(carpeta, d)`).

---

## 5. API (`src/gpmc/web/api.py`)

### 5.1 `POST /expedientes/{sid}/resolver` — `Resolucion` como unión discriminada por `tipo`

Los `tipo` de SP1 (`mmd03`, `meta01`, `meta02`, `api03`, cuerpo
`{tipo, ubicacion, valor: str}`) **no cambian**. Se añaden:

| `tipo` | cuerpo | efecto |
|---|---|---|
| `dic08` | `{tipo, ubicacion: "pantalla::campo", condicion: Condicion}` | busca el campo por nombre en esa pantalla y le pone `condicion_visible`; quita el hueco `DIC-08` de esa `ubicacion` |
| `mmd04campo` | `{tipo, ubicacion: gate_id, campo: str}` | escribe el override en `compuertas.json`, re-empalma `manifiesto.flujo` (4.3) |
| `mmd04rama` | `{tipo, ubicacion: gate_id, ramas: [{a: tarea_id, condicion: Condicion}]}` | reescribe las conexiones alrededor de esa compuerta: quita la arista lineal que la saltaba y añade una `Conexion(de=predecesora, a=rama.a, cuando=rama.condicion)` por cada rama; el resto de `manifiesto.flujo.conexiones` queda intacto; quita el `MMD-04` de esa compuerta |

- `condicion` en el cuerpo se valida con el modelo Pydantic de la Sección 3.1.
- Respuesta igual que SP1: `200 {manifiesto: dict, huecos: HuecoOut[]}`.
- `422 {error}` si: el campo de `dic08` no existe en esa pantalla; el `campo` de
  `mmd04campo` no está en el manifiesto; una `tarea_id` de `mmd04rama` no es una
  rama de esa compuerta; o una `Condicion` referencia un campo no declarado.

### 5.2 `GET /expedientes/{sid}/compuerta/{gate_id}` — read nuevo

- `200 {predecesora: str, ramas: [{a: str, a_nombre: str, etiqueta: str}]}` —
  del Mermaid del TO-BE re-parseado (`ramas_de_compuerta`).
- `404 {error}` si el `sid` o el `gate_id` no existen.
- **No** devuelve la lista de campos / catálogos: el cliente ya la tiene en
  `estado.manifiesto.pantallas[].campos[]`.

### 5.3 Señal de "el campo no bastó"

Sin flag. Tras `mmd04campo`, si la respuesta `huecos` sigue conteniendo el
`MMD-04` de esa compuerta, el cliente ofrece el respaldo por rama.

### 5.4 Cliente tipado (`frontend/src/lib/`)

- `types.ts`: `Clausula`, `Condicion` (`{campo, igual, operador, y: Clausula[]}`),
  `RamaCompuerta` (`{a, a_nombre, etiqueta}`), `EstructuraCompuerta`
  (`{predecesora, ramas: RamaCompuerta[]}`).
- `api.ts`: `resolverDic08(sid, ubicacion, condicion)`,
  `resolverCompuertaCampo(sid, gateId, campo)`,
  `resolverCompuertaRamas(sid, gateId, ramas)`,
  `leerCompuerta(sid, gateId)`. Todas relativas, mismo `ErrorApi` de SP1.
- Accesor `camposDelManifiesto(manifiesto): {nombre, etiqueta, catalogo}[]` —
  aplana `pantallas[].campos[]` con narrowing sobre el `Record<string, unknown>`;
  no se tipa el manifiesto entero.

---

## 6. Componentes React (`frontend/src/features/huecos/`)

### 6.1 `controles/ConstructorRegla.tsx`

- Props: `campos: {nombre, etiqueta, catalogo: {etiqueta, valor}[]}[]`,
  `value: Condicion | null`, `onChange(c: Condicion): void`.
- N filas `[Select campo] [Select operador ==/≠] [valor]`. El valor es un
  `<Select>` de `{etiqueta, valor}` si el campo tiene `catalogo`; si no, un
  `<Input>` de texto.
- "+ Y" añade fila; "×" quita. Fila 1 = cláusula base de la `Condicion`; filas
  2..N = `value.y`.
- shadcn base-ui (`Select`/`Input`/`Button`); colores por token; sin hex.
- Emite una `Condicion` bien formada en cada cambio (nunca `y` con cláusula
  vacía: una fila incompleta no entra en el `onChange`).

### 6.2 `controles/ControlVisibilidad.tsx` (DIC-08)

- Muestra la frase cruda no interpretada (del `hueco.mensaje`), el campo
  afectado (de `hueco.ubicacion` partido por `::`), un `ConstructorRegla`
  alimentado por `camposDelManifiesto`, y "Guardar".
- "Guardar" → `resolverDic08(sid, hueco.ubicacion, condicion)` → `onResuelto(resp)`.

### 6.3 `controles/ControlCompuerta.tsx` (MMD-04)

- **Fase 1:** `<Select>` de `camposDelManifiesto` + "Usar este campo" →
  `resolverCompuertaCampo(sid, gateId, campo)` → `onResuelto(resp)`. Si `resp.huecos`
  sigue trayendo el `MMD-04` de `gateId` → aviso "las ramas no resolvieron solas"
  y aparece la Fase 2.
- **Fase 2:** `leerCompuerta(sid, gateId)` → por cada `rama`,
  `→ <a_nombre> (etiqueta "<etiqueta>")` + un `ConstructorRegla`; "Guardar ramas"
  → `resolverCompuertaRamas(sid, gateId, ramas)` → `onResuelto(resp)`.

### 6.4 `TarjetaHueco.tsx`

Al switch por código de SP1 se suman `DIC-08 → ControlVisibilidad` y
`MMD-04 → ControlCompuerta`. `WizardHuecos` no cambia: el `onResuelto` que ya
fusiona `{manifiesto, huecos}` sirve igual.

### 6.5 Escape hatch

En las tarjetas `DIC-08` / `MMD-04`, debajo del constructor, un enlace pequeño
"o lo configuro a mano" que llama al `reconocer` de SP1 (registra el hueco en
`reconocidos.json` y levanta la puerta del linter) — para cuando el analista de
verdad no puede expresar la lógica.

---

## 7. Pruebas y verificación

### 7.1 Python (`pytest`)

- **Modelo:** `Condicion` con `y` round-trip `serializar`/`cargar`; una
  `Condicion` legada (sin `y`) parsea; `extra="forbid"` rechaza un campo extra.
- **`reglas.emitir`:** una cláusula = string de hoy; con `y` → unido por `&&`;
  `!=` por cláusula; orden estable (base, luego `y` en orden).
- **`reglas.evaluar`:** el string `&&` emitido → verdadero solo si todas las
  cláusulas se cumplen; falso si una falla.
- **Validador cruzado:** una cláusula de `y` con campo no declarado se reporta;
  el mensaje nombra el campo ofensor.
- **Compilador:** un `condicion_visible` y un `Conexion.cuando` con `y` emiten el
  string unido en el `.gpm` (assert sobre el texto).
- **Extractor DIC-08:** el hueco lleva `ubicacion == "p1::nombre_campo"`.
- **Extractor MMD-04:** `_flujo_ramificado(rm, pantallas, overrides={g: campo})`
  arma el `Flujo` ramificado cuando el único defecto era el campo; devuelve
  `None` si una etiqueta de rama no resuelve; `ramas_de_compuerta` devuelve
  predecesora + destinos + etiquetas para una compuerta conocida y `None` si no.
- **API:** `dic08` pone `condicion_visible` y quita el hueco; `mmd04campo`
  re-empalma el flujo, escribe `compuertas.json` y quita el `MMD-04`;
  `mmd04rama` inyecta las `Conexion` con `cuando` y quita el `MMD-04`;
  `GET /compuerta/{id}` devuelve la estructura y 404 con id inválido; los 422
  de cada validación.
- **Integración "cero clics":** fixture de expediente con visibilidad no
  interpretable + compuerta sin `@@campo` (etiquetas resolubles a catálogo) →
  `POST /expedientes` (201, trae `DIC-08` + `MMD-04`) → `resolver dic08` →
  `resolver mmd04campo` → `bloquean(huecos_vivos, reconocidos_de)` vacío y
  `GET /gpm` → 200.

### 7.2 Frontend (`Vitest`)

- `ConstructorRegla`: añadir una fila "Y" y elegir campo/op/valor emite el
  `Condicion` esperado con `y`; un campo con catálogo renderiza `<Select>` de
  valores, sin catálogo un `<Input>`; una fila incompleta no dispara `onChange`.
- `ControlVisibilidad`: renderiza la frase cruda, arma una condición, llama
  `resolverDic08` con los args exactos, sube el estado por `onResuelto`.
- `ControlCompuerta`: fase 1 llama `resolverCompuertaCampo`; cuando la respuesta
  sigue con el `MMD-04`, aparece la fase 2, se llama `leerCompuerta`, y "Guardar
  ramas" llama `resolverCompuertaRamas` con una condición por rama.
- `TarjetaHueco`: `DIC-08` / `MMD-04` enrutan a los controles nuevos; el enlace
  "o lo configuro a mano" sigue llamando `reconocer`.

### 7.3 Gates

- `.venv/bin/pytest -q` verde, ≥ 329 passed + las pruebas nuevas.
- `bash scripts/check-frontend.sh` exit 0 (tsc `-b --noEmit` limpio, `vitest run`
  todo verde, `vite build` OK).

### 7.4 Verificación en plataforma (el ritual del usuario — prueba real de "cero clics")

Compilar un `.gpm` de un expediente que hoy emite `DIC-08` + `MMD-04` (candidato:
uno de los 6 trámites de `Reingenieria 2026-09-02/`), resolverlo entero por el
wizard, importarlo a `modelador.hidalgo.gob.mx` y al portal del ciudadano, y
confirmar que la condición de visibilidad y la rama disparan sin tocar el
modelador. Acta en `planeacion/actas/2026-XX-XX-sp2-cero-clics.md`.

---

## 8. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| El "Y" rompe un `.gpm` / `manifiesto.yaml` existente | `y` opcional con default `[]`; prueba explícita de round-trip de una `Condicion` legada; el emisor con una sola cláusula produce el string idéntico al de hoy (prueba de regresión). |
| El simulador interpreta el "Y" distinto que la plataforma | `reglas.evaluar` ya trocea `&&` y exige todas; el simulador consume el string emitido, no el objeto. Prueba que compara `evaluar` contra la semántica esperada. |
| `mmd04campo` re-empalma un flujo y pisa resoluciones previas | El re-splice solo reemplaza `manifiesto.flujo`; las resoluciones de `DIC-08`, `MMD-03`, etc. viven en `campos` / `tareas`, no en `flujo.conexiones` derivadas. Los overrides se acumulan en `compuertas.json` y se re-aplican todos juntos. |
| El respaldo por rama produce un flujo inconsistente (rama a tarea inexistente) | `mmd04rama` valida cada `a` contra las ramas que devuelve `ramas_de_compuerta`; 422 si no casa. El validador cruzado del manifiesto corre después. |
| El constructor de reglas deja pasar una `Condicion` a medio llenar | `ConstructorRegla` no incluye en `onChange` una fila sin campo o sin valor; el botón "Guardar" se deshabilita si la cláusula base está incompleta. Prueba Vitest. |
| Crecimiento de alcance hacia FLU-01 | SP2 solo toca ramas de compuertas **ya presentes** en el Mermaid; crear/mover/unir tareas es FLU-01, fuera. El spec fija los 3 `tipo` y el read. |
| `Resolucion` como unión discriminada rompe el `resolver` de SP1 | Los `tipo` de SP1 quedan como están; los nuevos se suman. Las pruebas de SP1 de `resolver` siguen corriendo sin cambio. |

---

## 9. Decisiones del brainstorming (trazabilidad, 2026-09-10)

1. **Alcance:** solo `MMD-04` + `DIC-08` (constructor de reglas). `FLU-01` y
   `API-05` a sub-proyectos posteriores.
2. **Reglas:** comparación simple **+ "Y"** (AND plano). Sin "O", sin anidar.
3. **MMD-04:** las dos vías — selector de campo rápido (el servidor reconstruye
   las ramas) y, si alguna rama no resuelve, constructor de condición por rama.
   Esto incorpora una porción acotada de FLU-01 (exponer las ramas de una
   compuerta existente), no el editor de topología.
4. **Modelo:** enfoque A — `Condicion` gana `y: list[Clausula]` opcional.
   Retrocompatible, sin migración. Se descartó B (`Condicion` pasa a
   `{clausulas, junta}`) y C (nuevo `Regla` que envuelve `list[Condicion]`) por
   romper el formato.
