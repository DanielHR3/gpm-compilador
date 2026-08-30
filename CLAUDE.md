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

- **El folio se emite siempre con bloqueo transaccional sobre la columna `contador`.** Nunca
  `->count()`, nunca `rand()`. Ambas formas producen folios que colisionan.
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

## Cuestión abierta

`SINTAXIS_ESTRICTA` en `nucleo/reglas.py` está en `False`. Controla si una regla de transición se
emite como `@@campo=='valor'` o como `@@campo->value === 'valor'`.

Hay documentación que sostiene que la primera forma falla con campos complejos, pero **los
exports de referencia disponibles la usan**. No se puede resolver leyendo archivos: requiere una
prueba empírica en la plataforma.

**No cambies esa constante sin que exista esa prueba documentada.** Cuando llegue la respuesta,
es lo único que hay que tocar.

### Lo que se afirmó resuelto el 2026-08-28, y sigue sin acta

Se registró aquí que tres preguntas habían quedado cerradas por una prueba en la plataforma:
que `@@campo=='valor'` evalúa bien, que la plataforma acepta un `proceso_id` que ella no emitió,
y que `catalog_type: "manual"` basta sin `catalog_url`.

**Esa prueba no está documentada en el repositorio**: no consta qué `.gpm` se importó, en qué
fecha, ni qué se observó. Las tres siguen listadas como abiertas en `planeacion/pendientes.md`,
y este archivo no puede decir lo contrario mientras falte la evidencia. Es plausible que la
prueba ocurriera —y si ocurrió, vale mucho— pero una afirmación sin acta hace que la siguiente
persona deje de buscar.

Para cerrarlas: escribir `planeacion/actas/` con el archivo, la fecha, la pantalla y lo
observado, y citarlo desde aquí y desde `pendientes.md`.

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
