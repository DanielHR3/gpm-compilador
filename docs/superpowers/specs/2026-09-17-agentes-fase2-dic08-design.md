# Fase 2 — Generador de propuestas para `DIC-08` (agentes de IA)

**Goal:** que las condiciones de visibilidad que el extractor no supo
interpretar (`DIC-08`, 23 de los 73 huecos que hoy bloquean los seis
expedientes reales) lleguen al analista **ya propuestas**, con su cita y
verificadas de forma determinista, para que su trabajo sea aceptar o corregir
en vez de construir desde cero. Es la primera pieza del "generador" prometido a
la fábrica (láminas 4–6 de la presentación del 2026-09-15) y el primer uso de
un modelo de lenguaje en el proyecto.

**Architecture:** un módulo nuevo `src/gpmc/agentes/` —**el único del sistema
que habla con un modelo**— con un contrato de proveedor y dos implementaciones
(Gemini para pruebas, OpenAI para la licencia de Planeación), un armador de
contexto por tipo de hueco, un filtro determinista que reutiliza las reglas de
`/resolver`, y una bitácora de interacción *append-only* con los campos que
exige la "Licencia AI" del entregable de Planeación. `nucleo/` no cambia: el
invariante "sin dependencias de red en el núcleo" queda garantizado por la
dirección de las importaciones (`agentes` → `nucleo`, nunca al revés). Las
propuestas se generan en segundo plano al subir el expediente, se persisten en
la sesión y la SPA las presenta prellenadas en el control que ya existe. La
escritura al manifiesto sigue siendo **exclusivamente** `POST /resolver` con
`tipo: "dic08"`: el generador nunca escribe.

**Tech Stack:** Python 3.9+ (Pydantic v2), FastAPI (`BackgroundTasks`),
`google-genai` y `openai` como **extra opcional** `[agentes]`; Vite + React 19 +
TS + Tailwind + shadcn en el frontend, sin dependencias nuevas.

**Relación con lo anterior:** se apoya en SP2
(`2026-09-10-sp2-constructor-de-reglas-design.md`): `Condicion`/`Clausula` en
`nucleo/manifiesto.py`, la rama `dic08` de `resolver_expediente` en
`web/api.py`, `ControlVisibilidad` y `TarjetaHueco` en la SPA, y los archivos
por sesión de `web/sesiones.py` (`huecos.json`, `reconocidos.json`,
`compuertas.json`).

**Compromisos externos que este spec debe honrar:**

- Presentación a la fábrica (2026-09-15), lámina 5: *«la IA nunca rellena un
  dato para poder seguir; lo que no puede anclar lo deja como pregunta»*;
  lámina 4: trazabilidad, explicabilidad, demostrabilidad; lámina 12: *«el
  despliegue del modelo debe ser controlado y quedar documentado»*.
- Tarjeta informativa al Comisionado (2026-09-17): el criterio de avance es
  **casos que requieren a una persona**, medido sobre los mismos seis
  expedientes; si la fase no baja el número, no se avanza.
- "Licencia AI" (Entregables técnicos APIs, Planeación, págs. 66–70):
  proveedor OpenAI API directa (GPT-4/GPT-4o); bitácora de interacción con
  campos definidos, inmutable y exportable; control de tokens con límites;
  protección contra *prompt injection*; validación de salida antes de mostrar.

---

## Global Constraints

- Python 3.9-safe: `Optional[X]`, `list[X]`; identificadores en español sin
  acentos; textos de usuario con acentos.
- **`nucleo/` no importa nada de `agentes/`.** Se añade una prueba que lo
  verifica leyendo los `import` (falla si aparece).
- **Ninguna prueba de la suite toca la red.** Todo `agentes/` se prueba con
  `ProveedorFalso`. La única prueba contra un modelo real está marcada
  `@pytest.mark.red` y se salta salvo `GPMC_IA_PRUEBA_REAL=1`.
- **El generador es aditivo.** Sin proveedor, sin llave, sin red o con error,
  el asistente se comporta exactamente como hoy. Ningún camino del generador
  puede impedir descargar un `.gpm`.
- **La llave nunca toca el repositorio ni el `plist`.** Solo variables de
  entorno. El repositorio es público y ya arrastra un hallazgo `SEG-04`.
- **Nada del generador escribe en el manifiesto.** La única vía de escritura
  sigue siendo `POST /resolver`.
- **La columna "Ejemplo Real" del Diccionario nunca se manda al modelo.**
  Contiene CURP, nombres y datos de casos reales.

