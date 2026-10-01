# Tres decisiones que hoy se corrigen en la plataforma — diseño

Fecha: 2026-10-01 · Estado: aprobada (2026-10-01) · Solicita: Daniel

## Propósito

Un `.gpm` que sale del compilador importa limpio y aun así necesita tres retoques a mano en el
modelador antes de servir:

| Defecto | Qué pasa hoy | Registro |
| --- | --- | --- |
| El trámite sale oculto | `ruts.publico` nace en `False` y ningún extractor lo cambia ni lo dice. El funcionario ve el trámite; el ciudadano no. | P-17 |
| Los oficios salen al enviar la solicitud | `documentos.atar_a_tareas` cuelga cada documento de la primera tarea que ya tiene sus datos. Con plantillas sin variables, esa es siempre la primera. Queda un `DOC-04` `por_confirmar` sin control. | P-19 |
| La restricción por grupo no ata | `expediente.py` emite como grupo el nombre del actor en mayúsculas iniciales (`Direccion De Verificacion Vehicular`). La plataforma usa identificadores (`verificacion_vehicular`). No se avisa de nada. | PLAT-11 |

Este sub-proyecto lleva esas tres decisiones al asistente: cada una es un aviso con su control en
la tarjeta, y lo decidido viaja en el manifiesto y de ahí al `.gpm`.

Éxito: un analista decide las tres en la revisión y el `.gpm` importado aparece en el portal,
restringe las tareas del funcionario a su grupo y genera cada oficio en la tarea que eligió, sin
abrir el modelador para corregirlo.

## Decisiones tomadas (Daniel, 2026-10-01)

| Pregunta | Decisión |
| --- | --- |
| ¿Cierran la descarga del `.gpm`? | No. Solo avisan: las tres son `por_confirmar`. Sin decidir, el `.gpm` sale como hoy. |
| ¿De dónde sale el identificador del grupo? | Texto libre con sugerencias de los grupos ya vistos en exports. |
| ¿Se cambia la puerta del linter? | No. `nucleo/huecos.bloquean` no se toca. |

## Fuera de alcance

- Las notificaciones del Diccionario (P-11): segundo sub-proyecto, con su propia spec.
- Las plantillas sin `{{variables}}` (P-23).
- Derivar cualquiera de las tres sin preguntar.
- El `POST /resolver` de HTML en `web/app.py` (lo retira SP3) y la CLI: los avisos salen en
  `gpmc extraer` y se corrigen en el manifiesto, como cualquier otro.

## Los tres avisos

Todos `por_confirmar`. Dos códigos nuevos y uno que ya existe.

| Código | Ubicación | Cuándo se emite | Propuesta |
| --- | --- | --- | --- |
| `META-07` (nuevo) | `metadatos` | Siempre, uno por trámite | «Sí» cuando el actor de la tarea inicial es de autoservicio; si no, ninguna |
| `DOC-04` (existe) | `documentos/<acción>` | Como hoy, uno por documento atado | Ninguna: el mensaje ya nombra la tarea en que quedó |
| `ACT-01` (nuevo) | id del actor | Uno por actor de tipo `grupo` | Ninguna |

`META-07` y `ACT-01` se emiten en `extractores/expediente.py`, después de armar el flujo: es el
único punto donde se conocen a la vez los actores y la tarea inicial. `metadatos.py` no cambia.

La propuesta de `META-07` solo se enseña. No se aplica sola: `publico` sigue en `False` hasta que
una persona diga que sí.

## Resolver

`POST /api/v1/expedientes/{sid}/resolver` gana tres tipos en `ResolucionIn` (`ubicacion` +
`valor`), con su entrada en `_TIPO_A_CODIGO`. Cada resolución escribe en el manifiesto y tacha el
aviso, como las demás.

| Tipo | Valor | Escribe | 422 cuando |
| --- | --- | --- | --- |
| `meta07` | `si` o `no` | `tramite.ruts.publico` | el valor es otro |
| `doc04` | id de una tarea | quita la acción de la tarea donde esté y la añade a `acciones_despues` de la elegida | la acción no existe, la tarea no existe, o la tarea no es válida (abajo) |
| `act01` | nombre del grupo | `actor.grupos_usuarios = [valor]` | el actor no existe o no es de tipo `grupo`, o el valor queda vacío o trae saltos de línea |

Decir «no» en `meta07` también tacha el aviso: la decisión se tomó.

**No se valida la forma del grupo.** Un export auténtico trae `grupo práctica`, con espacio y
acento, así que exigir minúsculas y guion bajo rechazaría un nombre real. Tampoco se pone tope de
longitud: no hay un límite de columna observado y no se inventa uno.

### Qué tarea vale para un documento

Función pura nueva en `extractores/documentos.py`:

```python
def tareas_posibles(accion, flujo, pantallas) -> "list[tuple[str, list[str]]]"
```

Devuelve, en el orden del flujo, cada tarea con las variables de la plantilla que le faltan. Una
tarea vale si la lista sale vacía y no es terminal.

- A una tarea le «llegan» los campos de sus propias pantallas y los de toda tarea desde la que se
  puede alcanzar siguiendo las conexiones.
- La terminal nunca vale: ningún export observado cuelga un documento del cierre.

`atar_a_tareas` pasa a usar la misma función y toma la primera que vale. En un flujo lineal el
resultado es idéntico al de hoy. En uno ramificado deja de contar los campos de tareas que no
están antes de ella en el flujo, que hoy entran solo por ir antes en la lista.

Límite conocido: «alcanzable desde» incluye un campo capturado solo en una de dos ramas que se
juntan. La regla acota, no demuestra; por eso el aviso sigue siendo de una persona.

## Sugerencias de grupos

