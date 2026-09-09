# Diccionario de Datos — plantilla de ejemplo

Copia este archivo, cambia el nombre del trámite y reemplaza las filas por los
campos de **tu** trámite. Es un ejemplo completo de **Constancia de Residencia**.

## Cómo se llena

- Una fila por campo.
- **Nombre del Campo**: el texto que lee el ciudadano ("Nombre completo").
- **Descripción**: qué es el campo, y al final su nombre técnico entre acentos
  graves con `@@` delante: `` `@@nombre_completo` ``. Máximo 30 caracteres, solo
  minúsculas, números y `_`, sin repetir.
- **Catálogo de Valores**: solo para listas desplegables. Las opciones separadas
  por ` · ` (espacio, punto medio, espacio): `Aprobado · Rechazado`. Para Sí/No,
  pon el tipo `Booleano` y déjalo vacío.
- **Condición de Visibilidad**: si el campo solo aparece bajo condición,
  escríbela así: `Visible solo si "Dictamen" = Rechazado`. Si no, déjala en blanco.

## Sección 1 — Pantallas

### Pantalla 1 — CIUDADANO — Solicitud

| Nombre del Campo | Tipo de Dato | Componente Sugerido | Obligatorio | Condición de Visibilidad | Límite / Especificaciones | Catálogo de Valores | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CURP | Texto | Campo de texto | Sí | | 18 caracteres | N/A | CURP del solicitante. `@@curp` |
| Nombre completo | Texto | Campo de texto | Sí | | 150 caracteres | N/A | Nombre y apellidos del solicitante. `@@nombre_completo` |
| Domicilio | Texto | Área de texto | Sí | | 250 caracteres | N/A | Calle, número, colonia y municipio. `@@domicilio` |
| Comprobante de domicilio | Archivo | Carga de archivo | Sí | | PDF · máx. 5 MB | N/A | Recibo de luz, agua o predial. `@@doc_comprobante` |

### Pantalla 2 — FUNCIONARIO — Revisión

| Nombre del Campo | Tipo de Dato | Componente Sugerido | Obligatorio | Condición de Visibilidad | Límite / Especificaciones | Catálogo de Valores | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dictamen | Lista desplegable | Lista desplegable | Sí | | Valores definidos | Aprobado · Rechazado | Resultado de la revisión. `@@dictamen` |
| Motivo del rechazo | Texto | Área de texto | Condicional | Visible y obligatorio solo si "Dictamen" = Rechazado | 300 caracteres | N/A | Qué debe corregir el ciudadano. `@@motivo_rechazo` |
