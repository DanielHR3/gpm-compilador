# API de estado para Simplifica (primera entrega) y nuevo nombre

**Fecha:** 2026-11-06 · **Estado:** borrador para aprobación de Daniel.
Nota de origen: bóveda, `04 - Requerimientos y cambios/2026-11-06 - Liga con Simplifica (módulo de Reingeniería).md`.
Diseño del lado de Simplifica: bóveda de Simplifica, `06 - Informes y entregables/2026-11-06 - Diseño del módulo de Reingeniería (liga con Compilador GPM).md` (M-107, M-108).

## Intención

El módulo de Reingeniería de Sistema-3.0 (Simplifica) lista los trámites con acción de
Digitalización en agendas validadas. Luis necesita ver, junto a cada uno, en qué etapa está su
expediente aquí. Hoy Sistema-3.0 lo captura a mano. Esta entrega le da una puerta de **solo
lectura** para saberlo solo.

## Metas

- Cumplir el contrato que Sistema-3.0 ya tiene escrito (`shared/compilador.py`, rama
  `feat/modulo-reingenieria`), sin que Sistema-3.0 cambie.
- Unir un trámite de Simplifica con su expediente por `ruts_id`.
- Autenticación de servicio separada de las cuentas de persona.

## No metas (en esta entrega)

- Subir expedientes, leer sugerencias de la comparativa, pedir el estimador: segunda entrega,
  se diseña con lo que Luis pida tras usar el estado.
- Escribir en Simplifica o leer su base. La dependencia va en un solo sentido: Simplifica lee.
- Datos personales del ciudadano en la respuesta.
- Cambiar el stack de Sistema-3.0 (decisión suya del 2026-10-22).

## Anti-metas

- Que una respuesta inventada parezca real: un entregable sin evidencia es `null`, nunca una
  fecha supuesta.
- Que el token de servicio abra algo más que esta lectura.
- Emparejar dos trámites distintos por nombre parecido y mostrarle a Luis el expediente ajeno.

## Contrato (fijado por Sistema-3.0)

`GET /api/v1/expedientes?ruts_id=<id>` con `Authorization: Bearer <token de servicio>`.

```json
{"expedientes":[{"analista":"…","actualizado":"AAAA-MM-DD",
 "entregables":{"as-is":"AAAA-MM-DD"|null,"to-be":…,"diccionario":…,"bpmn":…,"gpm":…,"aprobacion":…,"publicado":…}}]}
```

- Sistema-3.0 toma `expedientes[0]`. Lista vacía = «Por iniciar».
- Siempre las siete claves de `entregables`, con fecha o `null`.
- Sistema-3.0 calcula la etapa: el entregable más avanzado con fecha (publicado, aprobacion,
  gpm/bpmn, diccionario, to-be, as-is). Aquí no se calcula etapa.
- Sistema-3.0 espera respuesta en menos de 4 s; si falla muestra el último estado con fecha.

## Piezas

1. **`tramite.ruts_id` opcional** en `nucleo/manifiesto.py`. `extractores/metadatos` lo lee del
   frontmatter del AS-IS. **Sin emparejado por nombre** (decisión de Daniel, 2026-11-06):
   Sistema-3.0 solo manda el `ruts_id`, así que un expediente aparece únicamente si su AS-IS lo
   trae. Si falta, se reporta el hueco `META-RUTS` (`por_confirmar`, no bloquea). Los expedientes
   existentes salen «Por iniciar» hasta que se les agregue el `ruts_id`.
2. **El endpoint** en el asistente web, módulo nuevo `web/api_estado.py`, solo lectura.
3. **Token de servicio** en variable de entorno (`GPMC_TOKEN_SERVICIO`), comparado en tiempo
   constante. Sirve **únicamente** para esta ruta; no abre sesión ni otras rutas. Si la variable no
   está puesta, la ruta responde 404 (no existe). El middleware de `acceso.py` hoy exige sesión
   en toda `/api/`: la ruta se exceptúa ahí y valida su propio token. Cada consulta entra a la
   auditoría como acción de servicio, sin persona.
4. **Nombre nuevo: Telar** (mi propuesta; Daniel la aprobó en chat). Cambia el nombre visible y
   el dominio. El paquete y la CLI `gpmc` se quedan hasta que haya razón para tocarlos.

## De dónde sale cada entregable (mis llamadas, marcadas)

