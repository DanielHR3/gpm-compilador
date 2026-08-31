# Acta — prueba de importación en la plataforma GPM

- **Fecha:** 2026-08-30
- **Plataforma:** `modelador.hidalgo.gob.mx`, sesión "Capacitación COEMERE"
- **Archivo importado:** `prueba-cascada.gpm`, compilado desde
  `manifiesto.yaml` con `estado_sol` (endpoint `mgee`), `municipio_sol`
  (endpoint `mgem`, dependiente de `estado_sol`) y `sexo_manual` (catálogo
  manual de dos opciones).
- **`proceso_id` emitido:** `50604`

Esta acta existe porque `CLAUDE.md` exige que las cuestiones abiertas no se
cierren "sin que exista esa prueba documentada". El 2026-08-28 se registraron
tres respuestas sin acta; ninguna de ellas resultó cierta.

---

## Resultado 1 — La plataforma NO respeta un `proceso_id` ajeno

**Observado:** el proceso apareció en el listado como **id 1045**, el siguiente
de la propia secuencia de la plataforma, y con homoclave `AIHYPCsp` asignada por
ella. El `50604` que emitimos se descartó por completo.

En el mismo listado, `1044 — b5a8defd46ca96d2 (Nuevo)` confirma lo mismo para un
import anterior.

**Contradice** lo que la bitácora del 2026-08-28 afirmaba: *"la plataforma traga
y respeta un proceso_id ajeno (generado localmente por hash) sin corromperse"*.

**Consecuencia para el código:** derivar `proceso_id` de un hash del nombre no
sirve para nada — la plataforma lo reasigna. El motivo original del cambio (que
`acciones.py` emite `->where('proceso_id', N)` para el contador de folios) sigue
siendo real, pero **la solución tiene que venir de la plataforma, no de
nosotros**: el `.gpm` no puede fijar ese número. Habrá que revisar qué hace
`php_folio` con un `proceso_id` que la plataforma cambió al importar.

## Resultado 2 — `catalog_type: "manual"` NO basta

**Observado, literal, en la vista del formulario:**

```
A PHP Error was encountered
Severity: Notice
Message: Undefined property: stdClass::$catalog_url
Filename: models/CampoSelect.php
Line Number: 468
```

El error sale en `sexo_manual`, el campo con catálogo manual, emitido con
`extra: {"tamano": ..., "catalog_type": "manual"}` — exactamente la forma que
trae el select manual del export auténtico
`acceso-informacion-publica.gpm` (`dictamen_ut`).

**La bitácora interna del 2026-08-10 tenía razón**, y la Fase 0 se equivocó al
seguir el export sobre ella. El spec argumentó que "cuando la documentación y el
archivo de referencia se contradicen, manda el archivo"; la revisión final lo
aprobó. Los tres nos equivocamos.

**La lección, más fina que la regla anterior:** el export auténtico dice qué
**produce** la plataforma, no qué **acepta**. Son cosas distintas. Ese
`dictamen_ut` salió de la plataforma ya con su `catalogo_id` y su `accion_id`
asignados por ella; nosotros emitimos una versión que su propio importador no
tolera.

**Consecuencia para el código:** un `select` manual debe emitir también
`catalog_url`, `object_response` y `key_object`, aunque vayan vacíos — que es lo
que la bitácora del 10-ago pedía desde el principio.

## Resultado 3 — El catálogo remoto simple SÍ funciona

**Observado:** el desplegable `Estado` se pobló con los **32 estados de INEGI**
(Aguascalientes … Hidalgo … Zacatecas), consultados en vivo desde
`https://gaia.inegi.org.mx/wscatgeo/v2/mgee`.

Es el primer resultado que confirma que el trabajo de la Fase A produce algo que
la plataforma ejecuta de verdad.

## Resultado 4 — La cascada NO funciona: dos defectos distintos

**Observado:** el desplegable `Municipio` trajo dos opciones de error de INEGI:

```
404
Para la clave <> <> no existe información, valores para las claves de
AGEE[01..32] y AGEM[001..n}
```

y ambas con `value=" cvegeo"` — **con un espacio delante**.