---

## 1. Módulo `src/gpmc/agentes/`

```
src/gpmc/agentes/
├── __init__.py       expone proponer_dic08(), hay_proveedor()
├── proveedor.py      Proveedor (Protocol), Respuesta, NingunProveedor, ProveedorFalso
├── gemini.py         ProveedorGemini  — pruebas (Google AI Studio)
├── openai_.py        ProveedorOpenAI  — licencia de Planeación (GPT-4o)
├── contexto.py       contexto_dic08(manifiesto, huecos) -> ContextoLote
├── prompt.py         INSTRUCCION_DIC08 (versionada) + esquema JSON de salida
├── dic08.py          proponer_lote(...) -> list[Propuesta]
├── verificar.py      verificar(propuesta, manifiesto) -> Veredicto
└── bitacora.py       registrar(Interaccion) -> None   (append-only JSONL)
```

### 1.1 `proveedor.py` — el contrato

```python
class Respuesta(BaseModel):
    texto: str                      # cuerpo devuelto (JSON como texto)
    tokens_entrada: Optional[int]
    tokens_salida: Optional[int]
    modelo: str
    duracion_ms: int

class Proveedor(Protocol):
    nombre: str
    def completar(self, instrucciones: str, contexto: str,
                  esquema: dict) -> Respuesta: ...
```

- `instrucciones` es el prompt de sistema fijo y versionado; `contexto` es el
  bloque de datos; `esquema` es el JSON Schema de la salida. Cada
  implementación traduce eso a su API (Gemini: `response_schema`; OpenAI:
  `response_format` con `json_schema`). **La salida debe ser JSON válido
  conforme al esquema o la implementación lanza `RespuestaInvalida`.**
- `NingunProveedor.completar` lanza `ProveedorNoDisponible`. Es lo que se
  instancia cuando falta configuración.
- `ProveedorFalso(respuestas: list[str])` devuelve textos de guion en orden.
  Es el único proveedor que ven las pruebas.
- Selección: `crear_proveedor()` lee `GPMC_IA_PROVEEDOR` ∈ `{gemini, openai}`
  y `GPMC_IA_LLAVE`. Modelo por omisión: `gemini-2.5-flash` /
  `gpt-4o`; se cambia con `GPMC_IA_MODELO`. Sin variables → `NingunProveedor`.
- Timeout por llamada: `GPMC_IA_TIMEOUT_S` (default 60). Reintento: **uno**,
  solo ante error de red o 5xx, nunca ante `RespuestaInvalida`.

### 1.2 `contexto.py` — lo que ve el modelo

Para un lote de huecos `DIC-08` de un mismo manifiesto:

```python
class CampoCandidato(BaseModel):
    nombre: str; etiqueta: str; tipo: str
    valores: list[str]          # valores técnicos del catálogo, si lo hay
    pantalla: str               # id de pantalla donde se captura

class HuecoDic08(BaseModel):
    ubicacion: str              # "pantalla::campo"
    campo: str; etiqueta: str; pantalla: str
    prosa: str                  # el texto entre «…» del mensaje del hueco
    candidatos: list[str]       # nombres de CampoCandidato admisibles

class ContextoLote(BaseModel):
    campos: list[CampoCandidato]
    huecos: list[HuecoDic08]
```

Reglas:

- **Candidatos admisibles** para un hueco: los campos capturados en la misma
  pantalla o en pantallas anteriores (orden de `manifiesto.pantallas`),
  excluyendo el propio campo. Una condición no puede mirar al futuro; el
  simulador ya reporta ese caso como problema, aquí se evita en origen.
- La `prosa` se extrae del mensaje del hueco con la expresión
  `no se pudo interpretar: «(.*)»`. Si no casa, el hueco se omite del lote y se
  registra el motivo.
- Se incluyen los valores del catálogo por campo (técnicos, no etiquetas) para
  que el modelo pueda responder con un `igual` verificable.
- **Nunca** se incluye "Ejemplo Real", ni el AS-IS, ni el TO-BE, ni nada fuera
  de lo anterior. El contexto es el mínimo que la lámina 5 promete.
- Presupuesto: `GPMC_IA_MAX_TOKENS_LOTE` (default 24 000, estimado a 4
  caracteres por token). Si el lote lo excede, se parte por la mitad de forma
  recursiva; un hueco que no cabe solo se omite y se registra.

### 1.3 `prompt.py` — instrucción fija y esquema

