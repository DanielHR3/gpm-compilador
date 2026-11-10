# Solicitudes desde Simplifica (campanita)

**Fecha:** 2026-11-10 · **Estado:** aprobado por Daniel en chat («Simplifica avisa»). Es la fase 3 del diseño de
M-108 (bóveda de Simplifica, `06 - Informes y entregables/2026-11-06 - Diseño del módulo de Reingeniería…`).

## Intención

Luis (Reingeniería) decide en Simplifica qué trámite se rediseña. Hoy «iniciar» es descargar una ficha YAML y
pegarla a mano: el Compilador no se entera. Con esto, Luis pulsa **«Enviar al Compilador»** en la ficha del trámite,
el Compilador recibe la ficha y muestra una **campanita** con los trámites enviados; desde ahí el analista descarga
un AS-IS inicial con el frontmatter ya lleno (`ruts_id` incluido), así el expediente nace ligado.

## Contrato

`POST /api/v1/solicitudes` con `Authorization: Bearer <token de envío>` y JSON:

```json
{"ruts_id":"4321","nombre":"…","dependencia":"…","enviado_por":"luis",
 "ruts":{"costo":"…","tiempo_entrega":"…","description":"…"}}
```

- `ruts_id` obligatorio (alfanumérico 1–20, el mismo `RUTS_VALIDO`). `nombre` y `dependencia` obligatorios.
- Textos recortados a 300 caracteres (`description` a 2000); claves desconocidas → 422. Nada del ciudadano.
- Respuesta 201 `{"ok":true}`. Reenviar el mismo `ruts_id` actualiza la ficha y la vuelve a marcar como nueva.

Para la persona (sesión normal):
- `GET /api/v1/solicitudes` → `{"solicitudes":[…], "nuevas": N}` de la más reciente a la más vieja.
- `POST /api/v1/solicitudes/{ruts_id}/vista` → la marca como vista.
- `GET /api/v1/solicitudes/{ruts_id}/as-is` → `Análisis AS-IS.md` inicial con frontmatter (`ruts_id`, `dependencia`)
  y el título `# Análisis AS-IS — <nombre>`, listo para llenarse y subirse.

## Reglas

- **Token de envío aparte** (`GPMC_TOKEN_ENVIO`), distinto del de lectura: el de lectura no escribe y el de envío no
  lee. Sin la variable, la ruta POST no existe (404). Mismo 401 sin pistas. Comparación en tiempo constante.
- El token de envío abre **solo** `POST /api/v1/solicitudes`; una sesión de persona no puede enviar.
- Registro persistente `solicitudes.jsonl` (mismo patrón que `estado.jsonl`: bytes, atómico, tolerante, sobrevive
  a la purga). Una línea por `ruts_id`.
- Auditoría: `servicio:simplifica` · `solicitud.recibir` · `<ruts_id>`.
- Simplifica: botón solo si está configurado `COMPILADOR_TOKEN_ENVIO` (https); 4 s de tope; nunca un 500 por el
  Compilador; bitácora `reingenieria.enviar`; solo quien puede capturar el estado de Reingeniería (Luis y Vinculación).

## Fuera de alcance

Crear la sesión del expediente en el Compilador (los insumos siguen subiéndose a mano), notificaciones por correo.
