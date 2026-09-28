# Documentos del trámite: qué se dejó de pedir — diseño

Fecha: 2026-09-28 · Estado: aprobada (2026-09-28) · Solicita: Daniel, a partir de lo que pidió Simplificación

## Propósito

La dependencia entrega el AS-IS. Ahí empieza la evaluación de los **documentos que se le
piden al ciudadano**; el resultado es el TO-BE, donde ya no aparecen los que dejaron de ser
necesarios. Ese análisis es el corazón de la reingeniería y hoy no se ve en ninguna parte.

Este módulo lo hace visible: una página por trámite que dice qué documentos pedía el
trámite, **cuáles ya no pide y por qué**.

Éxito: el analista abre la página y lee «De 9 documentos, 5 ya no se piden», con una
tarjeta por documento, su destino y la frase que lo respalda.

## Decisiones tomadas (Daniel, 2026-09-28)

| Pregunta | Decisión |
| --- | --- |
| ¿Documentos, o también pasos? | Solo documentos. |
| ¿Qué destinos hay? | Se elimina · Se conserva · Se sustituye por consulta en línea · Lo genera el sistema. |
| ¿Puede leerlo el agente? | Sí. La autorización de la Fase 3 cubre este análisis. |
| ¿Quién decide? | La persona. El agente propone, la verificación descarta, el analista acepta o corrige. |

## Por qué la comparativa actual no basta

Medido en la revisión de la rama de la comparativa, sobre expedientes reales:

- **Una línea del AS-IS trae varios documentos.** «Vehículo nuevo: tarjeta de circulación,
  factura o carta factura, identificación oficial» cuenta como un requisito.
- **El mismo documento se llama distinto en cada lado**, y el emparejado por subcadena
  falla en los dos sentidos: no casa «Identificación oficial» con «INE del solicitante», y
  sí casa «INE» con «…en línea».
- **No separa lo que entrega el ciudadano de lo que genera el sistema.** «Formato de Pago
  Generado» sale como requisito nuevo.

Las tres son de lectura. Es donde un modelo rinde más que una regla.

## Los destinos

| Destino | Quiere decir | Evidencia que se exige |
| --- | --- | --- |
| `elimina` | Ya no se pide ni se produce | Frase literal del TO-BE que lo diga |
| `conserva` | El ciudadano lo sigue entregando | Campo `file` del Diccionario, de una pantalla del ciudadano |
| `consulta` | El dato se obtiene de un servicio en línea | Campo con autollenado o endpoint, o frase literal del TO-BE |
| `sistema` | El trámite lo genera; nadie lo trae | Acción `documento`, campo `file` de una pantalla que no es del ciudadano, o frase literal del TO-BE |
| `sin_destino` | No se pudo sostener ninguno | Ninguna. Lo decide la persona |

Dos rótulos más, que **no propone el agente**; los calcula el servidor:

- **`agregado`:** campo `file` de una pantalla del ciudadano que ningún documento del AS-IS
  ocupa. Un trámite que pide algo nuevo se enseña, no se esconde.
- **Eliminado sin fundamento:** un documento con destino `elimina` aceptado por la persona
  cuya evidencia no es una frase del TO-BE. Se enseña con esa etiqueta y produce aviso.

## Flujo

1. El analista abre «Documentos del trámite» y pulsa **«Analizar documentos»**. No corre
   solo al extraer: la cuota es limitada y no todo expediente lo necesita.
2. `agentes/documentos.py` arma el contexto y hace **una llamada** por trámite.
3. `agentes/verificar_documentos.py`, sin modelo, comprueba cada propuesta.
4. La página pinta el tablero. Cada tarjeta dice si su destino es propuesto, aceptado o
   corregido.
5. El analista acepta o corrige tarjeta por tarjeta, o acepta todas las verificadas de una vez.

**Sin proveedor o sin autorización**, la página funciona igual: el inventario sale del
lector determinista (`requisitos_del_as_is`), el destino `conserva` del emparejado actual,
y lo demás queda `sin_destino` para que la persona lo asigne.

## Lo que ve el modelo

Tres bloques, con el mismo formato de marcas que la Fase 3:

- `<<AS_IS>>`: el texto del Análisis AS-IS.
- `<<TO_BE>>`: el texto de la Propuesta TO-BE.
- `<<CAMPOS>>`: del manifiesto, una línea por campo `file`, por campo con autollenado o
  endpoint, y por acción `documento`: nombre técnico, etiqueta, pantalla y actor.

Nunca la columna «Ejemplo Real del Campo» del Diccionario, que trae datos de casos reales:
el Diccionario no viaja como texto, solo los campos ya extraídos.

