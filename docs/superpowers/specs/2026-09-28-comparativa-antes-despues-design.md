# Comparativa «Antes y después» de la reingeniería — diseño

Fecha: 2026-09-28 · Estado: aprobada con la gráfica añadida (2026-09-28) · Solicita: Simplificación Administrativa (DSA)

## Propósito

Simplificación pidió poder **ver el antes y el después de un trámite** para comprobar que
sí tuvo una reingeniería adecuada. Hoy el asistente enseña solo el después (el TO-BE y el
Diccionario); del AS-IS se leen los metadatos y los requisitos, y los pasos del proceso
actual no se leen en ninguna parte.

La comparativa es de **uso interno** del equipo (decisión de Daniel, 2026-09-28). No es un
documento para la dependencia ni sustituye a la aprobación.

Éxito: con un expediente cargado, el analista abre una vista que dice, sin abrir los tres
documentos, qué había, qué quedó, qué se eliminó y qué no se pudo medir; y puede bajarla
como documento.

## Decisiones tomadas

| Pregunta | Decisión |
| --- | --- |
| ¿Quién la lee? | El equipo de Simplificación. Pantalla en la SPA más un documento descargable. |
| ¿De dónde sale lo que no está en el diagrama? | Se declara. En el TO-BE (tabla de métricas) o en la propia pantalla, en tarjetas. |
| ¿Bloquea la entrega del `.gpm`? | No. Todos los huecos de la comparativa son `por_confirmar`. |
| ¿Interviene un modelo de IA? | No. La medida es determinista. |

## Lo que traen los expedientes reales

Medido sobre los seis expedientes de «EXPEDIENTES DE TRAMITES CON REINGENIERIA»:

- **AS-IS.** Sección «Estado actual» con viñetas en negrita: `Canal`, `Pasos / ventanillas`,
  `Tiempo estimado` o `Tiempo de respuesta`, `Requisitos`, `Costo`, `Sistemas involucrados`.
  Los pasos vienen de dos formas: lista numerada anidada (Avisos de Testamento, 19 pasos) o
  en la misma línea separados por `→` (Constancia de No Infracción, 7 etapas). Sección
  «Fricciones identificadas», numerada o en viñetas.
- **TO-BE.** «Cambios concretos frente al AS-IS» (lista numerada), «Principio aplicado:
  eliminar, no solo digitalizar» (viñetas de lo eliminado) e «Impacto estimado», que el
  propio equipo marca como **cualitativo, no medido**.
- **El AS-IS no trae diagrama en Markdown** (viene en PDF). El «antes» es una lista de
  pasos, no un flujo dibujado.
- Periódico Oficial homologa tres trámites y no sigue la forma: debe degradar con huecos,
  no reventar.

## Qué se compara

### 1. Cuadro de métricas

Una fila por métrica, con antes, después, diferencia y **origen** de cada valor.

| Métrica | Antes | Después |
| --- | --- | --- |
| Requisitos documentales | contado: lista «Requisitos» del AS-IS | contado: campos `file` del manifiesto, sin las filas de solo lectura (la misma cuenta del tablero) |
| Pasos del proceso | contado: pasos del AS-IS | contado: tareas del manifiesto |
| Actores que intervienen | declarado o sin dato | contado: actores distintos de las tareas |
| Sistemas externos | contado: «Sistemas involucrados» | declarado o sin dato |
| Tiempo de respuesta | leído: el texto del AS-IS | declarado o sin dato |
| Visitas presenciales | declarado o sin dato | declarado o sin dato |
| Capturas manuales del mismo dato | declarado o sin dato | declarado; se informa aparte cuántos campos se autollenan por `api_ajax` |

Orígenes posibles: `contado`, `leido`, `declarado`, `sin_dato`. La diferencia y el
porcentaje solo se calculan cuando los dos lados son números. «13 días hábiles» contra
«24 horas» se enseña tal cual, sin convertir unidades: convertir sería inferir.

### 2. Requisitos, uno por uno

Cada requisito del AS-IS con su destino: **conservado** (casa con la etiqueta de un campo
`file`, con la misma regla de `GEN-01`), **sin destino** (no casa con ninguno) o **nuevo**
(campo `file` que no estaba en el AS-IS). «Sin destino» no se rotula «eliminado»: el
compilador no sabe si se eliminó o se olvidó. Si el TO-BE lo nombra en la lista bajo
«Principio aplicado: eliminar», se rotula «eliminado» y se cita la línea como fundamento. No
se buscan eliminaciones en los «Cambios concretos»: la revisión de la rama mostró que así se
listaba como eliminado lo que se había añadido.

