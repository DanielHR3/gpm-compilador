# Pendientes — estado verificado

Última verificación: 2026-08-29, suite en **192 passed, 21 skipped**.

Este archivo solo registra lo que se comprobó ejecutando código o leyendo el árbol. Una
afirmación sin evidencia aquí vale menos que nada: hace que alguien deje de buscar.

---

## Resueltos, verificados

| | Hallazgo | Cómo se comprobó |
|---|---|---|
| **P-01** | Los nombres de tarea arrastraban la anotación del TO-BE | El TO-BE de Testamento produce `'Capturar el Formato de Aviso de Testamento directamente en GPM, a distancia'` — sin el `*(Tarea GPM #7920…)*` |
| **P-04** | `i_comp` caía posicionalmente en la columna `Dependencia` y ganaba sobre el tipo declarado | Un híbrido con `Dependencia = fecha_nac` y `Tipo (GPM) = select` ahora emite `select`. Antes emitía `date` |
| **P-05** | `extraer()` tenía dos ramas casi gemelas de ~60 líneas | Extraído `_extraer_campos(filas, pantalla, r)`; el archivo pasó de 330 a 289 líneas y ya no hay dos cuerpos paralelos |
| — | El enlace de Aprobación reintrodujo `target="_blank"` | `test_revision_enlaza_al_simulador_en_la_misma_pestana` pasó de rojo a verde el 2026-08-29 |

## Abiertos

### P-02 · Un `select` sin opciones se dibuja como caja de texto en el simulador

`simulador/html.py` pinta `<select>` solo si `c.catalogo` trae opciones. Un campo `select`
cuyo catálogo se puebla por URL sale como `<input>`, lo que contradice el contrato que el
propio módulo declara: *"el simulador no puede mentir sobre lo que hará la plataforma"*.

Se disuelve en parte cuando los catálogos remotos existan, pero el caso "select declarado
sin catálogo resoluble" seguirá existiendo y debe dibujarse como desplegable vacío y
deshabilitado.

### P-03 · Sin AS-IS, todos los trámites se ven iguales

Subiendo solo el Diccionario, el trámite queda sin nombre y `/revisar` y `/historial`
muestran `[por confirmar]` para todos. `META-04` sí se reporta, pero el nombre no es el
lugar donde se reporta un hueco: se filtra además al nombre del archivo descargado y al
`proceso_id` derivado.

La revisión final recomendó que la portada pida el nombre del trámite cuando no hay AS-IS.
El Diccionario es el único insumo obligatorio, así que ese camino es de primera clase, no
un borde.

### Deuda de proceso

- **`tests/test_estimador.py` construye sus `Campo` a mano y nunca pasa por el
  extractor.** Esa frontera sin cruzar permitio que quitar `origen` del
  extractor dejara `estimador.integraciones` en 0 para un tramite con 6
  integraciones, sin que ninguna prueba fallara. Detectado y corregido el
  2026-08-29, pero el hueco estructural sigue: ninguna prueba recorre
  Diccionario -> extractor -> estimador de punta a punta. Volvera a morder.

- **8 scripts `fix_*.py` sueltos en la raíz del repo**, sin seguimiento. Es el mismo patrón
  que la Fase 1 limpió (`patch.py`, `patch_dic.py`). Parchear archivos con scripts en vez
  de editarlos es lo que permitió que `target="_blank"` volviera sin que nadie lo notara.
- `dummy.md` sin seguimiento.
- Fase A tiene spec (`planeacion/specs/2026-08-28-fase-A-apis-y-catalogos.md`) pero **no
  tiene plan de implementación**, y el modelo de datos que ya está en `manifiesto.py`
  (`dependencia_tipo`, `dependencia_campo`, `endpoint`) difiere del que se acordó en el
  diseño (registro de endpoints conocidos + `catalogo_remoto` / `consulta`). Conviene
  reconciliar las dos formas antes de seguir construyendo encima.

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