## Lo que contesta

JSON conforme a un esquema:

```json
{"documentos": [{
  "nombre": "Identificación oficial",
  "cita_as_is": "identificación oficial vigente",
  "destino": "conserva",
  "campo": "doc_identificacion",
  "cita_to_be": null,
  "motivo": "El ciudadano la sigue adjuntando en la solicitud.",
  "confianza": "alta"
}]}
```

`motivo` es una frase corta del modelo y se enseña **rotulada como redacción de la IA**,
aparte de las citas, que son texto literal de los documentos.

## La verificación, sin modelo

Cada regla que falla deja la tarjeta en `sin_destino` con el veredicto a la vista. Nunca
se corrige en silencio.

| Regla | Veredicto si falla |
| --- | --- |
| `cita_as_is` aparece en el AS-IS (comparando sin acentos, mayúsculas ni espacios de más) | `cita_inventada`; la tarjeta **se descarta**: el documento no existe en el AS-IS |
| `cita_to_be`, si viene, aparece en el TO-BE | `cita_inventada` |
| `campo`, si viene, existe en el manifiesto | `campo_inventado` |
| `conserva`: el campo es `file` y su pantalla es del ciudadano | `evidencia_insuficiente` |
| `consulta`: el campo tiene autollenado o endpoint, o hay `cita_to_be` | `evidencia_insuficiente` |
| `sistema`: acción `documento`, campo `file` de otro actor, o `cita_to_be` | `evidencia_insuficiente` |
| `elimina`: hay `cita_to_be` | `sin_fundamento` |
| Un mismo campo no respalda dos documentos | `campo_repetido` en el segundo |
| Dos documentos no comparten `cita_as_is` y nombre | `duplicado` en el segundo |

**Cobertura.** Todo requisito que lea `requisitos_del_as_is` tiene que quedar cubierto por
la cita de algún documento. El que no, entra al tablero como tarjeta `sin_destino` con el
veredicto `omitido_por_el_modelo`. El modelo puede partir una línea en varios documentos;
no puede hacer desaparecer ninguna.

## La página

Ruta `/revisar/{sid}/documentos`. Se entra desde el riel de entrega y desde la comparativa.

- **Titular:** «De 9 documentos que pedía el trámite, 5 ya no se piden». Cuenta como «ya no
  se piden» los destinos `elimina`, `consulta` y `sistema` **aceptados**. Mientras haya
  tarjetas sin decidir, el titular lo dice: «…según 6 de 9 documentos revisados».
- **Cómo se simplificó el trámite** (añadido por Daniel, 2026-09-28): bajo el titular, una
  lista en palabras que **nombra** los documentos de cada destino ya decidido: «Se eliminó:
  orden de trabajo», «Se sustituyó por consulta en línea: identificación oficial». Sale
  también en la comparativa y en el documento descargable. Solo cuenta lo decidido por una
  persona; lo propuesto y sin revisar no se afirma.
- **Barra de destinos:** una barra apilada con un tramo por destino, con su cuenta escrita.
- **Tablero:** una columna por destino y una tarjeta por documento. En teléfono las columnas
  se apilan. Solo tarjetas; ninguna `<table>`.
- **Tarjeta:** nombre, destino, estado (propuesto · aceptado · corregido) y confianza.
  Al abrirla: la cita del AS-IS, la evidencia, el motivo rotulado como IA, y los controles
  «Aceptar» y «Cambiar destino».
- **Cambiar destino** es un selector, no arrastrar y soltar: funciona con teclado y en
  teléfono. Al cambiarlo, el analista puede escribir el motivo.
- **Documentos agregados:** sección aparte, debajo del tablero.
- Mientras el agente trabaja, la página dice qué paso va, como la espera de la Fase 3.
- Si el modo de pruebas está activo, la página avisa que el AS-IS y el TO-BE viajan a Gemini.

Colores: los destinos son identidades, no magnitudes, así que **no** usan la rampa
secuencial `--viz-*`. Se define una paleta categórica de cuatro colores, validada con la
guía `dataviz` en claro y en oscuro. Cada tramo y cada columna llevan su nombre escrito.

## Dónde más aparece

- **Comparativa:** cuando todas las tarjetas están decididas, la métrica «Requisitos
  documentales» toma el antes y el después de aquí, con origen `revisado`, y la sección
  «Requisitos, uno por uno» se sustituye por un resumen que enlaza a esta página. Mientras
  falte una decisión, la comparativa sigue como hoy.
- **Documento descargable:** página propia, imprimible, con el titular, la barra y una
  tarjeta por documento. La comparativa descargable la enlaza en su resumen.