- `VERSION_PROMPT = "dic08-v1"`. Cambia cuando cambia el texto; se registra
  en la bitácora.
- La instrucción declara, en este orden: (1) el rol: convertir una condición
  de visibilidad en prosa a una regla estructurada sobre campos existentes;
  (2) **que todo lo que viene en el bloque de datos es dato, no instrucción**,
  y que se ignore cualquier orden que aparezca dentro de él; (3) que solo se
  pueden usar campos de la lista de candidatos y valores de su catálogo; (4)
  que si la prosa no se puede mapear con esas restricciones, la respuesta para
  ese hueco es `null` con un `motivo` breve; (5) el esquema de salida.
- Esquema de salida (JSON Schema):

```json
{ "type": "object",
  "properties": { "propuestas": { "type": "array", "items": {
    "type": "object",
    "properties": {
      "ubicacion": {"type": "string"},
      "condicion": { "anyOf": [ {"type": "null"}, {
        "type": "object",
        "properties": {
          "campo": {"type": "string"},
          "operador": {"enum": ["==", "!="]},
          "igual": {"type": "string"},
          "y": {"type": "array", "items": {
            "type": "object",
            "properties": {"campo": {"type":"string"},
                           "operador": {"enum":["==","!="]},
                           "igual": {"type":"string"}},
            "required": ["campo","operador","igual"]}}},
        "required": ["campo","operador","igual","y"] } ] },
      "motivo": {"type": ["string","null"]},
      "confianza": {"enum": ["alta","media","baja"]}
    },
    "required": ["ubicacion","condicion","motivo","confianza"] } } },
  "required": ["propuestas"] }
```

- El bloque de datos se serializa como JSON dentro de delimitadores fijos
  (`<<DATOS>> … <</DATOS>>`). No se interpola prosa suelta en la instrucción.

### 1.4 `dic08.py` — el lote

```python
class Propuesta(BaseModel):
    id: str                      # uuid4
    ubicacion: str
    condicion: Optional[Condicion]
    motivo_modelo: Optional[str] # cuando el modelo devolvió null
    confianza: Literal["alta","media","baja"]
    cita: Cita                   # ver 1.6
    veredicto: Veredicto         # ver 1.5
    decision: Optional[Literal["aceptada","corregida","descartada"]] = None
    condicion_final: Optional[Condicion] = None   # si fue corregida
    creada: str                  # ISO-8601
    decidida: Optional[str] = None
```

`proponer_lote(manifiesto, huecos, proveedor) -> list[Propuesta]`:

1. Filtra `huecos` a `DIC-08` y arma `ContextoLote` (1.2). Si queda vacío,
   devuelve `[]` sin llamar al modelo.
2. Parte el lote si excede el presupuesto (1.2).
3. Por cada parte: `proveedor.completar(INSTRUCCION, datos, ESQUEMA)`;
   registra la interacción en la bitácora (1.7) **pase lo que pase**.
4. Parsea a `Propuesta`. Una `ubicacion` que no estaba en el lote se descarta
   y se registra como alerta (`ubicacion_inventada`). Un hueco del lote que no
   viene en la respuesta se marca `veredicto=sin_respuesta`.
5. Cada propuesta con `condicion` pasa por `verificar` (1.5). Las que devuelven
   `null` se guardan con `veredicto=modelo_declino` y `motivo_modelo`.
6. Devuelve todas —aceptables y rechazadas— porque el registro de
   demostrabilidad necesita las dos. Quién las muestra decide.

### 1.5 `verificar.py` — el filtro determinista

Aplica **antes de mostrar** las mismas reglas que `/resolver` aplica al
guardar, y una más:

| Regla | Veredicto si falla |
|---|---|
| `condicion.campo` y cada `y[].campo` existen en el manifiesto | `campo_inexistente` |
| Ninguno es el propio campo de la ubicación | `autorreferencia` |
| Cada uno se captura en la misma pantalla o antes | `campo_futuro` |
| Si el campo tiene catálogo, `igual` es uno de sus valores técnicos | `valor_fuera_de_catalogo` |
| Si el campo es booleano (`Sí/No`), `igual` ∈ `{si, no}` | `valor_fuera_de_catalogo` |
| La `Condicion` valida contra el modelo Pydantic (`extra="forbid"`) | `esquema_invalido` |

Si todo pasa: `veredicto=aceptable`. La comparación de valores usa la misma
normalización que `extractores/diccionario._babel` (minúsculas, sin acentos)
para no rechazar por una tilde, pero `Propuesta.condicion.igual` se guarda con
el **valor técnico exacto del catálogo**, no con lo que escribió el modelo.

