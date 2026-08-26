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

## Cuestión abierta

`SINTAXIS_ESTRICTA` en `nucleo/reglas.py` está en `False`. Controla si una regla de transición se
emite como `@@campo=='valor'` o como `@@campo->value === 'valor'`.

Hay documentación que sostiene que la primera forma falla con campos complejos, pero **los
exports de referencia disponibles la usan**. No se puede resolver leyendo archivos: requiere una
prueba empírica en la plataforma.

**No cambies esa constante sin que exista esa prueba documentada.** Cuando llegue la respuesta,
es lo único que hay que tocar.

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