Eso revela dos cosas independientes:

**4a. La plataforma no interpoló `@@estado_sol`.** Pidió la URL literal y INEGI
respondió que la clave `<> <>` no existe. Falta averiguar qué necesita la
plataforma para sustituir el valor del campo padre: puede que `dependent_populated`
y `populated_by` no basten por sí solos, o que la interpolación solo ocurra en el
portal del ciudadano y no en la vista de edición del modelador.

**4b. `key_object` se parte por la coma sin recortar espacios.** Nuestro valor es
`"nomgeo, cvegeo"` — copiado tal cual del export— y la plataforma acabó buscando
una clave llamada `" cvegeo"`. Con `"nomgeo,cvegeo"` (sin espacio) probablemente
funcione. Es otra instancia de lo mismo: el export muestra un valor que la
interfaz de la plataforma escribió y sabe leer en su contexto, no necesariamente
lo que su importador acepta.

---

## Qué queda abierto

- **`SINTAXIS_ESTRICTA` sigue sin probarse, y no por descuido.** Probarla exige un
  `.gpm` con al menos una compuerta con regla de transición, y **ningún `.gpm`
  que este compilador produce tiene una sola**: el flujo sale siempre lineal, que
  es justo lo que reporta el hueco `FLU-01`. Para cerrarla haría falta primero
  ramificar un manifiesto a mano.
- **La interpolación del campo padre** (4a) — qué la activa.
- **Si `key_object` sin espacio arregla la cascada** (4b) — una prueba más.

## Limpieza pendiente

El proceso **1045 — "PRUEBA DGT - cascada de catalogos (borrar)"** quedó en la
plataforma. Nombrado así a propósito para que sea evidente que se puede eliminar.

---

## Segunda prueba — 2026-08-31, con los arreglos (proceso 1046)

Se re-importó `prueba-cascada-v2.gpm`, compilado con las dos correcciones.
Resultado del import: proceso **1046** (de nuevo, la plataforma reasignó el id;
emitimos 50604). Homoclave asignada por ella.

### Confirmado — Resultado 2 ARREGLADO (el error de PHP)

En la vista del formulario del proceso 1046, el campo `sexo_manual` (catálogo
manual) **ya no muestra ningún error**. Los tres campos se dibujan limpios.
Comparado con el proceso 1045, donde el mismo campo mostraba el recuadro rojo
`Undefined property: stdClass::$catalog_url`. **Emitir las cuatro claves
(catalog_url/object_response/key_object vacías) resolvió el fallo.** La bitácora
del 10-ago tenía razón.

### Confirmado — Resultado 4b ARREGLADO (el espacio de key_object)

Leído el DOM del proceso 1046:

- `estado_sol` se pobló con los 32 estados **y sus valores correctos**:
  `Hidalgo=13`, `Aguascalientes=01`, etc. En el proceso 1045 el `read_page` no
  llegaba a mostrar esos valores.
- Las opciones de `municipio_sol` ahora traen `value="cvegeo"` **sin el espacio
  delante** (en 1045 era `value=" cvegeo"`).

**Quitar el espacio de key_object corrigió la lectura de la clave.**

### Sigue abierto — Resultado 4a (interpolación del campo padre)

`municipio_sol` sigue mostrando el error de INEGI `Para la clave <> <> no existe
información`. Se comprobó por JavaScript que seleccionar Hidalgo en `estado_sol`
y disparar el evento `change` **no repobla** `municipio_sol` en la vista del
constructor.

**Diagnóstico:** la vista de edición del modelador es el *form builder*; no
cablea la cascada. La interpolación de `@@estado_sol` y el repoblado por
`dependent_populated`/`populated_by` solo ocurren en el **runtime del ciudadano**
(el formulario publicado que llena el solicitante). Esa prueba no se hizo: exige
previsualizar o publicar el trámite como ciudadano, un flujo distinto.

**Lo que SÍ quedó verificado del lado del `.gpm`:** la plataforma almacenó
`catalog_url` con `@@estado_sol`, `dependent_populated:"1"` y
`populated_by:["estado_sol"]` — el import los aceptó sin quejarse. Si el runtime
del ciudadano los honra o no es lo único que falta.

