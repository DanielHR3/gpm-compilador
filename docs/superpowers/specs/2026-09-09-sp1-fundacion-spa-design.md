# Diseño — SP1: Fundación de la SPA (React + FastAPI, un solo origen)

**Fecha:** 2026-09-09
**Estado:** diseño aprobado, pendiente de plan de implementación
**Contexto:** `Mejora de UX y Frontend - NextJS y Shadcn.md` y `Hallazgos_UX_y_Mejoras_Pendientes.md` del vault. Los 6 hotfixes de escritorio ya están en `main` (commit `90f5191`); esto es el paso arquitectónico que sigue.

---

## 1. Contexto y objetivo

El asistente web actual renderiza HTML desde f-strings de Python (`web/plantillas.py`, `simulador/html.py`). Se decidió (2026-09-09) modernizar la capa de presentación a una **SPA React** servida por FastAPI, manteniendo el núcleo intacto. La aplicación pasa a ser **cliente-servidor** y se despliega en servidores con pipeline (no más laptop + `.command`), por lo que tener Node en el *build* deja de ser una carga: el runtime sigue sin necesitar Node.

El trabajo completo se descompuso en tres sub-proyectos, cada uno con su propio spec → plan → implementación:

| | Sub-proyecto | Entrega |
|---|---|---|
| **SP1** *(este spec)* | Fundación SPA | Scaffold Vite+React+Tailwind+shadcn; `/api/v1/*`; FastAPI monta `dist/`; el build entra al despliegue; se migran a React la carga de insumos y el wizard de huecos. Las rutas HTML restantes siguen vivas. |
| **SP2** | Resolución avanzada (#7 "cero clics post-importación") | Constructores visuales de reglas (`MMD-04`, `DIC-08`), editor de flujo (`FLU-01`), editor de `apis.yaml` (`API-05`), y las extensiones de modelo/compilador que cada uno requiere. **Decisión diferida a SP2:** si se reabre la emisión de Acciones PHP para `API-05`. |
| **SP3** | Simulador + Aprobación en React | Reemplazan `simulador/html.py` y la generación HTML de `compilador/aprobacion.py`; se borran `web/plantillas.py` y `simulador/html.py`. |

**Objetivo de SP1:** que exista la plataforma (SPA + API REST + integración de build) y que las dos pantallas de mayor uso —carga de insumos y resolución de huecos— corran en React con paridad funcional, sin big-bang y sin que la suite de Python baje de verde en ningún paso.

## 2. Alcance

### En alcance

- `src/gpmc/web/api.py`: `APIRouter` montado en `/api/v1`, solo JSON.
- Modelo Pydantic espejo de `Hueco` para serialización/validación por FastAPI.
- `frontend/`: proyecto Vite + React + TypeScript + Tailwind + `shadcn/ui`.
- FastAPI sirve `frontend/dist/` como estáticos, con *fallback* SPA a `index.html`.
- Pantalla de **carga de insumos** en React (drag-drop real, validación de tamaño).
- **Wizard de resolución de huecos** en React (una tarjeta por hueco, `Progress`, controles de `MMD-03`/`META-01`/`META-02`/`API-03`, "lo configuro a mano" sin recarga).
- Integración del build en `despliegue/` y en el `.command` local.
- CI: `tsc --noEmit`, `vite build`, `vitest run`, además de `pytest`.

### Fuera de alcance (SP2/SP3)

- Constructores visuales de reglas, editor de flujo React Flow, `apis.yaml` desde la web.
- Simulador y Aprobación en React.
- Borrado de `web/plantillas.py` y `simulador/html.py` (quedan muertos tras el corte de SP1; los borra SP3).
- Emisión de Acciones PHP (decisión de alcance para SP2).
- Playwright / E2E con navegador (opcional, posterior).

## 3. Arquitectura

### Layout del repo

```
frontend/                     proyecto Vite
  package.json
  vite.config.ts              proxy /api -> :8000 en dev
  tsconfig.json
  index.html
  src/
    main.tsx
    api/                       cliente tipado de /api/v1
    components/ui/             componentes shadcn (código propio)
    features/
      carga/                   pantalla de carga de insumos
      huecos/                  wizard de resolución
    lib/
  dist/                        build (NO se comitea; lo excluye .gitignore)

src/gpmc/web/
  app.py                      monta StaticFiles(dist) + include_router(api) + rutas HTML restantes
  api.py         ← nuevo      APIRouter("/api/v1"), sin HTML
  plantillas.py               vivo hasta SP3
  ...
```

### Estrategia de rutas (convivencia durante SP1)

| Ruta | Quién la sirve | Cambia en SP1 |
|---|---|---|
| `/`, `/revisar/*` | **SPA React** (ruteo en cliente; datos de `/api/v1`) | Sí — se quitan los handlers HTML `portada` y `revisar` |
| `/api/v1/*` | `api.py` — JSON | Nuevo |
| `/simulador/{sid}`, `/aprobacion/{sid}`, `/historial`, `/vistas/{sid}`, `/descargar-plantilla` | HTML actual | No — la SPA enlaza a ellas |
| `/descargar/{sid}/{que}` | igual que hoy | No (la SPA puede seguir usándolas, o su equivalente en `/api/v1`) |

El *fallback* SPA: cualquier `GET` que no case con la API ni con un archivo real de `dist/` ni con una ruta HTML explícita devuelve `dist/index.html` con `200`, para que el ruteo de cliente de React funcione al recargar en `/revisar/<sid>`.

### Serialización

- `Manifiesto` ya es Pydantic v2 — FastAPI lo emite directo.
- `Hueco` es `dataclass`. Se añade `HuecoOut` (Pydantic) con los mismos campos (`nivel`, `codigo`, `ubicacion`, `mensaje`, `propuesta`) y un helper `HuecoOut.model_validate(hueco, from_attributes=True)`. `/revisar` ya serializaba huecos a mano; esto lo formaliza.
- `bloquean()`, `_purgar_sesiones()`, el gate del linter, `_reconocidos()`, `_huecos_vivos()` — se reutilizan tal cual desde `api.py` (se factorizan a funciones de módulo si hoy están anidadas en `crear_app`).

## 4. Superficie REST `/api/v1`

| Método · Ruta | Cuerpo | Devuelve | Errores |
|---|---|---|---|
| `POST /api/v1/expedientes` | multipart: `as_is?`, `to_be?`, `diccionario`, `vistas?` | `201 { sid, manifiesto, huecos[], estimacion, problemas[], tiene_vistas }` | `413 { error, archivos[] }` (archivo > `_MAX_SUBIDA`); `422 { error }` (sin manifiesto, permiso denegado con el texto de `SinPermiso`) |
| `GET /api/v1/expedientes/{sid}` | — | `200 { sid, manifiesto, huecos[], estimacion, problemas[], tiene_vistas }` | `404 { error: "sesión no encontrada" }` (sid inválido o purgado) |
| `POST /api/v1/expedientes/{sid}/resolver` | `{ resoluciones: [{ tipo, ubicacion, valor }] }` — `tipo` ∈ `mmd03`/`meta01`/`meta02`/`api03` | `200 { manifiesto, huecos[] }` | `404` |
| `POST /api/v1/expedientes/{sid}/reconocer` | `{ codigo, ubicacion }` | `200 { huecos[], reconocidos[] }` | `404` |
| `GET /api/v1/expedientes/{sid}/gpm?modo=produccion\|pruebas` | — | `200` `application/octet-stream` con `Content-Disposition` | `409 { bloqueantes: [{ codigo, ubicacion, mensaje }] }`; `404` |
| `GET /api/v1/expedientes/{sid}/manifiesto` | — | `200` YAML `text/yaml` | `404` |

Notas:

- Los códigos siguen el catálogo de huecos existente; el linter no cambia.
- `resolver` aplica cada `resolución` como hoy hace `POST /resolver` (actualiza `manifiesto.yaml`, limpia `huecos.json`), y devuelve el estado nuevo completo — React reemplaza su copia, sin merge.
- `reconocer` escribe en `reconocidos.json` (ya existe).
- El gate del linter (`bloquean(huecos_vivos, reconocidos)`) se aplica en `GET .../gpm` igual que en la ruta HTML actual.
- CORS: no se habilita nada — la SPA y la API comparten origen. Se conservan las cabeceras `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` del middleware actual.

## 5. Modelo de sesión

Se **mantiene** la carpeta de sesión en disco (`.md` subidos + `manifiesto.yaml` + `huecos.json` + `reconocidos.json`) con la purga TTL de 7 días (`_purgar_sesiones`, ya implementada).

Razón: el extractor necesita los `.md` en disco; el manifiesto debe sobrevivir un *reload* del navegador y poder descargarse. React guarda una **copia en memoria** para que la UI sea instantánea, pero **el servidor es la fuente de verdad**: cada `resolver`/`reconocer` devuelve el estado nuevo y React lo reemplaza.

Esto **matiza** el doc de referencia, que proponía "todo en memoria de React, sin carpetas". No es viable sin re-subir archivos en cada compilación o cargarlos como base64 en el navegador; la copia-en-cliente + verdad-en-servidor da la misma sensación de SPA sin ese costo.

## 6. Build, despliegue y desarrollo

### Stack del frontend

Vite + React + TypeScript + Tailwind + `shadcn/ui` (preset de Vite de su CLI; los componentes se copian al repo bajo `frontend/src/components/ui/`, sin dependencia de runtime). Componentes iniciales: `button`, `card`, `input`, `select`, `progress`, `tabs`, `dialog`, `sonner`.

### Sistema de diseño — `hidalgo-design-token-system`

**Requisito:** el diseño y los colores del frontend salen del paquete
`hidalgo-design-token-system@latest`, no de valores elegidos a mano ni de la
guinda muestreada del HTML actual. Se instala como dependencia
(`npm i hidalgo-design-token-system@latest`) y sus tokens (colores, radios,
tipografía, espaciado) se cablean al `tailwind.config` y/o al CSS global, de modo
que los componentes de `shadcn/ui` los consuman por variables CSS.

**A confirmar en el primer paso del plan** (antes de construir cualquier
componente): (1) el registro — npm público o privado con `.npmrc`; (2) qué
exporta — variables CSS, un preset de Tailwind, JSON de tokens, o una hoja de
estilos; (3) si trae modo claro/oscuro. La forma de la integración
(`tailwind.config` preset vs `@import` de CSS vars) depende de eso.

**Fallback:** si el paquete no está disponible o su forma bloquea, se arranca con
la paleta guinda actual (`#5e132c`/`#66132a`) como variables CSS con los mismos
nombres que espera `shadcn`, y se cambia al paquete después sin tocar componentes.

### Build

```
cd frontend && npm ci && npm run build   # -> frontend/dist/
```

Node/npm **solo en build** (CI o la máquina de despliegue). `frontend/dist/` **no se comitea** (`.gitignore`).

### Cómo lo encuentra FastAPI

Variable `GPMC_FRONTEND_DIST` (por defecto `<repo>/frontend/dist`). Si la carpeta no existe o no tiene `index.html`, `/` responde `503` con un cuerpo claro: *"El frontend no está compilado. Corre `cd frontend && npm ci && npm run build`."* — no un 404 críptico.

### Despliegue

`despliegue/instalar-servicio.sh` y `despliegue/LEEME.md` ganan el paso `npm ci && npm run build` antes de arrancar FastAPI. `Abrir Compilador GPM.command` (uso local): si hay `node`, construye; si no, sirve el último `dist/` con un aviso en consola.

### Desarrollo

- `cd frontend && npm run dev` — Vite en `:5173`, proxy `/api` → FastAPI `:8000`.
- `gpmc servir` — FastAPI en `:8000`.
- Documentado en `frontend/README.md` y en `CLAUDE.md`.

### CI

Se añade al pipeline: `tsc --noEmit`, `vite build`, `vitest run`. `pytest` sigue siendo obligatorio y la suite de Python nunca baja de verde.

## 7. Orden de migración

Cada paso deja la suite verde y la app usable.

1. **`api.py` con `/api/v1`** + `HuecoOut`. Pruebas `pytest`/`TestClient` de cada endpoint: formas JSON, gate del linter (`409`), ida-y-vuelta de `resolver`/`reconocer`, `413` de archivo grande, `404` de sesión inexistente. **El HTML viejo intacto.**
2. **Scaffold `frontend/`** (Vite+React+TS+Tailwind+shadcn). **Primero:** verificar e integrar `hidalgo-design-token-system@latest` (registro, exports, claro/oscuro) — sus tokens al `tailwind.config`/CSS global antes de construir cualquier componente; si no está disponible, el fallback de la §6. Montado temporalmente en `/app` para verificar el build y el *fallback*.
3. **Pantalla de carga de insumos en React** — drag-drop que asigna `input.files`, validación de tamaño con el mensaje del backend, contra `POST /api/v1/expedientes`. Tests `vitest`.
4. **Wizard de resolución de huecos en React** — una `Card` por hueco, estado en React, `Progress`, los cuatro controles interactivos y el "lo configuro a mano" (por diseño de SPA ya no recarga ni pierde lo capturado). Paridad funcional con `/revisar`. Tests `vitest`.
5. **Corte:** la SPA toma `/` y `/revisar/*`; se eliminan de `app.py` los handlers `portada` y `revisar`. `plantillas.portada`/`revision` quedan sin usar (los borra SP3). `/simulador`, `/aprobacion`, `/historial`, `/vistas`, `/descargar-plantilla` siguen en HTML; la SPA enlaza a ellas.

## 8. Pruebas

- **Backend (`pytest`):** obligatorio. Cada endpoint de `/api/v1` con `TestClient`. La suite completa de Python nunca baja de verde — las rutas HTML que se quedan conservan sus pruebas hasta SP3.
- **Frontend (`vitest` + React Testing Library):** obligatorio para componentes — carga de insumos (drop asigna archivo, error de tamaño se muestra), wizard (render de una tarjeta por hueco, el submit manda el `resolver` correcto, "lo configuro a mano" oculta sin navegar).
- **Type/bundle:** `tsc --noEmit` + `vite build` en CI (equivalente al `node --check` que ya se usa para el HTML embebido).
- **E2E (Playwright):** un smoke opcional (subir → resolver → descargar). **No bloquea SP1** — agrega navegador a CI y se decide aparte.

## 9. Riesgos y mitigación

| Riesgo | Mitigación concreta |
|---|---|
| El corte de `/` rompe enlaces guardados a `/revisar/{sid}` | La SPA rutea `/revisar/:sid` en cliente y hace `GET /api/v1/expedientes/{sid}` al montar. Si el `sid` no existe (purgado o inválido) → pantalla "La sesión expiró; vuelve a subir los insumos" con botón a `/`. Nunca un 404 en blanco. |
| `shadcn/ui` asume Next en varios ejemplos | Se usa el preset de Vite de su CLI. Los componentes son código propio en `frontend/src/components/ui/`, no una dependencia. En el paso 2 se agrega **un** componente (`button`) y se confirma que compila antes de seguir. |
| `hidalgo-design-token-system@latest` de forma o registro desconocido | El paso 2 lo verifica **antes** de construir componentes: registro (`npm view` / `.npmrc`), qué exporta (CSS vars / preset Tailwind / JSON), modo claro-oscuro. Si no está disponible → fallback documentado (paleta guinda actual como CSS vars con los nombres que espera shadcn) y se cambia después sin tocar componentes. |
| `frontend/dist/` sin construir en un servidor nuevo | FastAPI detecta la ausencia y responde `503` con la instrucción exacta. `instalar-servicio.sh` incluye `npm ci && npm run build`. `frontend/README.md` lo documenta. |
| Doble fuente de verdad (React vs disco) | El servidor manda. Cada `resolver`/`reconocer` devuelve el estado nuevo **completo**; React lo **reemplaza**, sin merge en cliente. No hay escritura optimista que reconciliar. |
| Regresión en las pantallas HTML que se quedan | No se tocan hasta SP3. Sus pruebas actuales (`test_web.py`) siguen corriendo en cada paso. El paso 5 solo **elimina** los dos handlers migrados; el resto de `app.py` no cambia. |
| El proxy de Vite en dev enmascara un problema de CSP/estáticos que solo aparece en `dist/` | El paso 2 monta el `dist/` real en `/app` y una prueba `pytest` verifica que `GET /app` devuelve `index.html` con la CSP `default-src 'self'` y que un asset de `dist/assets/` se sirve. No se depende solo de `npm run dev`. |
| `vite build` o `tsc` se rompen y nadie lo nota hasta el despliegue | Están en CI como pasos que fallan el pipeline, junto a `pytest`. |
| Crecimiento de alcance dentro de SP1 (alguien mete un constructor de reglas "ya que estamos") | El spec fija los cinco pasos. Cualquier cosa de la lista "Fuera de alcance" para y va a SP2/SP3 con su propio spec. |

## 10. Decisiones diferidas

- **Emisión de Acciones PHP** (`API-05`, doc #7): se decide en el spec de SP2, no aquí. Hoy `API-05` sigue siendo "hueco → PHP a mano".
- **Borrado de `web/plantillas.py` y `simulador/html.py`:** ocurre en SP3, cuando React tenga paridad de simulador y aprobación. En SP1 solo quedan sin uso los dos handlers migrados.
