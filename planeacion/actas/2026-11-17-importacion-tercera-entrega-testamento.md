# Acta — importación de la tercera entrega de Alta de Avisos de Testamento (2026-11-17)

**Archivo:** `Alta-de-Avisos-de-Testamento (produccion, 2026-11-17).gpm` (compilado de `main`
`e3d6253`). **Dónde:** `modelador.hidalgo.gob.mx/backend/procesos`, cuenta «Capacitación
COEMERE». **Cómo:** «Importar», sin relacionar con otro proceso. Se exportó de vuelta con
`/backend/procesos/exportar/1141` y se comparó con lo enviado.

## Resultado

| Qué | Resultado |
|---|---|
| Importación | **Sin error.** Proceso **1141**, «Alta de Avisos de Testamento (Nuevo)» |
| Conteos en el export | 7 tareas, 41 campos, 8 conexiones (4 con regla), 3 acciones, 3 eventos: **iguales a lo emitido** |
| Regla del paso (`Pasos[].regla`) | **Sobrevive al import**: la tarea «Selección de Modalidad de Pago» trae el paso 2 en `visualizacion` con `@@modalidad_pago=='en_linea'`, idéntica |
| `valor_default` con `@!` | **Sobrevive al import**: `nombre_funcionario_firma = @!nombres @!apellido_paterno @!apellido_materno` |
| Grupos de usuarios | **Se descartan en silencio.** Las 7 tareas salen con `GruposUsuarios: []`. La cuenta solo tiene dos grupos: «grupo práctica» (212) y «Grupo_Test» (213). «Notario» y «Area De Avisos De Testamento» no existen |

## Lo que esto NO prueba

Que el paso se oculte en el runtime cuando la modalidad es «banco» y que la plataforma
sustituya `@!` en el valor por defecto. Eso exige correr el trámite en el portal con un
usuario de cada grupo.

## Consecuencia

Pregunta 7 de la fábrica contestada por la plataforma: los grupos deben crearse (o elegirse
entre los existentes) antes de importar, o asignarse a mano después. Un `.gpm` con grupos
inexistentes importa «bien» pero deja las tareas de funcionario sin grupo.

## Grupos asignados a mano (mismo día)

Por decisión de Daniel, en el modelador (doble clic en cada tarea → Usuarios → «Sólo grupos
de usuarios específicos» → Guardar) se asignó **«Grupo_Test» (213)** a las 7 tareas del 1141.
Miembros del grupo: `danielhernadezr` y `Luis_Vera`. Re-exportado después: las 7 tareas con
`Grupo_Test`, y **nada más cambió** (13 pasos, la regla del paso intacta, 3 eventos, 8
conexiones, el `valor_default` con `@!`). El proceso sigue `public: 0`.

**Pendiente — prueba en el portal** (`tramites.hidalgo.gob.mx`, con `danielhernadezr`):
1. Ruta «En línea»: en «Selección de Modalidad de Pago» aparece el paso «Pago en Línea».
2. Ruta «Banco o transferencia»: NO aparece y el trámite pasa a «Generar y Cargar Formato».
3. «Verificar Notario y Firmar»: «Nombre del Funcionario que Firma» muestra el nombre, no
   el texto `@!nombres …`.

## Prueba en el portal (trámite 24177, mismo día)

Ciudadana (María) en `tramites.hidalgo.gob.mx`; servidor público (Daniel) en `admin.hidalgo.gob.mx`.

| Qué | Resultado |
|---|---|
| Iniciar con las tareas del Notario en grupo | ❌ «Usuario no puede iniciar este proceso». Corregido en el compilador (`25bd5e9`, `ACT-02`): quien inicia sale `publico` |
| Iniciar con las tareas del Notario en `publico` | ✅ Captura llenada y enviada |
| Revisión del Área: captura en `visualizacion` y luego dictamen | ✅ |
| Conexión `@@tiene_observaciones=='no'` (radio) | ✅ Llevó a «Selección de Modalidad de Pago» |
| Asignación de «Selección de Modalidad» (publico, autoservicio) | ⚠️ Queda en la bolsa de pendientes del funcionario, no le llega a la ciudadana. Igual en el export de la fábrica: pregunta para la fábrica |
| Regla de paso `@@modalidad_pago=='en_linea'` sobre `select` | ❌ **El paso no aparece** aunque se guardó «en_linea» |
| Regla de paso `@@modalidad_pago->value == 'en_linea'` | ✅ **El paso «Pago en Línea» aparece** (3 pasos en vez de 2), en visualización |
| «Número de Folio» | ⚠️ Vacío en la captura y en la revisión: la acción de folio no lo llena |

**Consecuencia:** en la regla de un PASO, un `select` exige `->value` (lo que dijo la fábrica en la
pregunta 1). En las conexiones la forma simple sigue funcionando (probado con `radio`).
Pendiente: corregir `nreglas.emitir` para pasos sobre `select`; probar la ruta banco (paso oculto);
recorrer hasta «Verificar Notario y Firmar» para el `@!`; diagnosticar el folio.
