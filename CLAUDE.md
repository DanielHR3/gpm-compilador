# CLAUDE.md — gpm-compilador

Convenciones del repositorio. Compilador que convierte un manifiesto YAML de trámite en un
archivo `.gpm` importable en una plataforma de modelado BPMN.

## Stack

- Python 3.9 o superior, entorno virtual en `.venv/`
- `pydantic` para el modelo del manifiesto
- `pyyaml` para leer y escribir manifiestos
- `pytest` para las pruebas
- `fastapi` + `uvicorn` + `python-multipart` como extra opcional `[web]`
- `reportlab` como extra opcional `[guia]` (genera los PDF de la guía del equipo)
- Sin dependencias de red en el núcleo. Sin base de datos.

## Regla que gobierna todo el formato `.gpm`

```python
json.dumps(obj, separators=(',', ':'), ensure_ascii=True).replace('/', '\\/')
```

La plataforma corre sobre PHP y exporta con `json_encode` sin `JSON_UNESCAPED_SLASHES`. Esa forma
reproduce **byte a byte** los exports de referencia. Ninguna otra manera de serializar es
aceptable, y la prueba de ida y vuelta lo verifica en cada corrida.

## Estructura

```
src/gpmc/
├── nucleo/
│   ├── formato.py        serializacion byte-exacta
│   ├── esquema.py        primitivos: tarea, paso, formulario, campo, conexion, proceso
│   ├── manifiesto.py     modelo Pydantic del manifiesto y su coherencia
│   ├── reglas.py         evaluador UNICO de reglas de transicion y de visibilidad
│   ├── integraciones.py  catalogo de APIs (SIPUBEH, INEGI, SEPOMEX) y su mapeo de respuesta
│   └── huecos.py         tipo Hueco y codigos estables (INS-*, DIC-*, META-*, FLU-*, MMD-*, API-*, PLAT-*)
├── extractores/
│   ├── expediente.py     orquestador: carpeta de insumos -> manifiesto + huecos
│   ├── metadatos.py      frontmatter y encabezados -> nombre, homoclave, dependencia, ficha RUTS
│   ├── diccionario.py    Diccionario .md -> pantallas, campos, catalogos, condiciones de visibilidad
│   └── mermaid.py        flowchart del TO-BE -> tareas, compuertas, conexiones, actores
├── compilador/
│   ├── a_gpm.py          manifiesto -> .gpm
│   ├── acciones.py       los cuatro arquetipos: folio, costo, documento, notificacion
│   └── aprobacion.py     manifiesto -> HTML estatico de aprobacion para la dependencia
├── validador/
│   └── reglas.py         hallazgos EST-* (estructura y limite de columna), FOLIO-*, de escapado y de credenciales
├── simulador/
│   ├── analisis.py       analisis estatico del flujo (tareas inalcanzables, ramas muertas, bucles)
│   └── html.py           recorrido navegable del tramite
├── planeacion/
│   ├── registro.py       mide el ciclo real de cada tramite
│   └── proyeccion.py     proyecta capacidad y tiempo
├── estimador.py          seis metricas de complejidad + sugerencia de nivel (escala no calibrada)
├── web/
│   ├── app.py            asistente de 5 pasos (FastAPI)
│   └── plantillas.py     HTML/CSS embebido, cero dependencias de frontend
└── cli.py                las 9 ordenes (abajo)
```

**Dependencia en un solo sentido:** `web`/`cli` → `compilador`/`validador`/`extractores` →
`nucleo`. Nada por debajo de `web` conoce interfaz de usuario: son funciones sobre archivos, sin
estado de sesión. Esa separación es la que permite que la CLI y las pruebas existan sin navegador.

### Las 9 órdenes de la CLI

| Orden | Hace |
|---|---|
| `compilar` | manifiesto YAML → `.gpm`. `--modo-pruebas` agrupa todas las pantallas en una tarea inicial sintética para recorrer las vistas sin compuertas. `--desde-expediente <carpeta>` re-extrae y aplica la puerta del linter antes de compilar (omite el manifiesto posicional) |
| `validar` | revisa un `.gpm` existente |
| `extraer` | carpeta de expediente → manifiesto YAML + huecos. `--nombre` cuando no hay AS-IS (P-03). `--estricto` no escribe el manifiesto si quedan huecos bloqueantes o de falta de datos (código 2) |
| `estimar` | seis métricas de complejidad y tiempo de ciclo |
| `simular` | manifiesto → simulador navegable en HTML |
| `aprobar` | manifiesto → HTML estático de aprobación para la dependencia |
| `planear` | mide y proyecta el ciclo (`iniciar`/`hito`/`cerrar`/`estado`/`capacidad`/`proyectar`/`sembrar`) |
| `servir` | levanta el asistente web |
| `diagnostico` | `--sintaxis` genera los archivos de la prueba empírica de sintaxis en plataforma |

