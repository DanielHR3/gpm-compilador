# Acta — Constancia de Residencia (ejemplo conforme) en el portal (2026-11-17)

**Archivo:** `ejemplos/expedientes/constancia-de-residencia` compilado de `1aa9437`, importado
como **1144** «Constancia de Residencia (prueba compilador)». «Grupo_Test» a mano en Revisión
y Emisión; publicado para la prueba y **despublicado al terminar**. Ciudadana: María
(`mariaptr`) en `tramites.hidalgo.gob.mx`; servidor público: Daniel en `admin.hidalgo.gob.mx`.

## Trámite 24192 — ruta de rechazo y corrección completa

| Qué | Resultado |
|---|---|
| Nombre de 17 letras con `max_length[150]` (antes `exact_length[150]`) | ✅ aceptado |
| Revisión abre con la solicitud en visualización (fila «Vista de solo lectura») | ✅ con el archivo |
| «Motivo del rechazo» con `@@dictamen=='rechazado'` (select, visibilidad) | ✅ aparece con Rechazado, se oculta con Aprobado |
| Conexión `@@dictamen->value == 'rechazado'` | ✅ a Corrección |
| Corrección abre con el dictamen y el motivo en visualización | ✅ |
| Corrección → Revisión (ciclo) | ✅ |
| Conexión `@@dictamen->value == 'aprobado'` | ✅ a Emisión |
| Folio con prefijo del ejemplo | ✅ **«RES-2026-00001»** |
| Etapas | ✅ 5, todas «Completado» |
| Corrección (del ciudadano) | ⚠️ cayó en la bolsa del funcionario (autoservicio) |

## Trámite 24193 — asignación al solicitante

En el 1144 se configuró a mano: Solicitud con «¿Almacenar el identificador del usuario…?» en
`solicitante_id`; Corrección con asignación «Usuario» `@@solicitante_id`.

| Qué | Resultado |
|---|---|
| Usuario actual de Corrección en el seguimiento | ✅ «Maria Guatemberg Hernandez» (antes Daniel) |
| La ciudadana abre y completa Corrección | ✅ «Asignado a: mariaptr», luego Revisión pendiente para el Área |
| Listas del portal ciudadano («Pendientes», «Todos») | ⚠️ no la muestran; se abrió con la liga directa de la etapa. Pregunta para la fábrica |

**Consecuencia (implementado):** la tarea inicial del solicitante guarda su usuario y las demás
tareas del mismo actor se le asignan (`a_gpm._asignacion_del_solicitante`). Wiki: 22 de 28
trámites, 66 tareas. Testamento: Selección de Modalidad y Comprobante de Pago.