### 1.6 `Cita`

```python
class Cita(BaseModel):
    fuente: Literal["Diccionario de Datos"]
    pantalla: str        # id
    pantalla_nombre: str
    campo: str
    texto: str           # la prosa literal
```

Los Diccionarios llegan en Word y PDF y se convierten a Markdown: el número de
línea se pierde. La cita ancla a *Diccionario · pantalla · campo · texto
literal*, que es lo que el analista puede cotejar. No se inventa un número.

### 1.7 `bitacora.py` — bitácora de interacción (Licencia AI)

`bitacora-ia.jsonl` en el **almacén global** (`raiz / "bitacora-ia.jsonl"`),
no en la carpeta de sesión: la purga por TTL de sesiones no debe llevársela.
Append-only; una línea JSON por interacción con el modelo:

| Campo | Valor |
|---|---|
| `id` | uuid4 |
| `timestamp` | ISO-8601 UTC |
| `sistema_origen` | `"gpm-compilador"` |
| `usuario` | `"anonimo"` mientras el asistente no tenga autenticación |
| `sid` | sesión |
| `proveedor`, `modelo` | del proveedor |
| `version_prompt` | `VERSION_PROMPT` |
| `solicitud` | `{huecos: [ubicaciones], n_campos, n_caracteres}` — resumen, no el contexto entero |
| `instruccion_hash` | sha256 de la instrucción; el texto vive en el código |
| `respuesta` | texto crudo devuelto |
| `tokens_entrada`, `tokens_salida` | del proveedor, o `null` |
| `duracion_ms` | medido |
| `estado` | `procesada` \| `error` \| `sujeta_a_validacion` |
| `alertas` | lista: `ubicacion_inventada`, `lote_partido`, `hueco_omitido`, `tope_tokens`, `respuesta_invalida` |

`gpmc medir-ia --exportar bitacora.jsonl` copia el archivo (auditoría:
exportación). No hay purga: la licencia pide "periodo definido" y no está
definido; se documenta como pendiente.

---

## 2. API (`web/api.py`)

### 2.1 Generación en segundo plano

En `POST /expedientes`, tras escribir `huecos.json` y responder como hoy:

- Si `hay_proveedor()` y hay huecos `DIC-08`, se encola con
  `BackgroundTasks` la función `generar_propuestas(raiz, sid)`, que escribe
  `propuestas.json` (2.2) al terminar. Antes de encolar, escribe
  `propuestas.json` con `{"estado": "proponiendo"}`.
- Si no hay proveedor: no se escribe `propuestas.json`. La ausencia del archivo
  significa "esta sesión no tiene propuestas ni las tendrá".

La respuesta de `POST /expedientes` **no cambia** (sigue devolviendo
`EstadoExpediente`).

### 2.2 `propuestas.json` (por sesión)

```json
{ "estado": "proponiendo" | "listo" | "error",
  "motivo": null | "texto para el analista",
  "generadas": "ISO-8601" | null,
  "propuestas": [ Propuesta, ... ] }
```

Helpers en `sesiones.py`, mismo estilo que los existentes:
`propuestas_de(carpeta) -> Optional[dict]`, `escribir_propuestas(carpeta, d)`.

### 2.3 Endpoints nuevos

- `GET /api/v1/expedientes/{sid}/propuestas` → `PropuestasOut`
  (`estado`, `motivo`, `propuestas` filtradas a `veredicto == "aceptable"`
  y `decision is None`). `404` si la sesión no existe; `{"estado":
  "sin_proveedor", "propuestas": []}` si no hay archivo.
- `POST /api/v1/expedientes/{sid}/propuestas/{id}/decision` con cuerpo
  `{"decision": "aceptada"|"corregida"|"descartada", "condicion_final":
  Condicion|null}` → `200 {"ok": true}`. Solo anota; **no toca el
  manifiesto**. `404` si no existe la propuesta; `409` si ya tenía decisión.
- **`POST /resolver` no cambia.** Aceptar o corregir desde la SPA hace dos
  llamadas: `resolver` (escritura, como hoy) y luego `decision` (registro).
  Si la segunda falla, la resolución ya quedó: el registro es el que se
  reintenta, no la escritura.

### 2.4 Estimación en el estado

`EstadoExpediente` gana un campo opcional `propuestas_pendientes: bool` para
que la SPA sepa si vale la pena consultar `/propuestas`. `False` si no hay
archivo.