### Balance

| Pregunta | Estado |
|---|---|
| `catalog_type: "manual"` sin las 4 claves | **Arreglado y confirmado** |
| `key_object` con espacio | **Arreglado y confirmado** |
| Catálogo remoto simple (Estado) | Funciona, con valores correctos |
| Cascada de punta a punta (4a) | Pendiente del runtime del ciudadano |
| `proceso_id` ajeno | La plataforma lo reasigna (1046). Sin cambio |

### Limpieza — hecha el 2026-08-31

Los dos procesos de prueba (**1045** y **1046**) se eliminaron de la plataforma.
El listado se verificó por JavaScript: cero filas "PRUEBA DGT" restantes.

Queda en la plataforma el proceso **1044** ("b5a8defd46ca96d2"), de una sesión
anterior con otro agente, con nombre de id de sesión. No se tocó porque no salió
de esta tarea; conviene revisarlo por separado.

---

## Tercera prueba — 2026-08-31, con acción de folio (proceso 1047)

Se importó `prueba-folio-cascada.gpm`, con una acción `folio` ligada a la tarea.
El manifiesto emitió `proceso_id: 59201`, y el PHP de la acción lo llevaba
hardcodeado en `->where('proceso_id', 59201)`.

### PLAT-4 CERRADO — la plataforma NO reescribe el proceso_id dentro de la acción

**Observado en la pestaña Acciones → Editar del proceso 1047** (leído del DOM y
confirmado a ojo en el editor):

- El proceso se importó como **1047** (de nuevo, la plataforma reasignó el id;
  emitimos 59201).
- El PHP de la acción de folio **sigue diciendo `proceso_id, 59201`**, en sus dos
  ocurrencias (el `where` del lock y el `updateOrInsert`). `1047` no aparece por
  ningún lado en la acción.

**Conclusión:** la plataforma reasigna el id del proceso al importar pero **no
reescribe las referencias `proceso_id` dentro del PHP de las acciones**. El
contador de folios del proceso 1047 consultaría la fila `proceso_id = 59201`, que
corresponde a un proceso que no existe. **El folio queda roto tras cualquier
importación.**

Es un defecto real y grave, y **no se puede arreglar emitiendo "el id correcto"**,
porque el id lo asigna la plataforma en tiempo de importación — nosotros no lo
conocemos al compilar. Caminos posibles, todos por confirmar con el proveedor o
con más pruebas:

1. Que el PHP de la acción **no** hardcodee un `proceso_id`, sino que use una
   variable que la plataforma exponga en tiempo de ejecución (algo como el id del
   proceso actual). Habría que averiguar si GPM ofrece esa variable.
2. Que el folio se resuelva por otro mecanismo de la plataforma (¿un componente
   nativo de folio?) en vez de PHP a mano.
3. Reescribir el `proceso_id` de las acciones **después** de importar, ya sabiendo
   el id asignado — un paso manual o un post-proceso.

Esto invalida además el esquema de `proceso_id` por hash de `a_gpm.py`: da igual
qué número emitamos, la plataforma lo ignora para el proceso y lo conserva —roto—
dentro de la acción. Ver `src/gpmc/compilador/acciones.py :: php_folio`.

**Nota de dominio:** el primer invariante de `CLAUDE.md` es "el folio se emite
siempre con bloqueo transaccional sobre la columna contador". El PHP lo hace bien
(`lockForUpdate`), pero apunta al proceso equivocado. El invariante se cumple en
la forma y falla en el destino.

### PLAT-3 — la cascada, seguía sin poder probarse aquí

Igual que en la segunda prueba: la vista de edición es el form builder y no cablea
la cascada. Sigue pendiente el runtime del ciudadano.

### Limpieza

Queda por borrar el proceso **1047**. (El 1044 de otra sesión sigue aparte.)

### Limpieza — hecha

Proceso 1047 eliminado el 2026-08-31; verificado por JavaScript: cero procesos
"PRUEBA DGT" restantes. Queda el 1044 de otra sesión, aparte.