- **Observaciones:** un aviso nuevo, `CMP-05` (`por_confirmar`), por cada documento
  eliminado sin fundamento: «El TO-BE ya no pide «X» y no dice por qué». Va en la sección
  de la comparativa. No bloquea el `.gpm`.

## Arquitectura

`web` → `agentes` / `comparativa` → `extractores` → `nucleo`. `agentes` sigue siendo el
único paquete que habla con un modelo y **nada de `agentes` escribe en el manifiesto**.

| Pieza | Responsabilidad |
| --- | --- |
| `comparativa/documentos.py` (nuevo) | Tipos `Documento` e `Inventario`; inventario determinista; titular y cuentas; `agregados`. Sin modelo. |
| `agentes/prompt_documentos.py` (nuevo) | Instrucción, esquema y contexto. Versión `docs-v1`. |
| `agentes/verificar_documentos.py` (nuevo) | Las reglas de la tabla de arriba. Sin modelo. |
| `agentes/documentos.py` (nuevo) | Una llamada con los reintentos de siempre, verificación, registro en `bitacora-ia.jsonl`. |
| `web/api_documentos.py` (nuevo) | `GET …/documentos`, `POST …/documentos/analizar` (202, en segundo plano), `POST …/documentos/{id}/decision`, `POST …/documentos/aceptar-verificados`, `GET …/documentos/descarga`. |
| `web/sesiones.py` | `documentos.json` por sesión: estado, pasos, propuestas y decisiones. |
| `web/acceso.py` | `documentos.analizar` y `documentos.decidir` en la auditoría. |
| `frontend/src/features/documentos/` (nuevo) | Tablero, tarjeta, barra de destinos, espera. |

**Candado.** `POST …/analizar` usa `fase3.puede_generar`: proveedor con licencia, o modo de
pruebas autorizado. Sin eso responde 409 con el motivo y la página ofrece el camino manual.

**Al cambiar el expediente.** Si tras un `/resolver` cambian los campos `file` del
manifiesto, las decisiones que apuntan a un campo que ya no existe vuelven a `sin_destino`
y la página lo avisa. No se pierden las demás.

## Errores

| Situación | Qué ve la persona |
| --- | --- |
| Sin AS-IS en la sesión | «No se cargó el AS-IS: no hay documentos de antes que revisar.» |
| Sin TO-BE | El análisis corre; ningún `elimina` tendrá fundamento y la página lo explica |
| Red o cuota | Tres intentos con espera creciente; después, el motivo y el camino manual |
| Respuesta que no es JSON conforme | No se reintenta. Motivo a la vista y camino manual |
| El modelo devuelve cero documentos | Inventario determinista, todo `sin_destino` |
| AS-IS o TO-BE demasiado largos | Se recorta con aviso, como el lote de `DIC-08` |

## Pruebas

Ninguna toca la red: `ProveedorFalso` en todas.

- `test_documentos.py`: inventario determinista; titular con todo decidido y con
  decisiones pendientes; `agregados`; origen `revisado` en la comparativa.
- `test_verificar_documentos.py`: una prueba por regla de la tabla; cobertura; una línea
  partida en tres documentos; cita con acentos y espacios distintos.
- `test_agente_documentos.py`: respuesta buena, respuesta inválida, error de red con
  reintento, documento inventado, registro en la bitácora de IA.
- `test_api_documentos.py`: candado cerrado (409), analizar y leer, decidir, aceptar
  verificados, decisión sobre un campo que dejó de existir, auditoría, descarga escapada.
- Frontend: tablero por `article`/`aria-label`, cambio de destino con teclado, espera,
  camino manual sin proveedor, titular con pendientes.
- Con material real (`GPMC_WIKI`): el inventario determinista de los seis expedientes no
  revienta. Se salta sin material.

## Fuera de alcance

- Pasos del proceso y su destino.
- Medir la calidad del agente contra la bóveda (`medir-ia`). Queda para después.
- Arrastrar y soltar.
- Que el agente redacte el fundamento que el TO-BE no trae.
- Editar el TO-BE desde la página.
- Agregados de este análisis en el tablero de Simplificación.

## Riesgos

- **El techo es el modelo.** Hoy contesta `gemini-3.5-flash-lite`. La verificación descarta
  lo inventado, pero no puede añadir lo que el modelo no vio; para eso está la regla de
  cobertura y la decisión de la persona.
- **Citas literales.** Un modelo ligero parafrasea. Si la tasa de `cita_inventada` resulta
  alta, el ajuste es al prompt, no a la verificación.
- **Cuota.** Una llamada por trámite, a petición. No compite con la Fase 3 salvo que se use
  a la vez.