---

## 3. SPA

### 3.1 Cliente (`lib/api.ts`, `lib/types.ts`)

`Propuesta`, `Cita`, `PropuestasOut`; `leerPropuestas(sid)`,
`decidirPropuesta(sid, id, decision, condicionFinal?)`.

### 3.2 `WizardHuecos`

- Al montar con `propuestas_pendientes`, llama `leerPropuestas`. Mientras
  `estado === "proponiendo"`, muestra en la cabecera *«Proponiendo condiciones
  con IA…»* —sin contador: el lote es una sola llamada— y reintenta cada 2 s,
  máximo 30 intentos. En `listo`,
  pasa el mapa `ubicacion → Propuesta` a las tarjetas. En `error`, aviso
  discreto con `motivo` y sigue en modo manual.
- Sin `propuestas_pendientes`: **no hace ninguna llamada**. La pantalla es
  idéntica a hoy; ninguna prueba existente cambia.

### 3.3 `TarjetaHueco` / `ControlVisibilidad`

`ControlVisibilidad` gana dos props opcionales: `propuesta?: Propuesta` y
`onDecision?`. Con propuesta:

- El constructor arranca **prellenado** con `propuesta.condicion`.
- Debajo, un bloque `Propuesto a partir de: «{cita.texto}» — Diccionario ·
  {pantalla_nombre} · {campo}` y la confianza del modelo como texto discreto.
- Tres acciones: **Aceptar** (llama `resolverDic08` con la condición propuesta
  y luego `decidirPropuesta(aceptada)`), **Corregir** (deja el constructor
  editable; al guardar, `resolverDic08` con la condición editada y
  `decidirPropuesta(corregida, condicionFinal)`), **Descartar**
  (`decidirPropuesta(descartada)`; la tarjeta vuelve al modo manual de hoy).
- El enlace "o lo configuro a mano" se conserva.
- Sin propuesta: comportamiento exactamente igual al actual.

Copia: en ningún texto aparece "hueco"; se usa "inconsistencia" o
"condición", como el resto de la SPA desde `60952d1`.

---

## 4. Medición: `gpmc medir-ia`

Orden de CLI que corre `proponer_lote` sobre una carpeta con expedientes (por
omisión los seis del lote real, ruta por argumento) con el proveedor
configurado y reporta:

```
expediente                          DIC-08  aceptables  rechazadas  declinó
Publicación en el Periódico Oficial     11          9           1        1
…
TOTAL                                   23         18           3        2
```

Y, si existe `propuestas.json` con decisiones (sesiones ya revisadas):
`aceptadas sin corregir / total`. Es el indicador de la tarjeta informativa,
ejecutable. `--exportar` copia la bitácora.

---

## 5. Errores y degradación

| Situación | Comportamiento |
|---|---|
| Sin `GPMC_IA_PROVEEDOR` / `GPMC_IA_LLAVE` | `NingunProveedor`; no se crea `propuestas.json`; SPA idéntica a hoy |
| Extra `[agentes]` no instalado | `hay_proveedor()` es `False` aunque haya variables; se registra un aviso en el log del servidor |
| Timeout / red / 5xx | un reintento; si falla, `estado=error`, `motivo` legible; bitácora `estado=error` |
| `RespuestaInvalida` (JSON malformado o fuera de esquema) | sin reintento; `estado=error`; respuesta cruda en bitácora |
| Propuesta que no pasa `verificar` | se guarda con su veredicto; no se muestra |
| `ubicacion` inventada por el modelo | se descarta; alerta en bitácora |
| Lote mayor al presupuesto | se parte; `lote_partido` en bitácora |
| Hueco sin prosa reconocible | se omite; `hueco_omitido` |
| Falla `decision` tras un `resolver` exitoso | la resolución queda; la SPA reintenta el registro una vez y, si falla, avisa sin deshacer nada |

Ninguna fila de esta tabla impide descargar el `.gpm`.

---

## 6. Pruebas

**Backend (`tests/test_agentes.py`, `tests/test_api.py`, `tests/test_cli.py`):**

- `nucleo/` no importa `agentes/` (lectura de imports).
- `contexto_dic08`: candidatos solo de pantallas anteriores o la misma; excluye
  el propio campo; excluye "Ejemplo Real"; extrae la prosa; omite huecos sin
  prosa; incluye valores técnicos del catálogo.
