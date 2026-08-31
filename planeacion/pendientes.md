# Pendientes — estado verificado

Última verificación: 2026-08-31, suite en **236 passed, 22 skipped**.

Este archivo solo registra lo que se comprobó ejecutando código o importando a la
plataforma. Una afirmación sin evidencia aquí vale menos que nada: hace que alguien deje de
buscar.

---

## Resueltos, verificados

| | Hallazgo | Cómo se comprobó |
|---|---|---|
| **P-01** | Los nombres de tarea arrastraban la anotación del TO-BE | El TO-BE de Testamento produce `'Capturar el Formato de Aviso de Testamento directamente en GPM, a distancia'` — sin el `*(Tarea GPM #7920…)*` |
| **P-04** | `i_comp` caía posicionalmente en la columna `Dependencia` y ganaba sobre el tipo declarado | Un híbrido con `Dependencia = fecha_nac` y `Tipo (GPM) = select` ahora emite `select`. Antes emitía `date` |
| **P-05** | `extraer()` tenía dos ramas casi gemelas de ~60 líneas | Extraído `_extraer_campos(filas, pantalla, r)`; el archivo pasó de 330 a 289 líneas y ya no hay dos cuerpos paralelos |
| — | El enlace de Aprobación reintrodujo `target="_blank"` | `test_revision_enlaza_al_simulador_en_la_misma_pestana` pasó de rojo a verde el 2026-08-29 |
| **PLAT-1** | Un `select` manual con solo `catalog_type` reventaba al importar (`CampoSelect.php:468`) | **Importado a la plataforma** (proceso 1046, 2026-08-31): el error desapareció al emitir las cuatro claves. Ver `actas/2026-08-30-prueba-en-plataforma.md` |
| **PLAT-2** | `key_object` con espacio → la plataforma buscaba una clave inexistente | **Importado**: `estado_sol` cargó los 32 estados con `Hidalgo=13` correcto al quitar el espacio |
| **P-02** | El simulador dibujaba `<input>` para un `select` sin opciones | Fase A: un `select` sin catálogo resoluble sale `<select disabled>`. `test_un_select_sin_catalogo_resoluble_sale_deshabilitado` en verde |
| **PLAT-5** | Nombres largos (`formulario.nombre`, `campo.nombre`) tumbaban el import con `Data too long` | **Prueba de punta a punta del expediente REAL de Testamento**: tras capar nombres (60 para forma/tarea, 30 para campo derivado) la plataforma importó sin error y reconstruyó 9 formularios, 10 tareas, 46 campos y 9 conexiones — exactamente lo emitido. Cuarta prueba en `actas/2026-08-30-prueba-en-plataforma.md` |
| — | ¿El compilador sirve para *crear* `.gpm` importables? | **Sí, verificado en la plataforma el 2026-08-31**: expediente real → `.gpm` → import completo → export de vuelta con los mismos conteos |

## Abiertos

### PLAT-3 · La cascada no se ha probado en el runtime del ciudadano — LA BRECHA GRANDE

`municipio_sol` depende de `estado_sol`. La plataforma **aceptó y almacenó** la metadata de
cascada (`catalog_url` con `@@estado_sol`, `dependent_populated`, `populated_by`), verificado
al importar el proceso 1046. Pero **la interpolación de `@@estado_sol` solo ocurre en el
runtime del formulario que llena el ciudadano**, no en el *form builder* del modelador — ahí
el desplegable de municipios siempre muestra el error 404 de INEGI porque no hay estado
seleccionado.

Verificado el 2026-08-31: el modelador **no expone una vista previa** del formulario del
ciudadano para el proceso importado, y la vista de edición es el form builder, que no cablea
la cascada. Para cerrarlo hace falta llegar al runtime real — publicar el trámite o crear un
expediente de prueba —, una acción con efectos que conviene decidir aparte. La plataforma sí
almacenó la metadata de cascada al importar. Ver `actas/2026-08-30-prueba-en-plataforma.md`.

### PLAT-4 · CONFIRMADO como defecto — el folio se rompe tras importar

Cerrado el 2026-08-31 importando un `.gpm` con acción de folio (proceso 1047). Leído en el
editor de la acción: el proceso quedó como **1047**, pero su PHP de folio **sigue diciendo
`->where('proceso_id', 59201)`** — el id que emitimos, que ya no corresponde a ningún
proceso. La plataforma reasigna el id del proceso pero **NO reescribe las referencias
`proceso_id` dentro del PHP de las acciones**. El contador de folios apunta a un proceso
inexistente: el folio queda roto tras cualquier importación.

