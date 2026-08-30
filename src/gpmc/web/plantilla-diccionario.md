# Diccionario de Datos

Esta plantilla muestra cómo documentar los campos para que el compilador GPM pueda extraer correctamente la **Etiqueta** (el nombre amigable que verá el ciudadano) y la **Variable** (el identificador técnico interno para el GPM).

El compilador **propone, no adivina**: el nombre técnico que tú declares se respeta tal cual, nunca se sustituye. Hay dos formas de declararlo y las dos funcionan hoy. **No las combines en una misma tabla.**

## Opción 1: Nombre del Campo + `@@variable` en la Descripción (recomendada)

Usa la columna **Nombre del Campo** para el texto que lee el ciudadano y escribe el identificador técnico dentro de la columna **Descripción**, antecedido por `@@`. Con esta forma no se levanta ningún hueco: la etiqueta la escribió una persona y la variable está declarada.

### Pantalla 1 — CIUDADANO — Datos Generales

| Nombre del Campo | Tipo de Dato | Componente Sugerido | Obligatorio | Límite / Especificaciones | Catálogo de Valores | Descripción |
| --- | --- | --- | --- | --- | --- | --- |
| Nombre(s) | Texto | Texto | Sí | 50 caracteres | N/A | Captura del nombre del solicitante. `@@nombres_sol` |
| Primer Apellido | Texto | Texto | Sí | 50 caracteres | N/A | Captura del apellido paterno. `@@paterno_sol` |
| ¿Acepta términos? | Booleano | Checkbox | Sí | N/A | Sí · No | Si el ciudadano acepta los términos de uso. `@@acepta_term` |

## Opción 2: Columna `Variable` sola, sin columna "Nombre del Campo"

Si prefieres una columna exclusiva para el identificador técnico, nómbrala **Variable** y **no incluyas** la columna "Nombre del Campo". El compilador lee el nombre técnico de la columna `Variable` y **deriva** de él una etiqueta legible (por ejemplo `cp_sol` → `Cp sol`).

Esa etiqueta derivada se reporta como hueco **DIC-05** (`por confirmar`): nadie la escribió, la propuso la herramienta, y conviene que una persona la revise antes de compilar. El nombre técnico, en cambio, se toma de la columna `Variable` sin cambios y no genera hueco.

### Pantalla 2 — CIUDADANO — Domicilio

| Variable | Tipo de Dato | Componente Sugerido | Obligatorio | Catálogo de Valores |
| --- | --- | --- | --- | --- |
| `cp_sol` | Numérico | Texto | Sí | N/A |
| `colonia_sol` | Texto | Desplegable | Sí | Centro · Norte · Sur |
| `municipio_sol` | Texto | Desplegable | Sí | Pachuca · Tulancingo |

> **Nota:** Una misma tabla no debe traer las dos columnas a la vez. Si trae `Variable`, no lleva "Nombre del Campo"; si trae "Nombre del Campo", el identificador técnico va en la Descripción con `@@`. Una tabla con ambas columnas no está soportada hoy: el compilador leería solo "Nombre del Campo" e ignoraría `Variable`.