### 3. Pasos de antes y tareas de después

Dos columnas de tarjetas: los pasos del AS-IS en su orden, y las tareas del manifiesto con
su actor. No se emparejan paso a paso: no hay dato que lo sostenga.

### 4. Lo que el equipo escribió

Tal cual, sin reescribir: fricciones del AS-IS; cambios concretos, eliminaciones e impacto
estimado del TO-BE. El impacto lleva la advertencia del propio equipo de que es cualitativo.

### 5. Veredicto

Una frase determinista, armada con las cuentas, y una de tres señales:

Se mira toda métrica con número en los dos lados:

- **Reduce:** alguna baja y ninguna sube.
- **Mixto:** unas bajan y otras suben.
- **No reduce:** ninguna baja. Sale `CMP-03`.

Con menos de dos métricas comparables el veredicto es «no se puede medir» y dice qué falta.

### 6. Gráfica del porcentaje de simplificación

Pedida por Daniel el 2026-09-28.

- **Por métrica:** `(antes − después) / antes × 100`, solo cuando los dos lados son números
  y el antes es mayor que cero. Una métrica que sube da porcentaje negativo y se enseña
  así, no se esconde.
- **Global:** el promedio simple de los porcentajes de las métricas comparables. Va siempre
  con su base a la vista: «47 % sobre 3 de 7 métricas». Con menos de dos métricas
  comparables no hay cifra global: se dice qué falta declarar.
- **Regla de unidades:** dos valores se comparan solo si traen número y la **misma unidad**
  («13 días hábiles» contra «3 días hábiles»). «13 días hábiles» contra «24 horas» no
  entra: convertir sería inferir.
- **Forma:** barras horizontales emparejadas, antes y después, una pareja por métrica
  comparable, con su porcentaje al lado; y la cifra global arriba como indicador. SVG y
  CSS propios, como el tablero, sin librería. Colores de la rampa `--viz-*`, validados en
  claro y oscuro con la guía `dataviz`. Cada barra lleva su valor en texto: el color no es
  el único portador del dato.
- **En el documento descargable** la misma gráfica va como SVG incrustado.
- El cálculo vive en `comparativa/armar.py`; la SPA solo pinta lo que recibe.

## Métricas declaradas

Dos caminos para el mismo dato; **gana lo capturado en la pantalla**, porque es lo último
que decidió una persona.

1. **En el TO-BE**, sección opcional que se añade a `web/plantilla-tobe.md`:

   ```markdown
   ## Métricas del rediseño

   | Métrica | Antes | Después |
   | --- | --- | --- |
   | Tiempo de respuesta | 13 días hábiles | 3 días hábiles |
   | Visitas presenciales | 2 | 0 |
   ```

2. **En la pantalla**, una tarjeta por métrica sin dato, con su campo de captura. Se guarda
   en `comparativa.json` dentro de la sesión, con la fecha. El quién ya lo registra la
   auditoría del servidor. No toca el manifiesto.

Lo declarado también **corrige una cuenta**: si el extractor leyó mal los pasos de un
AS-IS con forma rara, la persona escribe la cifra y queda rotulada «declarado».

## Huecos `CMP-*` (todos `por_confirmar`, ninguno bloquea)

| Código | Cuándo | Va a |
| --- | --- | --- |
| `CMP-01` | El AS-IS no trae pasos legibles | AS-IS |
| `CMP-02` | Una métrica no tiene dato del después. Un solo hueco que las nombra todas | TO-BE |
| `CMP-03` | La reingeniería no reduce requisitos ni pasos | TO-BE |
| `CMP-04` | Requisitos del AS-IS sin destino. Un solo hueco que los nombra | TO-BE |

Viven **solo en la comparativa**: no entran a la lista del wizard ni a la puerta del
linter, para no engordar la cuenta de pendientes de un expediente que ya compila.

**Sí van en las observaciones** que se le mandan a Simplificación (decisión de Daniel,
2026-09-28), en una sección propia «Sobre la comparativa de antes y después».

