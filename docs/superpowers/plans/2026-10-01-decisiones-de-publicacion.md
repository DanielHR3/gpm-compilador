# Tres decisiones de publicación — plan de implementación

> **Para quien lo ejecute:** se implementa tarea por tarea con TDD (la prueba que falla va antes
> del código). Ejecución nativa en una sola sesión, por instrucción de Daniel del 2026-10-01
> («realízalo»).

**Objetivo:** que público, la tarea de cada oficio y el grupo de cada actor se decidan en el
asistente y viajen al `.gpm`.

**Arquitectura:** tres avisos `por_confirmar` (`META-07`, `DOC-04`, `ACT-01`) con control en la
tarjeta; tres tipos nuevos en `POST /api/v1/expedientes/{sid}/resolver` que escriben en el
manifiesto. Nada cambia en `nucleo/huecos.bloquean` ni en el compilador.

**Stack:** Python 3.9+, pydantic, FastAPI, pytest · React + TS, vitest.

**Spec:** `docs/superpowers/specs/2026-10-01-decisiones-de-publicacion-design.md`

## Restricciones globales

- Compatible con Python 3.9: `Optional[X]`, nada de `X | None`.
- Identificadores en español sin acentos; textos al usuario con acentos.
- `nucleo/` no importa de `compilador`, `validador`, `web` ni `cli`.
- Los tres avisos son `por_confirmar`; `bloquean` no se toca.
- No se valida la forma del grupo ni se le pone tope de longitud.
- No se relaja ninguna aserción existente. Si una prueba existente cambia, se lista con motivo.
- `CLAUDE.md` no se modifica: su texto se propone al final para aprobación.
- Línea base: 1004 aprobadas, 24 saltadas (servidor).

## Foco de revisión

1. Un expediente sin TO-BE (flujo lineal) con plantilla sin variables: toda tarea no terminal
   vale; la terminal no.
2. Resolver `doc04` dos veces seguidas: la acción queda en una sola tarea.
3. Resolver `act01` sobre el actor ciudadano: 422, no lo convierte en grupo.
4. `meta07` con valor distinto de `si`/`no` («Sí», vacío): `Sí` con acento y mayúscula se
   acepta; cualquier otro, 422.
5. Flujo con ciclo de corrección (una tarea regresa a otra): `tareas_posibles` termina.

---

### Tarea 1: `tareas_posibles` y `atar_a_tareas`

**Archivos:** `src/gpmc/extractores/documentos.py` · prueba `tests/test_documentos_salida.py`

**Produce:**

```python
def tareas_posibles(accion: Accion, flujo: Flujo, pantallas: "list[Pantalla]") -> "list[tuple[str, list[str]]]"
# (id de tarea, variables que le faltan, ordenadas). Vale si la lista es vacia y la tarea no es terminal.
def vale_para(accion, flujo, pantallas, tarea_id) -> "Optional[str]"
# None si vale; si no, el motivo en castellano.
```

`atar_a_tareas(acciones, flujo, pantallas)` cambia su segundo argumento de `tareas` a `flujo` y
toma la primera tarea que vale; `expediente.py` arma el `Flujo` antes de llamarla.

Pruebas: lineal con dos pantallas (igual que hoy), ramificado (una rama hermana no aporta sus
campos), plantilla sin variables, terminal excluida, ciclo que termina.

### Tarea 2: avisos `META-07` y `ACT-01`

**Archivos:** `src/gpmc/extractores/expediente.py` · prueba `tests/test_extractor_expediente.py`

Tras armar el flujo: un `META-07` (`metadatos`), con `propuesta="Sí, porque lo inicia el ciudadano"`
cuando el actor de la tarea inicial es `autoservicio`; un `ACT-01` por actor `grupo`, con
`ubicacion` = id del actor. Mensajes:

- `META-07`: `el tramite saldra oculto del portal del ciudadano: nada en el expediente dice si es publico`
- `ACT-01`: `las tareas de «{nombre}» se restringen al grupo «{grupo}», que es el nombre del responsable y no un grupo de la plataforma`

### Tarea 3: sugerencias de grupos

**Archivos:** crear `src/gpmc/nucleo/grupos.py` · `src/gpmc/web/api.py` · prueba `tests/test_api.py`

`OBSERVADOS: tuple` con los cuatro de `pendientes.md`. `GET /api/v1/grupos` → `{"grupos": [...]}`.

### Tarea 4: resolver `meta07`, `doc04`, `act01`

**Archivos:** `src/gpmc/web/api.py` · prueba `tests/test_api.py`

`ResolucionIn.tipo` y `_TIPO_A_CODIGO` ganan los tres. Reglas y 422 de la tabla de la spec.
`doc04` usa `vale_para`. Pruebas: cada escritura, cada 422, y el `.gpm` compilado
(`public`/`add_in_menu`, `Eventos` de la tarea, `GruposUsuarios`).

### Tarea 5: el tablero no los cuenta

**Archivos:** `src/gpmc/web/tablero.py` · prueba `tests/test_tablero.py`

`resumir` deja fuera `META-07` y `ACT-01` de `huecos`.

### Tarea 6: pantalla

**Archivos (frontend/src):** `lib/types.ts`, `lib/api.ts`,
`features/huecos/tareasDeDocumento.ts` (nuevo), `controles/ControlSiNo.tsx` (nuevo),
`controles/ControlTarea.tsx` (nuevo), `controles/ControlTexto.tsx`, `TarjetaHueco.tsx`,
`lenguaje.ts`, `observaciones.ts`, con su `*.test.ts(x)`.

```ts
export type TareaCandidata = { id: string; nombre: string; vale: boolean; motivo?: string; actual: boolean };
export function tareasDeDocumento(manifiesto: Record<string, unknown>, accion: string): TareaCandidata[];
export async function leerGrupos(): Promise<string[]>;
```

Los tres controles llevan «Dejarlo así» (`reconocer`).

### Tarea 7: documentación

`planeacion/pendientes.md` (P-17, P-19, PLAT-11), `docs/guias/LEEME - equipo de
Simplificación.md`, estado de la spec. Texto propuesto para `CLAUDE.md`, sin aplicarlo.

### Tarea 8: verificación y entrega

`.venv/bin/pytest -q`, `bash scripts/check-frontend.sh`, revisión del diff, push y
`scripts/desplegar.sh`.
