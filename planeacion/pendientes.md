# Pendientes — estado verificado

Última verificación: 2026-08-31, suite en **233 passed, 22 skipped**.

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

## Abiertos

### PLAT-3 · La cascada no se ha probado en el runtime del ciudadano — LA BRECHA GRANDE

`municipio_sol` depende de `estado_sol`. La plataforma **aceptó y almacenó** la metadata de
cascada (`catalog_url` con `@@estado_sol`, `dependent_populated`, `populated_by`), verificado
al importar el proceso 1046. Pero **la interpolación de `@@estado_sol` solo ocurre en el
runtime del formulario que llena el ciudadano**, no en el *form builder* del modelador — ahí
el desplegable de municipios siempre muestra el error 404 de INEGI porque no hay estado
seleccionado.

Para cerrarlo: previsualizar o publicar el trámite como ciudadano, elegir un estado, y ver
si municipios se puebla. Si sale vacío, mirar en las herramientas de desarrollo qué URL se
pidió — si `mgem/13` (correcto) o `mgem/@@estado_sol` sin sustituir. Ver
`actas/2026-08-30-prueba-en-plataforma.md`, resultado 4a.

### PLAT-4 · `proceso_id`: la plataforma lo reasigna, y falta ver qué hace con las acciones

Confirmado importando (50604 → 1045 → 1046): la plataforma **descarta** el `proceso_id` que
emitimos y asigna el suyo. Eso hace que derivarlo por hash sea inocuo pero inútil.

Lo que queda abierto: `acciones.py` emite PHP con `->where('proceso_id', N)` para el contador
de folios. Si la plataforma reasigna el id del proceso pero **no** reescribe ese `N` dentro
de la acción, la acción queda apuntando al id viejo y el folio se rompe. No se probó porque
el `.gpm` de prueba no tenía acciones. Un `.gpm` de prueba con una acción de folio lo cierra.

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

## Preguntas que solo se cierran frente a la plataforma

`CLAUDE.md` registra desde el 2026-08-28 que las tres primeras quedaron resueltas por una
prueba empírica. **Esa prueba no está documentada en el repositorio**: no consta qué archivo
se importó, en qué fecha, ni qué se observó. El propio `CLAUDE.md` exigía que el cambio no
se hiciera "sin que exista esa prueba documentada".

Si la prueba ocurrió —y es plausible que sí—, vale la pena escribir el acta: qué `.gpm`, qué
pantalla de la plataforma, qué se vio. Sin eso, la siguiente persona no puede distinguir un
hallazgo de una suposición.

1. **¿Basta `catalog_type: "manual"` en un `select` sin `catalog_url`?** El export auténtico
   trae solo esa clave; la bitácora interna del 2026-08-10 pide cuatro.
2. **¿Acepta la plataforma un `proceso_id` que ella no emitió?** Importa además porque con
   el `"900"` fijo anterior *todos* los trámites compartían la fila 900 del contador de
   folios (`acciones.py` emite `->where('proceso_id', …)`), lo que colisiona contra el
   primer invariante del dominio.
3. **`SINTAXIS_ESTRICTA`** — `@@campo=='valor'` contra `@@campo->value === 'valor'`.

## Menores conocidos

- `_campo_gpm` sin anotaciones de tipo, mientras su hermana `_validacion_de` sí las lleva.
- El docstring de `_campo_gpm` afirma como hecho el fallo de `CampoSelect.php`, que es una
  de las preguntas de arriba.
- Ningún manifiesto de `ejemplos/` trae un `select`, así que la prueba de serialización
  nunca ejercita ese camino.
- En `test_extractor_mermaid.py`, la señal `:::nota` nunca se ejercita sola: todos los
  fixtures de nota llevan también la forma `[/.../]`.
- La forma `[/.../]` marca como nota un nodo aunque declare carril propio.
