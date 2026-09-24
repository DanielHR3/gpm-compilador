# Dos caminos de entrada y revisión visual de la propuesta — diseño

**Fecha:** 2026-09-24
**Estado:** implementado el 2026-09-24 (plan: `docs/superpowers/plans/2026-09-24-dos-caminos-y-revision-visual.md`)
**Depende de:** Fase 3 (`docs/superpowers/specs/2026-09-23-fase3-propuestas-desde-as-is-design.md`, implementada el 2026-09-24)

## Propósito

Que el equipo de Simplificación elija de forma explícita entre **subir el
expediente completo** (como siempre) y **proponer desde el AS-IS** (Fase 3),
sepa en todo momento en qué camino y paso va, y pueda **decidir sobre la
propuesta viendo el Diccionario como pantallas y el TO-BE como diagrama
grande**, no como Markdown crudo en dos columnas.

## Lo que se decidió y por qué

| Decisión | Alternativa descartada | Motivo |
| --- | --- | --- |
| Inicio con dos tarjetas grandes | Pestañas en la misma pantalla; una sola carga con botón más visible | Elegido por el usuario: la elección es explícita y el camino de la carpeta queda intacto |
| Una pantalla por documento en la propuesta, diagrama a todo lo ancho | Texto y diagrama lado a lado; tarjetas de hoy con «ampliar» | Elegido por el usuario: para decidir hay que ver el diagrama, y lado a lado cada mitad queda angosta |
| Diccionario como vista por pantallas + «Editar texto» | Solo el texto, más grande | Elegido por el usuario: las tablas de 8 columnas no se leen en crudo |
| El diagrama grande también en la revisión de huecos | Solo en el camino del AS-IS | Elegido por el usuario: quien sube la carpeta nunca veía su TO-BE dibujado |
| Sin enrutador nuevo; `App` extiende su lectura de `pathname` + `pushState` | react-router | Cinco pantallas no lo justifican; las ligas `/revisar/{sid}` siguen vivas; sin dependencia nueva |
| El camino («carpeta» / «AS-IS») se deduce en el cliente con `GET /generados` | Campo `origen` en `EstadoExpediente` | Una migaja de UI no debe cambiar el contrato del expediente |
| Migas de máximo tres tramos | «Inicio › Solo AS-IS › Propuesta › TO-BE (2 de 2)» | El tramo «Propuesta» no lleva a ningún lado distinto |
| Sin vuelta a un documento ya decidido | Enlace al Diccionario desde el TO-BE | La decisión no se puede cambiar; un enlace que no hace nada estorba |
| Zoom por CSS sobre el SVG de mermaid; pantalla completa con la API del navegador | Librería de pan/zoom | Sin dependencia nueva; basta para leer un flowchart |
| `GET /capacidades` antes de subir nada | Descubrir «sin licencia» tras subir el AS-IS | Con Gemini en el servidor, esa sería la experiencia de todo el equipo |

## Parte 1 — Rutas, inicio y migas de pan

| Dirección | Pantalla | Migas |
| --- | --- | --- |
| `/` | **Inicio**: dos tarjetas grandes | Inicio |
| `/expediente` | Carga de la carpeta completa (la `CargaInsumos` de hoy, **sin** el botón «Proponer») | Inicio › Expediente completo |
| `/desde-as-is` | Carga solo del AS-IS y adjuntos, con una línea que dice qué va a pasar | Inicio › Solo AS-IS |
| `/revisar/{sid}` en propuesta | Generando / Diccionario / TO-BE | Inicio › Solo AS-IS › Diccionario (1 de 2) *o* TO-BE (2 de 2) |
| `/revisar/{sid}` en revisión | El asistente de huecos de siempre | Inicio › Expediente completo › Revisión *o* Inicio › Solo AS-IS › Revisión |

- **Inicio.** Pregunta «¿Qué tienes del trámite?» y dos tarjetas: «Tengo el
  expediente completo» (AS-IS, TO-BE y Diccionario listos; sube la carpeta) y
  «Solo tengo el AS-IS» (el compilador propone el TO-BE y el Diccionario; tú los
  revisas y decides). Cada una con su botón «Empezar». Debajo, la liga de
  siempre a «Ver expedientes anteriores».
- **Capacidades.** `GET /api/v1/capacidades` → `{"proponer": bool, "motivo":
  str | null}`; `proponer` es `True` solo si hay proveedor y `puede_generar`
  devuelve `None`. Sin licencia, la tarjeta «Solo tengo el AS-IS» sale
  **desactivada con el motivo a la vista**. Si la consulta falla, la tarjeta se
  muestra activa y el error, si lo hay, sale al subir (como hoy).
- **Migas.** Componente `MigasDePan` arriba del contenido, en todas las
  pantallas de proceso; máximo tres tramos; solo los tramos anteriores son
  enlaces; el último es texto. En las pantallas de propuesta solo «Inicio»
  es enlace.
- **Camino.** `App` guarda `camino: "carpeta" | "as_is" | null`. Se fija al
  elegir la tarjeta; al abrir `/revisar/{sid}` directo, se deduce: si
  `GET /generados` contesta 200, es `as_is`; si 404, `carpeta`. Un fallo de
  esa consulta deja las migas en «Inicio › Revisión».
