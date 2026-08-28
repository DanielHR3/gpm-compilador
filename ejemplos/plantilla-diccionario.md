# Diccionario de Datos

Esta plantilla muestra cómo documentar los campos para que el compilador GPM pueda extraer correctamente la **Etiqueta** (el nombre amigable que verá el ciudadano) y la **Variable** (el identificador técnico interno para el GPM).

Existen dos formas de hacerlo correctamente:

## Opción 1: Usando la Descripción (Recomendada)

Usa la columna "Nombre del Campo" para lo que lee el ciudadano, y pon el identificador técnico en la columna "Descripción" antecedido por `@@`.

### Pantalla 1 — CIUDADANO — Datos Generales

| Nombre del Campo | Tipo de Dato | Componente Sugerido | Obligatorio | Límite / Especificaciones | Catálogo de Valores | Descripción |
| --- | --- | --- | --- | --- | --- | --- |
| Nombre(s) | Texto | Texto | Sí | 50 caracteres | N/A | Captura del nombre del solicitante. `@@nombres_sol` |
| Primer Apellido | Texto | Texto | Sí | 50 caracteres | N/A | Captura del apellido paterno. `@@paterno_sol` |
| ¿Acepta términos? | Booleano | Checkbox | Sí | N/A | Sí · No | Si el ciudadano acepta los términos de uso. `@@acepta_term` |

## Opción 2: Usando columnas separadas

Si prefieres tener una columna exclusiva para el nombre interno, nombra a la columna `Variable` y asegúrate de incluir también `Nombre del Campo`.

### Pantalla 2 — CIUDADANO — Domicilio

| Nombre del Campo | Variable | Tipo de Dato | Componente Sugerido | Obligatorio | Catálogo de Valores |
| --- | --- | --- | --- | --- | --- |
| Código Postal | `cp_sol` | Numérico | Texto | Sí | N/A |
| Colonia | `colonia_sol` | Texto | Desplegable | Sí | Centro · Norte · Sur |
| Municipio | `municipio_sol` | Texto | Desplegable | Sí | Pachuca · Tulancingo |

> **Nota:** Si usas la Opción 2 y omites la columna "Nombre del Campo", el compilador intentará humanizar automáticamente la variable (ej. `nombres_sol` -> `Nombres sol`).