No se arregla emitiendo "el id correcto" — lo asigna la plataforma al importar y no lo
conocemos al compilar. Tres caminos posibles en el acta, todos por confirmar con el
proveedor. Esto también invalida el esquema de `proceso_id` por hash de `a_gpm.py`: da igual
qué número emitamos. Ver `actas/2026-08-30-prueba-en-plataforma.md`, tercera prueba, y
`src/gpmc/compilador/acciones.py :: php_folio`. **Bloquea usar acciones de folio en
producción hasta resolverlo.**

### P-03 · Sin AS-IS, todos los trámites se ven iguales

Subiendo solo el Diccionario, el trámite queda sin nombre y `/revisar` y `/historial`
muestran `[por confirmar]` para todos. `META-04` sí se reporta, pero el nombre no es el
lugar donde se reporta un hueco: se filtra además al nombre del archivo descargado y al
`proceso_id` derivado.

La revisión final recomendó que la portada pida el nombre del trámite cuando no hay AS-IS.
El Diccionario es el único insumo obligatorio, así que ese camino es de primera clase, no
un borde.

### Deuda de proceso

- **`cli.py:72` fija `--proceso-id` en `"900"` por omisión; el asistente web lo deriva del
  nombre.** Es una inconsistencia entre los dos caminos, pero tras verificar que la
  plataforma **reasigna** el `proceso_id` al importar (PLAT-4), el valor emitido no llega a
  importar de todos modos. Lo que sí importa es la referencia interna de `acciones.py`
  (`->where('proceso_id', N)`), y eso está en PLAT-4. No arreglar por separado hasta cerrar
  PLAT-4.

- **`tests/test_estimador.py` construye sus `Campo` a mano y nunca pasa por el
  extractor.** Esa frontera sin cruzar permitió que quitar `origen` del extractor dejara
  `estimador.integraciones` en 0 para un trámite con 6 integraciones, sin que ninguna prueba
  fallara. Detectado y corregido el 2026-08-29, pero el hueco estructural sigue: ninguna
  prueba recorre Diccionario → extractor → estimador de punta a punta. Volverá a morder.

- **El proceso `1044` ("b5a8defd46ca96d2") sigue en la plataforma.** Es de una sesión anterior
  con otro agente, con nombre de id de sesión. No salió de esta tarea; conviene revisarlo y
  borrarlo por separado.

*(Cerrado el 2026-08-31: los 8 scripts `fix_*.py` y los `dummy*.md` sueltos se borraron y
`.gitignore` ya los excluye. Fase A tiene spec y plan
—`planeacion/planes/2026-08-29-fase-A-apis-y-catalogos.md`— implementados y fusionados.)*

---

## Preguntas de plataforma — estado al 2026-08-31

Las tres preguntas que la bitácora del 28-ago daba por "resueltas empíricamente" sin acta ya
tienen respuesta real, documentada en `actas/2026-08-30-prueba-en-plataforma.md`:

1. **¿Basta `catalog_type: "manual"` sin `catalog_url`?** **NO** — reventaba
   (`CampoSelect.php:468`). Arreglado y reconfirmado (PLAT-1, arriba).
2. **¿Acepta la plataforma un `proceso_id` ajeno?** **NO** — lo reasigna, y no reescribe las
   referencias dentro de las acciones (PLAT-4, arriba). El folio se rompe.
3. **`SINTAXIS_ESTRICTA`** — **sigue sin poder probarse**: exige un `.gpm` con una compuerta
   con regla de transición, y ningún `.gpm` que este compilador produce tiene una (el flujo
   sale lineal, `FLU-01`). Para probarla habría que ramificar un manifiesto a mano primero.

## Menores conocidos

- `_campo_gpm` sin anotaciones de tipo, mientras su hermana `_validacion_de` sí las lleva.
- El docstring de `_campo_gpm` afirma como hecho el fallo de `CampoSelect.php`, que es una
  de las preguntas de arriba.
- Ningún manifiesto de `ejemplos/` trae un `select`, así que la prueba de serialización
  nunca ejercita ese camino.
- En `test_extractor_mermaid.py`, la señal `:::nota` nunca se ejercita sola: todos los
  fixtures de nota llevan también la forma `[/.../]`.
- La forma `[/.../]` marca como nota un nodo aunque declare carril propio.
