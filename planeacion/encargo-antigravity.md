# Encargo — 2026-08-30

Trabajo pendiente tras la revisión final de la Fase A. `main` está en `7e1a949`, con
**231 pruebas en verde**, y todo pusheado.

**Trabaja en tu propia rama.** No commitees en `main`.

## Contexto en cuatro líneas

`gpmc` convierte un Diccionario de Datos en markdown a un archivo `.gpm` para la plataforma
de modelado de Hidalgo. **No tenemos el código de la plataforma.** La regla que gobierna todo
el proyecto es reproducir lo que los exports auténticos contienen, byte a byte, nunca razonar
sobre cómo "debería" ser el formato. El export de referencia está en
`~/Desktop/Projects/GPM/Acceso a la Informacion/acceso-informacion-publica.gpm` — **ábrelo
antes de escribir cualquier cosa sobre el formato `.gpm`**.

---

## Tarea 1 — Dos pruebas del simulador que no pueden fallar

La revisión final las marcó como Important. Ambas guardan criterios de aceptación del spec y
**pasarían aunque el comportamiento que protegen se rompiera por completo**.

### 1a. `tests/test_simulador.py::test_un_endpoint_no_registrado_no_inventa_una_url`

```python
assert "consultarfc" not in html.split("const PANTALLAS")[1].split("const ACTORES")[0] \
    or "catalogo_url" not in html.split("raro_sol")[1].split("}")[0]
```

`generar()` nunca serializa `endpoint` en el payload, así que la primera cláusula es siempre
`True` y el `or` cortocircuita. Si mañana `_catalogo_de_campo` empezara a inventar una URL
para endpoints desconocidos, esta prueba seguiría pasando.

**Arreglo:** quita el `or`. Parsea el JSON de `const PANTALLAS={...};` y assertea
positivamente que el campo `raro_sol` **no tiene** la clave `catalogo_url`.

### 1b. `tests/test_simulador.py::test_un_select_sin_catalogo_resoluble_sale_deshabilitado`

Sus dos aserciones tampoco pueden fallar:

- `'<input name="raro_sol"' not in html` — los campos se dibujan **en el navegador** desde
  plantillas `${c.nombre}`, así que un nombre concreto de campo nunca aparece en el HTML que
  genera Python. Es `False` incluso para un manifiesto solo de texto.
- `"(sin catálogo resoluble)" in html` — ese literal está dentro de `_GUION`, presente en
  todas las páginas siempre.