### La puerta del linter (`nucleo/huecos.bloquean`)

`bloquean(huecos, reconocidos)` decide qué huecos impiden entregar un `.gpm`: los
`bloqueante` siempre; los `falta_dato` salvo que estén *reconocidos* — una persona marcó "lo
configuro a mano en la plataforma"; los `por_confirmar` nunca. La usan `gpmc extraer
--estricto`, `gpmc compilar --desde-expediente`, y en el asistente web `GET
/descargar/{sid}/gpm` (409 mientras quede un hueco sin resolver ni reconocer; `POST
/reconocer/{sid}` levanta la puerta para uno, dejando constancia en `reconocidos.json`). El
objetivo no es que `falta_dato` sea infranqueable: es que nadie mande un expediente sin haber
visto y decidido sobre cada hueco.

## Reglas de código

- Identificadores y nombres de módulo **en español sin acentos** (`nucleo`, no `núcleo`). Los
  textos dirigidos al usuario sí llevan acentos.
- Los comentarios explican *por qué*, no *qué*. Si un valor por omisión viene de un export real,
  el comentario lo dice.
- Compatible con Python 3.9: nada de `X | None` en anotaciones, usar `Optional[X]`.
- Ninguna función del `nucleo` importa de `compilador`, `validador`, `web` ni `cli`.

## Reglas de dominio (invariantes de este proyecto)

Son reglas de calidad, no configurables:

- **El folio se emite siempre con bloqueo transaccional sobre el contador de `dato_seguimiento`,
  llaveado por el nombre de la variable y sin `proceso_id`.** Nunca `->count()`, nunca `rand()`
  (ambas colisionan), y nunca un `proceso_id` hardcodeado: la plataforma lo reasigna al importar
  y no reescribe las referencias del PHP, así que el folio queda roto (PLAT-4). La forma correcta
  es `\DB::table('dato_seguimiento')->where('nombre', '<variable>')->lockForUpdate()->value('valor')`,
  copiada de los dos exports auténticos que funcionan. Ver `planeacion/actas/2026-08-30-prueba-en-plataforma.md`.
- **Toda variable de usuario interpolada en un documento pasa por `htmlspecialchars`.** Sin
  excepción y sin bandera para desactivarlo.
- **No se genera configuración de firma electrónica.** Ningún archivo de referencia disponible
  tiene una firma real configurada; no se infiere una.
- **No se emiten los componentes `Api variable`, `Javascript` ni `Redirección`.** Los dos últimos
  evalúan control de flujo en el navegador.
- **El validador propone, no adivina.** Lo que no puede derivarse de los insumos se reporta como
  hueco, nunca se rellena por inferencia silenciosa.
- **Las condiciones de visibilidad solo se emiten cuando son inequívocas.** Un campo del
  Diccionario con la forma «Visible solo si X = Y» viaja al `.gpm` como string en
  `dependiente_campo`, que es la forma de los exports. Una condición compuesta o ambigua se
  reporta como hueco `DIC-08` y el campo queda siempre visible — no se infiere la regla.

## Cuestión abierta: `Api variable` frente a `api_ajax`

**No se resuelve leyendo archivos. Requiere una respuesta humana.**

El invariante de arriba prohíbe emitir el componente `Api variable`. Pero el export auténtico
`acceso-informacion-publica.gpm` **sí contiene** un campo de tipo `api_ajax`, con su
configuración completa: la URL de SIPUBEH, el evento `blur` que lo dispara y los tres campos
que autocompleta a partir de la CURP.

La pregunta es si son el mismo componente:

- Si **`Api variable` == `api_ajax`**, el invariante prohíbe algo que la plataforma produce por
  su cuenta, y hay que decidir si se relaja y bajo qué condición.
- Si **son distintos**, no hay conflicto: `api_ajax` puede emitirse y el invariante sigue
  cubriendo otro componente.

La redacción sugiere lo segundo —la justificación dice "los dos últimos evalúan control de flujo
en el navegador", que solo cubre `Javascript` y `Redirección`— pero eso es una lectura, no una
confirmación. Lo sabe quien tenga la plataforma abierta y vea cómo se llama cada componente en
su catálogo.

**Consecuencia mientras siga abierta:** la Fase A emite catálogos remotos por URL (que son
campos `select` normales, sin componente prohibido y sin credencial) y **no** emite el
autollenado por CURP. Un campo que lo declare se reporta como hueco `API-04` y queda de captura
manual.

**Si se resuelve que sí se puede emitir, la regla no es "emitirlo siempre":** solo endpoints
públicos. INEGI, SEPOMEX y SIPUBEH responden sin credencial (verificado el 2026-08-28). RENAPO y
SAT no, y `guia_modelado_gpm.md` es explícita al respecto —"no insertes tokens de APIs en campos
`api_ajax`; toda llamada autenticada hazla a través de `Acciones` de tipo PHP"—, en línea con el
riesgo SEG-04 ("fuga de secretos: API keys de Keycloak y RENAPO expuestas en las peticiones AJAX
del navegador"). Un trámite que pida un endpoint autenticado se reporta como hueco y se manda a
una Acción PHP.

## Cuestión resuelta: `SINTAXIS_ESTRICTA` (2026-08-31)

`SINTAXIS_ESTRICTA` en `nucleo/reglas.py` está en `False` y **ahí se queda**. Controla si una
regla de transición se emite como `@@campo=='valor'` o como `@@campo->value === 'valor'`.

La documentación interna sostenía que la primera forma falla con campos complejos. Quedó
**refutado con prueba empírica en la plataforma**, documentada en
`planeacion/actas/2026-08-30-prueba-en-plataforma.md`:

- Cuatro exports auténticos **publicados** usan `@@campo == "valor"` sobre campos `select`
  (constancia-ambiental, pago-de-bases, test-ciudadano-4-pasos, busqueda-testamento).
- Prueba de runtime: un trámite compilado con la constante en `False` emitió `@@procede=='si'`
  sobre un `select`, y en el portal del ciudadano el flujo **avanzó** al elegir la rama. La
  tarea de origen sólo tenía salidas condicionales (sin transición por defecto), así que sólo
  pudo avanzar porque una regla con `==` evaluó verdadero.

La prueba confirma el valor actual (`False`); no exige cambiarlo. **Sigue en pie que no se
cambie la constante sin una prueba documentada** — y la que hay respalda `False`.

### Las tres preguntas del 2026-08-28, ya probadas en la plataforma (con acta)

El 2026-08-28 se afirmó aquí que tres preguntas habían quedado cerradas por una prueba, pero
sin acta. El 2026-08-31 se probaron de verdad, importando `.gpm` reales a la plataforma, y la
evidencia está en `planeacion/actas/2026-08-30-prueba-en-plataforma.md`. El resultado fue el
**contrario** de lo afirmado en dos de las tres:

1. **¿Basta `catalog_type: "manual"` sin `catalog_url`?** **NO.** Reventaba al importar
   (`Undefined property: stdClass::$catalog_url`, `CampoSelect.php:468`). Arreglado emitiendo
   las cuatro claves aunque tres queden vacías (**PLAT-1**, cerrado). El compilador ya lo hace.
2. **¿Acepta la plataforma un `proceso_id` que ella no emitió?** **NO.** Lo reasigna al importar
   y **no reescribe** las referencias `->where('proceso_id', N)` dentro del PHP de las acciones,
   así que el contador de folios apuntaba a un proceso inexistente y el folio quedaba roto tras
   importar (**PLAT-4**). **Cerrado el 2026-08-31:** el folio se llavea ahora por el nombre de la
   variable en `dato_seguimiento.valor`, sin `proceso_id` — la forma de `constancia-ambiental` y
   `pago-de-bases`, que corre en runtime. Ver el invariante del folio arriba y `pendientes.md`.
3. **`SINTAXIS_ESTRICTA` (`@@campo=='valor'`)** — **sigue sin poder probarse.** Exige un `.gpm`
   con una compuerta con regla de transición, y ningún `.gpm` que este compilador produce trae
   una (el flujo sale lineal, `FLU-01`). Para probarla habría que ramificar un manifiesto a mano.

Lección que se mantiene: una afirmación de "resuelto" sin acta hace que la siguiente persona deje
de buscar. Toda pregunta de plataforma se cierra con un archivo en `planeacion/actas/` —el `.gpm`,
la fecha, la pantalla y lo observado— citado desde aquí y desde `pendientes.md`.

### Verificado de punta a punta el 2026-08-31

El compilador produce `.gpm` importables completos: el expediente real de Testamento
(Diccionario + TO-BE + AS-IS) se compiló, se importó sin error y la plataforma reconstruyó 9
formularios, 10 tareas, 46 campos y 9 conexiones —exactamente lo emitido—. Dos defectos de
longitud de columna que la suite local no atrapaba se corrigieron en esa prueba (nombres de
formulario/tarea capados a 60; nombre técnico de campo derivado capado a 30, porque la columna
`campo.nombre` no admite los 40 que producía una etiqueta larga). Cuarta prueba del acta.

### Lote de reingeniería del 2026-09-02 — PLAT-7/8/9 (suite 245 → 268)

Seis expedientes con insumos reales del equipo de Simplificación se importaron a
`modelador.hidalgo.gob.mx` (procesos 1068-1073). Tres defectos que la suite de escritorio no
atrapaba salieron en pantalla al importar:

- **PLAT-7** — `Data too long for column 'nombre'`: el nombre técnico `@@` que declara el
  analista pasaba entero (`@@fecha_vencimiento_certificado_anterior`, 38 chars). El extractor
  solo capaba a 30 el nombre que *proponía*. Ahora capa las tres rutas, reporta `DIC-06`, y el
  validador marca `EST-05` (bloqueante) si `campo.nombre` pasa de 30.
- **PLAT-8** — `Invalid argument supplied for foreach()`: los `select`/`radio` salían sin
  opciones. El extractor no leía varios formatos de catálogo (coma, ` / `, `<br>`, envoltura
  `(catalogo: …)`, Boolean con `Sí-No` en la columna Límite). Parser ampliado; Boolean →
  `{Sí, No}`. Piso seguro: un `select`/`radio` sin opciones, sin endpoint y sin campo padre se
  degrada a texto (hueco `DIC-07`, regla `EST-06`).
- **PLAT-9** — un «Selector de fecha (calendario)» se clasificaba como `select` porque «select»
  es subcadena de «selector». `selector de fecha`/`calendario` → `date`.

### Degradación silenciosa de catálogos — `EST-07`

`Estado Civil` de Testamento venía `(Catálogo: Soltero        casado       <br>Divorciado
Viudo <br>Unión Libre)`: separadores irregulares (corridas de espacios además del `<br>`). El
extractor partía solo por `<br>` y emitía **3 opciones basura** — `Soltero        casado`,
`Divorciado  Viudo`, `Unión Libre` — y el `.gpm` compilaba **sin un solo hallazgo**.

- `extractores/diccionario.py` (`_despegar`): tras partir por el separador, una corrida de 2+
  espacios/tabs por dentro de una opción se trata como separador perdido (`Soltero  casado` →
  `Soltero`, `casado`). Un espacio simple (`Unión Libre`) se respeta.
- `validador/reglas.py` (`EST-07`, aviso): una opción de `select`/`radio` con una corrida de
  espacios en el texto se reporta — red de seguridad para un `.gpm` compilado antes del
  arreglo o un manifiesto escrito a mano. No bloqueante: la lista existe, solo está mal partida.

### Endurecimiento de la auditoría (2026-09-08)

- **Simulador (`simulador/html.py`):** todo dato del manifiesto que entra al DOM por
  `innerHTML` pasa por `esc()` (un `<br>` o un `<img onerror>` en una etiqueta —visto en
  catálogos reales— no rompe el render ni ejecuta nada). El JSON incrustado en el `<script>`
  se emite con `_js()`, que escapa `<` para que un nombre con `</script>` no cierre la
  etiqueta. `fetch()` de catálogos remotos con `AbortController` a 8 s.
- **Asistente web (`web/app.py`):** cabeceras `X-Content-Type-Options: nosniff` /
  `X-Frame-Options: SAMEORIGIN` en toda respuesta; `GET /vistas/{sid}` sirve el HTML subido
  con `Content-Security-Policy: sandbox` (origen opaco, sin scripts, sin mismo origen); las
  subidas se cortan a `_MAX_SUBIDA` (10 MB) por archivo.
- **`nucleo/reglas.py`:** el `&&` se parte solo fuera de las comillas (`_SEPARADOR_AND`), así
  un valor `'Smith && Sons'` no se toma como separador de condiciones.
- **`nucleo/limites.py`:** los topes de columna de la plataforma (`LIMITE_CAMPO_NOMBRE` = 30,
  `LIMITE_FORMULARIO_NOMBRE` = 60) viven en un solo lugar; `esquema`, `validador`, `diccionario`
  y `expediente` lo importan.
- **`extractores/expediente.py`:** un `.md` en Latin-1/Windows-1252 se lee con `errors="replace"`
  en vez de reventar con un traceback.

## Tests

- Cada módulo tiene su `tests/test_<modulo>.py`. Antes de escribir código, escribe la prueba que
  falla.
- Nada se comitea sin que la suite pase: `.venv/bin/pytest -v`
- Las pruebas que necesitan material real se saltan cuando no está disponible; nunca fallan por
  eso. Se configuran con `GPMC_EXPORTS`, `GPMC_GPM` y `GPMC_WIKI`.
- Los archivos de referencia **se leen, nunca se modifican**.

## Lo que el agente no puede hacer sin aprobación humana

- Modificar este `CLAUDE.md`.
- Cambiar `SINTAXIS_ESTRICTA`.
- Relajar una aserción de prueba para que pase. Si una prueba falla, se corrige el código o se
  reporta el problema — no se ablanda el criterio.
- Sobrescribir cualquier archivo `.gpm` existente.

## Mejoras recientes (Septiembre 2026)

### 1. Ramificación del flujo desde el Mermaid (`expediente._flujo_ramificado`)
El extractor construye un flujo **no lineal** desde el diagrama TO-BE, y **solo si es
seguro** (spec 2026-09-03, Parte 2). Las cuatro condiciones, todas obligatorias — si una
falla, el flujo sale lineal y se reporta `FLU-01`, exactamente como antes:

1. Cada nodo `tarea` casa 1:1 por nombre con una pantalla del Diccionario (se acepta el
   prefijo de carril: `Area: Cotiza` casa con la pantalla `Cotiza`).
2. Cada compuerta nombra **exactamente un** `@@campo`, y ese campo existe en el manifiesto.
3. Cada arista que sale de una compuerta trae etiqueta, y esa etiqueta resuelve a un valor
   del catálogo del campo (por valor técnico o por etiqueta visible), o `Sí`/`No`.
4. Toda compuerta está alimentada por una tarea, y sus ramas van a tareas.

Cuando ramifica, emite `FLU-03` (`por_confirmar`): «se ramificó solo; confirma el emparejado
nodo↔pantalla». `mermaid._ARISTA` acepta las dos formas de etiqueta de arista de Mermaid:
`A -- texto --> B` (la que usan los expedientes del equipo) y `A -->|texto| B` (la que
prescribe la plantilla para las compuertas). Ejemplo conforme y verificado:
`ejemplos/expedientes/constancia-de-residencia/`. **Ningún `.gpm` ramificado se ha importado
aún a la plataforma**; hasta hacerlo con acta, la ramificación no está probada en runtime.

### 2. Soporte de Alias para variables truncadas (Mitigación de DIC-06)
Cuando un nombre de variable excede los 30 caracteres (el límite de la base de datos para la columna `campo.nombre` que tumba el import con `Data too long`), el extractor sigue reportando el hueco **`DIC-06`** y emite el nombre truncado seguro en el `.gpm`. Sin embargo, `diccionario.py` ahora mantiene un **alias** interno en memoria durante la extracción. Esto permite que las reglas de visibilidad (y otras fórmulas en el texto) que sigan usando la referencia larga (`@@nombre_muy_largo`) se resuelvan correctamente sin obligar al analista a corregir toda la documentación del expediente.

### 3. Autocompletado `api_ajax` (Pendiente)
Aún se mantiene el hueco `API-04` que degrada el componente a captura manual. Implementarlo requiere un ejemplo validado del JSON esperado por la plataforma en el arreglo `extra` del campo, y no contamos con esa estructura en este momento.
