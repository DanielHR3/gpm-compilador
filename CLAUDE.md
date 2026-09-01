# CLAUDE.md — gpm-compilador

Convenciones del repositorio. Compilador que convierte un manifiesto YAML de trámite en un
archivo `.gpm` importable en una plataforma de modelado BPMN.

## Stack

- Python 3.9 o superior, entorno virtual en `.venv/`
- `pydantic` para el modelo del manifiesto
- `pyyaml` para leer y escribir manifiestos
- `pytest` para las pruebas
- `fastapi` + `uvicorn` como extra opcional `[web]`
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
│   ├── formato.py      serializacion byte-exacta
│   ├── esquema.py      primitivos: tarea, paso, formulario, campo, conexion, proceso
│   ├── manifiesto.py   modelo Pydantic del manifiesto y su coherencia
│   └── reglas.py       evaluador UNICO de reglas de transicion
├── extractores/        insumos en markdown -> manifiesto
├── compilador/         manifiesto -> .gpm, y los cuatro arquetipos de Accion
├── validador/          hallazgos estructurales, de folio, de escapado y de credenciales
├── simulador/          recorrido navegable del tramite y analisis estatico
├── planeacion/         registro y proyeccion del ciclo de trabajo
├── estimador.py        complejidad del tramite
├── web/                asistente de 5 pasos
└── cli.py              las 7 ordenes
```

**Dependencia en un solo sentido:** `web`/`cli` → `compilador`/`validador`/`extractores` →
`nucleo`. Nada por debajo de `web` conoce interfaz de usuario: son funciones sobre archivos, sin
estado de sesión. Esa separación es la que permite que la CLI y las pruebas existan sin navegador.

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
   así que el contador de folios apunta a un proceso inexistente: el folio queda roto tras
   importar (**PLAT-4**, abierto — bloquea usar acciones de folio en producción).
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