## Arquitectura

Dependencia en un solo sentido, como el resto: `web` → `comparativa` → `extractores` →
`nucleo`. Nada de esto importa de `agentes`.

| Pieza | Responsabilidad |
| --- | --- |
| `extractores/as_is.py` (nuevo) | `extraer(texto) -> EstadoActual`: canal, pasos, requisitos, tiempo, costo, sistemas, fricciones. Tolerante: lo que no se lee queda vacío. |
| `extractores/rediseno.py` (nuevo) | Del texto del TO-BE: cambios, eliminaciones, impacto y métricas declaradas. |
| `comparativa/armar.py` (nuevo) | `comparar(estado_actual, rediseno, manifiesto, declaradas) -> Comparativa`. Función pura. |
| `comparativa/documento.py` (nuevo) | `Comparativa` → HTML estático, autocontenido e imprimible. Todo dato pasa por escapado. |
| `web/api_comparativa.py` (nuevo) | `GET /api/v1/expedientes/{sid}/comparativa`, `POST …/comparativa/declarar`, `GET …/comparativa/documento` (con `Content-Disposition`). |
| `frontend/src/features/comparativa/` (nuevo) | Vista en tarjetas; `veredicto.ts` aparte del componente. |

**Reacomodo necesario:** `requisitos_del_as_is` y `_casa` viven hoy en
`agentes/verificar_fase3.py`. Se mudan a `extractores/as_is.py` y `agentes` los importa de
ahí. Sin cambio de comportamiento; las pruebas de `GEN-01` lo fijan.

**Sin AS-IS en la sesión** (expediente cargado solo con Diccionario y TO-BE): la API
responde `200` con `disponible: false` y el motivo; la pantalla lo dice y no pinta ceros.

## Pantalla

- Se entra desde el riel de entrega («Ver antes y después») y por la ruta
  `/revisar/{sid}/comparativa`, que basta para reconstruir la vista.
- **Solo tarjetas**, regla de la SPA: una `Card` por métrica, por requisito, por paso y por
  tarea. Ninguna `<table>`.
- Cada valor enseña su origen con una etiqueta: «contado», «declarado», «sin dato».
- Colores de la rampa `--viz-*` y tokens del sistema de diseño; claro y oscuro.
- La descarga sale en la propia vista, **nunca bloqueada**. No va en el panel de descargas:
  ese panel enseña una vista previa en texto y el documento es una página.

## Pruebas

- `tests/test_as_is.py`: pasos en lista anidada y en línea con `→`; requisitos; tiempo;
  sistemas; fricciones; AS-IS sin forma devuelve vacío sin excepción.
- `tests/test_rediseno.py`: tabla de métricas declaradas; cambios; eliminaciones.
- `tests/test_comparativa.py`: porcentaje por métrica y global con su base, métrica que
  sube, menos de dos comparables; orígenes; diferencia solo entre números; tres veredictos;
  cada `CMP-*`; la pantalla gana sobre el TO-BE; requisito «sin destino» contra «eliminado».
- `tests/test_comparativa_documento.py`: escapado de `<script>` en un requisito.
- API: sin AS-IS, con AS-IS, declarar y releer.
- Con material real (`GPMC_WIKI`): los seis expedientes arman comparativa sin excepción;
  se saltan si no está disponible.
- Frontend: `veredicto.test.ts`, vista por `article`/`aria-label`, captura de una métrica.

## Fuera de alcance

- Orden nueva en la CLI. Las funciones quedan listas para añadirla.
- Documento para la dependencia y bloque de autorización.
- Emparejar cada paso del AS-IS con una tarea del TO-BE.
- Leer el diagrama del AS-IS desde el PDF.
- Agregados de la comparativa en el tablero.
- Conversión de unidades de tiempo.
- Cualquier redacción hecha por un modelo.

## Supuestos

Confirmados por Daniel el 2026-09-28:

1. «En cards»: la vista entera en tarjetas **y** la captura de métricas faltantes en
   tarjetas dentro de la pantalla.
2. El documento descargable es HTML imprimible a PDF desde el navegador, sin librería nueva.

3. Los huecos `CMP-*` no aparecen en el wizard, y **sí** en las observaciones.
4. `CLAUDE.md` se actualiza y la entrega se despliega a AWS dentro de este plan.