`nucleo/grupos.py` con una tupla `OBSERVADOS` y nada más. Arranca con los cuatro identificadores
que constan en `planeacion/pendientes.md` (PLAT-11): `area_primer_contacto`, `licitaciones_admin`,
`transparencia_admin`, `verificacion_vehicular`. `grupo práctica` no entra: es un grupo de
pruebas.

**Sin verificar por mí contra los exports:** las rutas `GPMC_EXPORTS` y `GPMC_GPM` no están
configuradas en esta máquina. El plan incluye releer los exports y ampliar la lista cuando estén
a la mano; hasta entonces el comentario del módulo dice de dónde salió cada entrada.

`GET /api/v1/grupos` devuelve `{"grupos": [...]}`. Es una lista de ayuda: escribir un grupo que no
está en ella es válido.

## Pantalla

En `features/huecos/TarjetaHueco.tsx`, tres ramas antes de la genérica de `por_confirmar`:

| Código | Control | Qué hace |
| --- | --- | --- |
| `META-07` | `ControlSiNo` (nuevo) | Dos botones: «Sí, que aparezca en el portal» y «No, que quede oculto». Si hay propuesta, se lee arriba. |
| `DOC-04` `por_confirmar` | `ControlTarea` (nuevo) | Selector con las tareas del flujo. Las que no valen salen deshabilitadas con el motivo a la vista («faltan: folio, fecha»; «es el cierre del trámite»). La actual viene elegida. |
| `ACT-01` | `ControlTexto` con `sugerencias` | El campo de texto de siempre con un `<datalist>` de `GET /api/v1/grupos`. Si lo escrito no parece identificador (minúsculas, dígitos, guion bajo), una nota lo dice sin impedir guardar. |

Los tres conservan «Dejarlo así», que cae al `reconocer` de siempre: deja constancia y no cambia
el manifiesto. `DOC-04` de nivel `falta_dato` (el documento no cabe en ninguna tarea) sigue como
hoy.

`features/huecos/tareasDeDocumento.ts` replica la regla de `tareas_posibles` sobre el manifiesto
que la pantalla ya tiene, igual que `candidatos.ts` replica `verificar.py`. El servidor es la
autoridad: la pantalla anticipa, el 422 decide.

Además:

- `lenguaje.ts`: títulos de `META-07` («Visibilidad en el portal») y `ACT-01` («Grupo de usuarios
  de un responsable»), y redacción llana de los tres, **anclada** al mensaje del backend como las
  demás.
- `observaciones.ts`: `META-07` y `ACT-01` van a `plataforma`, donde ya está `DOC-04`. Se cuentan
  al pie y no se le mandan a Simplificación.
- `lib/types.ts` y `lib/api.ts`: los tres tipos nuevos de `Resolucion` y `leerGrupos()`.

## Tablero

`web/tablero.resumir` deja fuera de la cuenta de avisos a `META-07` y `ACT-01`. Se emiten por
construcción en todos los trámites, y el tablero ordena por número de trámites: quedarían
primeros en todas las dependencias sin decir nada del expediente.

Cambia respecto a lo que se dijo en la conversación de diseño, donde se anticipó que aparecerían
en la matriz.

## Pruebas

Antes del código, la prueba que falla. Ninguna toca la red.

**Servidor (pytest)**

- Extractor: `META-07` sale siempre, con propuesta solo si inicia el ciudadano; `ACT-01` sale uno
  por actor de grupo y ninguno por el ciudadano; los dos son `por_confirmar` y `bloquean` no los
  devuelve.
- `tareas_posibles`: flujo lineal, flujo ramificado, plantilla sin variables, tarea terminal.
- `atar_a_tareas`: mismo resultado que hoy en los casos lineales que ya tienen prueba.
- Resolver: `meta07` cambia `publico` y el `.gpm` compilado trae `public` y `add_in_menu` en `"1"`;
  `doc04` mueve el evento a la tarea elegida y no deja copia en la anterior; `act01` cambia
  `GruposUsuarios` de las tareas de ese actor; cada 422 de la tabla.
- Tablero: una línea no cuenta `META-07` ni `ACT-01`.

**Pantalla (vitest)**

- Los dos controles nuevos, `ControlTexto` con sugerencias, las ramas de `TarjetaHueco`,
  `tareasDeDocumento`, y las redacciones con su ancla.

**Pruebas existentes que cambian.** La búsqueda no encontró ninguna que fije el total de avisos
de una extracción: casi todas filtran por código. Si al implementar alguna cambia, se lista con
su motivo para aprobación; no se ablanda una aserción para que pase.

Línea base del 2026-10-01: 1004 aprobadas y 24 saltadas en el servidor.

## Lo que solo se comprueba en la plataforma

Dos cosas no las cierra la suite y, según la regla del proyecto, piden acta en
`planeacion/actas/`:

1. **El grupo real ata.** Importar un `.gpm` con `verificacion_vehicular` y comprobar que la
   tarea del funcionario queda restringida. No está probado que el import case `GruposUsuarios`
   por nombre con un grupo existente.
2. **El oficio sale en la tarea elegida.** Colgarlo de la tarea de validación y comprobar que se
   genera al terminarla y no al enviar la solicitud.

Que `publico` enciende el trámite en el portal ya está probado (PLAT-6).

Hasta que haya acta, la documentación dice «emitido, no probado en runtime».

## Documentación

- `CLAUDE.md`: sección nueva con los tres avisos y sus reglas. Su texto se propone en el plan y
  se aplica solo con aprobación, como pide el propio archivo.
- `planeacion/pendientes.md`: P-17, P-19 y PLAT-11 pasan a «decisión en el asistente; falta acta».
- `docs/guias/LEEME - equipo de Simplificación.md`: una línea en «Resuelve los huecos».