Lo irónico es que el comentario de la propia prueba advierte del riesgo ("Assertear solo
'disabled' seria vacuo") y acto seguido comete otra versión del mismo error.

**Arreglo:** assertea sobre el payload. Parsea `const PANTALLAS`, y comprueba que el campo
`raro_sol` tiene `tipo == "select"` y **no** tiene `catalogo_url`. Deja anotado en la prueba
que el renderizado deshabilitado en sí no es verificable sin un runtime de JavaScript.

**Verifica que tus pruebas nuevas de verdad fallan** si rompes el comportamiento. Rompe el
código a propósito, mira la prueba en rojo, y deshaz. Si no falla, la prueba no sirve — es
exactamente el defecto que estás corrigiendo.

---

## Tarea 2 — Un `select` con catálogo manual **y** endpoint emite una forma que no existe

`src/gpmc/compilador/a_gpm.py`, en `_campo_gpm`. Hoy produce:

```jsonc
"extra": {"catalog_type": "url", "catalog_url": "...", "object_response": "...", "key_object": "..."},
"datos": [{"etiqueta": "A", "valor": "a"}]
```

En el export auténtico, el select manual (`dictamen_ut`) lleva `datos`; los tres con catálogo
por URL **no llevan esa clave en absoluto**. Esta combinación no aparece en ningún export.
Dado que la regla del proyecto es no emitir formas no observadas, es la clase exacta de
defecto contra la que existe esa regla.

**Arreglo:** cuando se resuelve un catálogo remoto, pasa `datos=None`, y levanta un hueco que
diga que las opciones manuales se descartaron porque el endpoint gana. No las tires en
silencio — el invariante del proyecto es *"propone, no adivina"*.

El código de hueco libre siguiente es `API-05`. Los existentes están en
`planeacion/specs/2026-08-28-fase-A-apis-y-catalogos.md` §5.

---

## Tarea 3 — Escribir el acta de la prueba en la plataforma

**Esta es la de más valor, y es la única que ni yo ni ninguna sesión puede hacer sola: hace
falta abrir la plataforma.**

El 2026-08-28 se registró en `CLAUDE.md` que tres preguntas habían quedado resueltas
empíricamente. La revisión final lo marcó como **Critical** porque no consta qué archivo se
importó, en qué fecha, ni qué se observó — y `CLAUDE.md` exigía que ese cambio no ocurriera
"sin que exista esa prueba documentada". Ya restauré la salvaguarda y las tres volvieron a
estar abiertas.

Escribe `planeacion/actas/2026-08-28-prueba-en-plataforma.md` con, para cada pregunta:

1. Qué archivo `.gpm` se importó, y de qué manifiesto salió
2. Fecha y hora aproximada
3. En qué pantalla de la plataforma se observó el resultado
4. Qué se vio **exactamente** — no "funcionó", sino lo que apareció

Las tres preguntas:

- **¿Basta `catalog_type: "manual"` en un `select` sin `catalog_url`?** El export auténtico
  trae solo esa clave; la bitácora interna del 2026-08-10 sostiene que hacen falta cuatro y
  que sin ellas revienta `CampoSelect.php`.
- **¿Acepta la plataforma un `proceso_id` que ella no emitió?** Importa mucho: `acciones.py`
  emite `->where('proceso_id', N)` para el contador de folios, así que un id equivocado o
  colisionado rompe el primer invariante del dominio.
- **`SINTAXIS_ESTRICTA`** — si `@@campo=='valor'` evalúa bien, o hace falta
  `@@campo->value === 'valor'`.

**Si alguna no se probó realmente, dilo en el acta y déjala abierta.** Una pregunta marcada
como abierta vale infinitamente más que una cerrada sin evidencia. Nadie te va a reprochar
que falte una prueba; sí importa que alguien deje de buscar por una afirmación sin respaldo.

---

## Tarea 4 — Probar la cascada en la plataforma

**Nadie ha hecho esto y es la brecha grande.** El compilador emite catálogos remotos con
cascada, y el JSON coincide **clave por clave** con el export auténtico — verificado tres
veces por separado. Pero *coincidir* no es *funcionar*.

Pasos:

1. Compila el expediente de *Acceso a la Información* (está en
   `~/Desktop/expediente-acceso-informacion/`, tres `.md`). Trae `estado_sol` con endpoint
   `mgee` y `municipio_sol` con `mgem`, dependiente del primero.
2. Impórtalo a `modelador.hidalgo.gob.mx`
3. Abre la vista del formulario y **elige un estado**
4. Observa si el desplegable de municipios se puebla solo

Lo que el compilador emite hoy para `municipio_sol`:

```jsonc
"extra": {"catalog_type": "url",
          "catalog_url": "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@estado_sol",
          "object_response": "datos",
          "key_object": "nomgeo, cvegeo",
          "dependent_populated": "1",
          "populated_by": ["estado_sol"]},
"catalogo_id": "1"
```

**Qué mirar si NO se puebla:** `estado_sol` guarda `cvegeo` ("13") y muestra `nomgeo`
("Hidalgo"). La cascada solo funciona si la plataforma interpola el **valor guardado**, no la
etiqueta: `mgem/13` devuelve 84 municipios, `mgem/Hidalgo` no devuelve nada. Si sale vacío,
abre las herramientas de desarrollo y mira **qué URL se pidió**. Esa observación es el
hallazgo, y vale más que cualquier tarea de código de esta lista.

Anota el resultado en el mismo acta.

---

## Reglas de la casa (no negociables)

- **Python 3.9**: nada de `X | None`, usar `Optional[X]`.
- **Español sin acentos** en identificadores, comentarios y docstrings. Los textos que lee una
  persona sí llevan acentos.
- Los comentarios explican *por qué*, no *qué*.
- **Nada se comitea sin que la suite pase**: `.venv/bin/pytest -v`. Línea base: **231 passed,
  22 skipped, 1 warning** (ese warning es de fastapi/httpx y es previo).
- **Nunca ablandar una aserción para que pase.** Si una prueba existente estorba, se corrige el
  código o se reporta — no se afloja el criterio.
- **No modificar `CLAUDE.md`** salvo para la Tarea 3, y solo para reflejar lo que el acta
  demuestre.
- **No editar archivos con scripts `fix_*.py`.** Edita los archivos directamente. Los ocho
  scripts sueltos que quedaron en la raíz son cómo se coló una regresión sin que nadie la
  notara: el enlace de Aprobación recuperó `target="_blank"`, que el navegador bloquea, y la
  prueba que lo cubría se puso en rojo sin que se viera. Si ya no los necesitas, bórralos.
- **No reportar como completo lo que está a medias.** Si una tarea queda al 70%, dilo. Vale
  más un informe honesto que un tablero verde.

## Dónde está la verdad

- Export auténtico: `~/Desktop/Projects/GPM/Acceso a la Informacion/acceso-informacion-publica.gpm`
- Estado verificado y lo diferido: `planeacion/pendientes.md` — solo registra lo comprobado
  ejecutando código, con cómo se comprobó
- Spec y plan de Fase A: `planeacion/specs/2026-08-28-fase-A-apis-y-catalogos.md` y
  `planeacion/planes/2026-08-29-fase-A-apis-y-catalogos.md`

## Cómo entregar

Rama propia, commits pequeños cuyo mensaje diga *por qué*, y al final un resumen honesto: qué
quedó hecho, qué quedó a medias, y qué no pudiste comprobar.