Cada entregable tiene su evidencia en la sesión; la fecha se guarda en el registro persistente
(ver abajo), con `ruts_id` como llave:

| Entregable | Evidencia | Mi llamada |
|---|---|---|
| `as-is` | `Análisis AS-IS.md` | primera vez que aparece |
| `to-be` | `Propuesta TO-BE.md` | primera vez que aparece |
| `diccionario` | `Diccionario de Datos.md` | primera vez que aparece |
| `bpmn` | no existe como archivo propio | siempre `null` por ahora |
| `gpm` | registro de la descarga del `.gpm` pasando la puerta del linter | fecha de esa descarga en la auditoría; `null` si nunca |
| `aprobacion` | no hay evidencia automática | `null` hasta que Daniel decida (ver abajo) |
| `publicado` | solo lo sabe una persona | `null` hasta que Daniel decida (ver abajo) |

`actualizado` = la fecha más reciente entre los entregables presentes. `analista` = cadena vacía:
las cuentas no tienen campo de nombre y solo Luis usa el Compilador desde Simplifica (Daniel,
2026-11-06). No se toca la subida de expedientes. Mi llamada; si luego hace falta, se agrega
un nombre a la cuenta.

**Registro de estado persistente (decisión de Daniel).** La purga borra sesiones sin actividad
en 7 días y con ellas la evidencia. Por eso, al extraer y en cada hito (archivo nuevo, descarga
del `.gpm` que pasa la puerta), se escribe una línea en `<almacén>/estado.jsonl` con `ruts_id` y
la fecha de cada entregable; `_purgar_sesiones` no lo toca (mismo patrón que `tablero.jsonl`:
escritura atómica, lectura tolerante). El endpoint lee **este registro**, no las carpetas.
Las fechas son del día en `America/Mexico_City` y no cambian al re-extraer: se guarda la
primera vez que el entregable aparece. Los hitos de `planeacion/registro` ganan si existen.

## Empareje

Solo por `ruts_id` exacto (texto, sin espacios sobrantes). Una sesión sin `ruts_id` no aparece nunca.
Un `ruts_id` tiene una sola línea en `estado.jsonl`.

Formato del frontmatter (lo escribe la «ficha.yaml» de Simplifica, confirmado por esa sesión):
`ruts_id: "4321"`, con o sin comillas, alfanumérico de 1 a 20 caracteres. Sin prefijo.

## Errores

- Token ausente o inválido: 401 con cuerpo `{"error":"…"}`, sin pistas de qué falló.
- `ruts_id` ausente en la consulta: 422.
- Sin sesiones que casen: 200 con `{"expedientes":[]}`.

## Pruebas

Una por comportamiento: contrato exacto (siete claves), `null` sin evidencia, 401 sin token y con
token de persona, 404 con la variable sin definir, empareje solo por `ruts_id` exacto, `META-RUTS` cuando falta, sobrevivencia a la purga, y que ninguna respuesta lleve datos de campos del ciudadano. Sin red.

## Dominio y despliegue

El dominio propio lo pide Simplifica para la fase 2 (hoy `d1zuvw2fi2wub0.cloudfront.net`,
alias `compilador-gpm.commit-lab.pro`). El dominio nuevo se registra y se alía en el mismo
paso que el nombre; hasta entonces el alias actual sigue sirviendo. El token se guarda en
`scripts/aws/estado.env`, nunca en git ni en la URL, y se rota como `SECRET_KEY`.

## Decisiones tomadas (Daniel, 2026-11-06)

1. `aprobacion` y `publicado` quedan en `null`; el botón «marcar como…» va en la segunda entrega.
2. `gpm` cuenta solo si la descarga pasó la puerta del linter (respuesta 200, no 409).

## Mis llamadas (Daniel puede revertirlas)

- Auditoría de servicio como `servicio:simplifica`; sin auditoría si corre `--sin-usuarios`.
- Con varias sesiones del mismo `ruts_id` se usa el registro de ese `ruts_id` (uno solo).
- El token ve todas las dependencias (Simplifica es central) y solo abre esta lectura.
- Zona horaria `America/Mexico_City`.
- Pendiente: dominio de Telar (¿`telar.commit-lab.pro`?); se decide al desplegar.

## Lo que queda al constructor

Forma interna del módulo, nombre exacto de la variable de entorno, cómo leer la auditoría para la
fecha de `gpm`, el formato del hueco `META-RUTS` en la SPA y la lectura del analista.