- **Barra lateral.** No cambia; su primer paso («Insumos») lleva a `/`.
- **`CargaInsumos`** pierde el botón «Proponer» y la prop `onPropuesta`. La
  carga del AS-IS es un componente aparte, `CargaAsIs`, con una zona para el
  AS-IS (obligatoria), una para adjuntos, y el botón «Proponer TO-BE y
  Diccionario»; llama `proponerExpediente` y navega a `/revisar/{sid}`.

## Parte 2 — Las pantallas de la propuesta

**Contrato nuevo en `generados.json`.** El `Documento` del Diccionario lleva
`vista`, calculada en `agentes/fase3.py` en la misma extracción que ya produce
los huecos (sin llamada extra al modelo ni al extractor):

```
vista: [ { "id": "p1", "nombre": "Solicitud", "actor": "Ciudadano",
           "campos": [ { "etiqueta": "CURP", "tipo": "text", "obligatorio": true,
                         "opciones": [], "condicion": null | "texto en palabras" } ] } ]
```

Si el extractor no saca pantallas, `vista: []`. El `Documento` del TO-BE no
lleva `vista` (su vista es el diagrama, que se dibuja del texto).

**Diccionario (1 de 2).** Una tarjeta por pantalla («Pantalla 1 · Ciudadano ·
Solicitud»), con sus campos como tarjetas pequeñas: etiqueta, tipo en
palabras («Texto», «Archivo», «Lista», «Fecha», «Párrafo»…), asterisco si es
obligatorio, las opciones si es lista, «visible solo si …» si tiene condición.
Debajo, los pendientes en palabras (`redactarHueco`, como hoy) y los tres
botones de decisión. «Editar texto» cambia a un `textarea` a todo lo ancho con
«Ver como pantallas» para volver; el texto editado se conserva al alternar. Si
`vista` está vacía, se muestra «El compilador no pudo leer pantallas en este
borrador» y se abre el texto directamente. **La vista es la del borrador del
servidor**; mientras se edita se ve el texto, y la extracción real corre al
aceptar.

**TO-BE (2 de 2).** El diagrama ocupa el ancho completo y una altura fija
generosa (70 % del alto de la ventana), con controles de zoom (+, −, ajustar)
por `transform: scale` sobre el SVG y un botón de pantalla completa
(`requestFullscreen` sobre el contenedor; si el navegador no lo permite, el
botón no aparece). Debajo, los pendientes y los botones. «Editar texto» abre
el Markdown en un panel lateral izquierdo y el diagrama se redibuja a la
derecha; «Cerrar» vuelve al diagrama grande. El componente `DiagramaMermaid`
crece con `zoom` y `pantallaCompleta` y se reutiliza tal cual en la Parte 3.

**Generando / error / sin licencia.** Como hoy: la espera con «puedes cerrar y
volver»; en error o sin licencia, el motivo y las dos zonas de carga (aquí sí
en una sola pantalla, porque no hay nada que revisar).

**Orden y decisión.** Se revisa primero el Diccionario; al decidirlo se pasa al
TO-BE. Si el par queda resuelto, el servidor devuelve el expediente y se entra
a la revisión de huecos (como hoy). Un 422 del extractor muestra el motivo y
relee el estado (como hoy).

## Parte 3 — El diagrama en la revisión de huecos

- Tarjeta «Diagrama del TO-BE» arriba de la lista de huecos, **plegada por
  omisión**, con el número de tareas y decisiones en el título (contados del
  manifiesto). Al abrirla, `DiagramaMermaid` con zoom y pantalla completa.
- Si el expediente no trae TO-BE, la tarjeta no aparece.
- Ruta nueva `GET /api/v1/expedientes/{sid}/insumos/to_be` → el texto del TO-BE
  de la sesión como `text/markdown`; 404 si no hay sesión o no hay TO-BE. Solo
  `to_be` por ahora (YAGNI); el nombre de la ruta deja sitio para los otros.

## Fuera de alcance

- Editar el diagrama arrastrando nodos; editar campos del Diccionario en la
  vista por pantallas (se edita el texto).
- Volver a generar bajo demanda.
- Un enrutador de terceros.
- Cambiar el candado o el proveedor del servidor.

## Pruebas

Backend (`tests/test_api.py`, `tests/test_fase3.py`): `capacidades` con y sin
licencia y sin proveedor; `insumos/to_be` con TO-BE, sin TO-BE (404) y con
`sid` inválido (404); `vista` en `generados.json` con las pantallas del
borrador y `[]` con un borrador sin pantallas.

Frontend: Inicio con las dos tarjetas y la del AS-IS desactivada sin
licencia; cada ruta monta su pantalla y sus migas (tres tramos como máximo,
enlaces solo en los anteriores); `App` deduce el camino en `/revisar/{sid}`;
`CargaAsIs` manda el AS-IS y navega; vista por pantallas con dos pantallas y
campos de cada tipo; alternar a texto y volver conserva la edición; `vista`
vacía abre el texto; en el TO-BE existen zoom y pantalla completa y cambian el
estado (jsdom no dibuja); la tarjeta plegable de la revisión no aparece sin
TO-BE y carga el texto al abrirse.

## Orden de entrega

1. Inicio, rutas, migas, `capacidades`, `CargaAsIs` — lo que el equipo usa hoy.
2. Diagrama en la revisión de huecos (`insumos/to_be`, tarjeta plegable,
   zoom y pantalla completa en `DiagramaMermaid`).
3. Las dos pantallas de la propuesta (`vista`, Diccionario por pantallas,
   TO-BE grande).