- Partición del lote por presupuesto; hueco que no cabe solo se omite.
- `proponer_lote` con `ProveedorFalso`: respuesta válida → propuestas con
  cita; `null` → `modelo_declino`; ubicación inventada → descartada con alerta;
  hueco sin respuesta → `sin_respuesta`; `RespuestaInvalida` → excepción
  controlada y bitácora `error`.
- `verificar`: una prueba por regla de la tabla 1.5, más el caso de valor con
  tilde que casa por normalización y se guarda con el valor técnico.
- Bitácora: cada campo de la tabla 1.7 presente; append-only (dos llamadas →
  dos líneas); vive en `raiz`, no en la sesión.
- API: `POST /expedientes` sin proveedor no crea `propuestas.json` y la
  respuesta es idéntica; con `ProveedorFalso` inyectado, `propuestas.json`
  pasa de `proponiendo` a `listo`; `GET /propuestas` filtra a aceptables sin
  decisión; `POST decision` 200/404/409; `POST /resolver` intacto (las pruebas
  actuales no cambian).
- CLI: `medir-ia` sobre `ejemplos/expedientes/` con `ProveedorFalso` produce la
  tabla.
- `@pytest.mark.red`: una llamada real a Gemini con el expediente de ejemplo
  `constancia-de-residencia`, saltada salvo `GPMC_IA_PRUEBA_REAL=1`.

**Frontend (`ControlVisibilidad.test.tsx`, `WizardHuecos.test.tsx`):**

- Sin propuestas: cero llamadas a `leerPropuestas`; render idéntico.
- Con `proponiendo`: cabecera con el estado; con `listo`: tarjeta prellenada,
  cita visible, tres acciones.
- Aceptar → `resolverDic08` con la condición propuesta y luego
  `decidirPropuesta("aceptada")`, en ese orden.
- Corregir → editable; guardar → `resolverDic08` con la editada y
  `decidirPropuesta("corregida", condicionFinal)`.
- Descartar → `decidirPropuesta("descartada")` y la tarjeta vuelve al modo
  manual.
- `error` → aviso y modo manual.

---

## 7. Configuración y despliegue

Variables de entorno (todas opcionales; sin ellas, no hay generador):

| Variable | Valores | Default |
|---|---|---|
| `GPMC_IA_PROVEEDOR` | `gemini` \| `openai` | — |
| `GPMC_IA_LLAVE` | la llave del proveedor | — |
| `GPMC_IA_MODELO` | nombre de modelo | `gemini-2.5-flash` / `gpt-4o` |
| `GPMC_IA_TIMEOUT_S` | segundos | `60` |
| `GPMC_IA_MAX_TOKENS_LOTE` | entero | `24000` |

Se instalan con `pip install -e ".[web,agentes]"`. `despliegue/LEEME.md`
documenta las variables y que el `plist` **no** las contiene ni las contendrá:
`gpmc servir` carga `~/.config/gpmc/entorno` (fuera del repo, permisos `600`,
formato `CLAVE=valor`) al arrancar, si existe. Así la llave no pasa por el
instalador ni queda escrita en `~/Library/LaunchAgents`.

---

## 8. Fuera de alcance (Fase 2b y siguientes)

- Otros códigos (`MMD-04`, `DOC-03`, `META-01`…): mismo módulo, un
  `contexto_*`/esquema por código. No en este spec.
- El "acervo de trámites ya construidos" como anclaje: para una condición de
  visibilidad la respuesta vive en la misma fila del Diccionario; el acervo
  aportaría cuando toque `MMD-04` o `DOC-03`.
- El verificador con modelo (Fase 3): para `DIC-08` la salida es cerrada y el
  filtro determinista basta.
- Autenticación de usuarios en el asistente (necesaria para el campo
  `usuario` de la bitácora).

---

## 9. Puntos abiertos (decisión de la Dirección, no de este spec)

1. **Datos reales contra AI Studio.** El nivel de estudio de Google puede usar
   los datos para mejorar sus modelos; la licencia de Planeación (OpenAI)
   garantiza procesamiento transitorio. Este spec asume que **las pruebas con
   Gemini usan los expedientes de ejemplo del repositorio** y no los seis
   reales, salvo decisión expresa en contrario. Con el proveedor `openai`
   bajo la licencia, la restricción desaparece.
2. **Retención de `bitacora-ia.jsonl`**: sin purga hasta que Planeación fije
   el periodo.
3. **"Despliegue controlado y documentado"** (lámina 12): este spec y el
   `LEEME.md` de despliegue son la documentación; la parte "controlado" la da
   la licencia de Planeación, no AI Studio.
