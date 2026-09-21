# Vistas de solo lectura: cómo documentarlas

**Para:** equipo de Simplificación Administrativa
**De:** Dirección de Gestión Tecnológica
**Fecha:** 2026-09-21
**Responde a:** su mensaje sobre las filas «Vista de solo lectura (Origen → Destino)»

---

## Lo primero: tienen razón

**No son campos.** Su lectura del proceso es correcta, y además la plataforma tiene exactamente
la pieza que ustedes describen: un **Paso en modo Visualización** dentro de la tarea del actor que
mira.

No lo decimos de memoria. Lo comprobamos sobre los doce trámites auténticos que tenemos, hechos a
mano en la plataforma y exportados de ella:

| | |
| --- | --- |
| Pasos en modo Visualización | **19**, repartidos en **8 de los 12** trámites |
| Trámites que usan solo el modo Edición | 4 |

Y el patrón es el que ustedes plantean. En *Acceso a la Información Pública*:

| Tarea | Paso | Modo | Pantalla |
| --- | --- | --- | --- |
| 1. Captura de Solicitud (Ciudadano) | 1 | edición | **9250** — Vista_Solicitud_Acceso |
| 2. Revisión de UT (Funcionario) | 1 | **visualización** | **9250** — la misma |
| 2. Revisión de UT (Funcionario) | 2 | edición | 9251 — Vista_Revision_UT |

El funcionario ve **la misma pantalla** que llenó el ciudadano. Mismo identificador de pantalla,
ningún campo nuevo, ninguna variable nueva. Tal como ustedes lo describieron.

---

## Sus tres preguntas

### 1. ¿Una fila con Tipo «N/A» y `@@vista_…` se puede tratar como Paso de visualización?

**El Paso sí. El `@@vista_…`, mejor no.**

Un Paso no tiene variable propia: apunta a **una pantalla que ya existe**. No hay nada que nombrar.
Y ese `@@` de más es justo lo que hoy nos produce el campo fantasma que les señalamos: nuestro
extractor toma **el primer `@@` que encuentra en la Descripción** y lo usa como nombre del campo.
En Reposición eso creó ocho nombres duplicados, y tres campos distintos acabaron llamándose
`@@estatus_tramite`.

Así que el `@@vista_` no resuelve el problema: lo causa.

**Cómo preferimos que lo documenten:** en la **Propuesta TO-BE**, no en el Diccionario. En la tarea
del actor que mira, una línea:

> Muestra la **Pantalla 2 (Captura del ciudadano)** en solo lectura, y luego captura su dictamen.

Si les sirve dejar la fila en el Diccionario como recordatorio, consérvenla **sin ningún `@@` en la
Descripción**. Con eso deja de convertirse en campo.

> **Lo que nos toca a nosotros, y lo decimos claro:** hoy el compilador **no construye** esos Pasos.
> De los seis trámites del lote que compilamos, **ninguno** salió con un Paso de visualización: el
> flujo se emite en línea recta. La pieza existe en nuestro formato intermedio, pero falta que el
> compilador la derive de sus documentos. Es trabajo nuestro, no suyo, y con su respuesta ya
> sabemos qué construir.

### 2. ¿Puede el mismo `@@` aparecer en más de una pantalla?

**Preferimos que no**, y esta vez la razón no es nuestra comodidad.

Buscamos esa forma en los doce trámites auténticos. **No aparece para este propósito.** El único
nombre repetido que hay —`observaciones`, en Licitaciones— resultó ser otra cosa al abrirlo: son
**dos campos distintos y editables**, en dos ramas que nunca ocurren juntas, que coinciden en el
nombre. No es un dato mostrado de nuevo.

La regla que sigue este proyecto es no emitir formas que no hayamos visto en un trámite real que
funcione, porque un error así no se nota hasta que el trámite ya está en producción.

Y hay una razón práctica: un nombre repetido **nos rompe de verdad**. Ayer encontramos que, con
dos campos del mismo nombre, nuestra comprobación se quedaba con el primero; si ese no traía
catálogo, dejaba pasar cualquier valor. Ya está corregido de un lado y en cola del otro.

**Lo que sí está observado**, para el caso del ciudadano que ve las observaciones del funcionario:

- **Mostrar la pantalla completa** del funcionario en modo visualización, como el caso anterior.
- **Un campo propio marcado como solo lectura.** La plataforma tiene ese atributo por campo y lo
  usa: **47 campos** de los trámites auténticos están marcados así.

### 3. Si ninguna sirve, ¿cómo lo documentamos?

Mientras tanto, y para que puedan ajustar **Reposición** y **Prórroga** sin esperarnos:

| Caso | Dónde va | Cómo se escribe |
| --- | --- | --- |
| El funcionario revisa lo que llenó el ciudadano | **TO-BE**, en la tarea del funcionario | «Muestra la Pantalla N en solo lectura» |
| El ciudadano vuelve a ver un dato que capturó el funcionario | **Diccionario**, como campo propio | Su propio `@@`, marcado `[Solo lectura]`, con su catálogo si lo tiene |
| Cualquiera de los dos | — | **Ningún `@@` ajeno en la Descripción** |

Sobre la visibilidad: de acuerdo con ustedes. Queda **«Siempre visible»**, y el momento en que se
muestra lo decide el recorrido del proceso, que ya está en las compuertas del TO-BE.

---

## Una pregunta que ni ustedes ni nosotros podemos contestar leyendo

Su caso 2 depende de algo que no sabemos: **si dos campos con el mismo `@@` en pantallas distintas
comparten el valor** en la plataforma, o si son dos datos independientes que coinciden en el
nombre. Ningún trámite auténtico lo demuestra.

Eso se prueba, no se razona: montamos un trámite de prueba, lo importamos, lo recorremos como
ciudadano y miramos qué pasa. Es como cerramos la pregunta de la sintaxis de las condiciones el 31
de agosto, y quedó acta. Cuando tengamos la respuesta se la pasamos, y si resulta que sí comparten
valor, la recomendación de arriba cambia y se lo diremos con la misma claridad.

Mientras tanto, lo de la tabla funciona y no les obliga a rehacer nada dos veces.

---

**Gracias por la respuesta.** Nos ahorró trabajo: estábamos a punto de pedirles que cambiaran el
Diccionario, y lo que hacía falta cambiar era nuestro compilador.
