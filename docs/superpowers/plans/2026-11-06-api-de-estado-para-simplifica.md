# API de estado para Simplifica Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `GET /api/v1/expedientes?ruts_id=…` responde el estado del expediente con el contrato que Sistema-3.0 ya espera, protegido por un token de servicio.

**Architecture:** El extractor lee `ruts_id` del frontmatter del AS-IS y lo guarda en el manifiesto. Un registro persistente `estado.jsonl` (una línea por `ruts_id`, fuera del alcance de la purga, mismo patrón que `tablero.jsonl`) anota la primera fecha de cada entregable al extraer y al descargar el `.gpm` que pasó la puerta. Un router nuevo lee ese registro; el middleware de sesión deja pasar solo esa ruta y el manejador valida su propio token.

**Tech Stack:** Python 3.9 (`Optional[X]`, sin `X | None`), FastAPI, pytest, `hmac.compare_digest`.

**Spec:** `docs/superpowers/specs/2026-11-06-api-de-estado-para-simplifica-design.md`

## Global Constraints

- Python 3.9: nada de `X | None`; identificadores en español sin acentos; comentarios explican *por qué*.
- Token de servicio en la variable de entorno `GPMC_TOKEN_SERVICIO`, comparado en tiempo constante; sin la variable la ruta responde 404.
- Sirve únicamente para esta ruta. Nunca en la URL. Sin datos del ciudadano en la respuesta.
- Siete claves siempre en `entregables`: `as-is`, `to-be`, `diccionario`, `bpmn`, `gpm`, `aprobacion`, `publicado`, con `AAAA-MM-DD` o `null`.
- `bpmn`, `aprobacion` y `publicado` salen `null` en esta entrega; `analista` es `""`.
- `gpm` solo se anota si la descarga de producción pasó la puerta del linter (respuesta 200).
- Emparejado solo por `ruts_id` exacto, texto alfanumérico de 1 a 20 caracteres. Sin emparejado por nombre.
- Fechas en `America/Mexico_City`; la primera fecha en que aparece el entregable no se reescribe.
- Auditoría de servicio como `servicio:simplifica`, solo si hay almacén de usuarios.
- Nada de `agentes/`, `compilador/` ni `nucleo/` importa de `web`. No se modifica `CLAUDE.md` ni se relaja ninguna aserción existente.

## Review Focus

- Dos `ruts_id` parecidos (`4321` y `43210`, o mayúsculas distintas): no se mezclan líneas.
- `ruts_id` con inyección (`4321&x=1`, `../`, espacios, vacío, más de 20 caracteres): 422, nunca llega al registro.
- Token de una persona (JWT de sesión) en la cabecera: 401, no abre la ruta.
- `Authorization` sin esquema `Bearer`, o token vacío: 401.
- Registro corrupto, con una línea rota o inexistente: la respuesta es `{"expedientes":[]}` o ignora la línea; nunca un 500.
- Re-extraer el mismo expediente al día siguiente no cambia la fecha del `as-is`.
- La purga de sesiones no borra `estado.jsonl`.
- Un expediente sin `ruts_id` en el frontmatter sigue extrayéndose igual y suma solo el hueco `META-RUTS` (`por_confirmar`).
- Dos consultas simultáneas con escrituras del extractor no dejan el archivo a medias.

---

### Task 1: `ruts_id` en el manifiesto y en el extractor

**Files:**
- Modify: `src/gpmc/nucleo/manifiesto.py:30-36` (modelo `Tramite`)
- Modify: `src/gpmc/extractores/metadatos.py` (bloque que lee el frontmatter, ~línea 95, y la construcción de `Tramite`, ~línea 140)
- Test: `tests/test_extractor_metadatos.py`, `tests/test_manifiesto.py`

**Interfaces:**
- Produces: `Tramite.ruts_id: str = ""`; el hueco `Hueco("por_confirmar", "META-RUTS", "metadatos", <mensaje>)` cuando el frontmatter del AS-IS no trae `ruts_id`.

- [ ] **Step 1: Write the failing tests**

En `tests/test_extractor_metadatos.py` (usa el mismo AS-IS mínimo que los tests vecinos y le añade frontmatter):
- `test_lee_ruts_id_del_frontmatter_con_y_sin_comillas`: frontmatter `ruts_id: "4321"` y `ruts_id: 4321` dan `r.tramite.ruts_id == "4321"`, y no aparece `META-RUTS` en `r.huecos`.
- `test_ruts_id_ausente_da_hueco_meta_ruts_por_confirmar_y_no_bloquea`: sin la clave, `r.tramite.ruts_id == ""` y hay un hueco con `codigo == "META-RUTS"` y `nivel == "por_confirmar"`.
- `test_ruts_id_que_no_es_alfanumerico_o_pasa_de_20_se_descarta_con_el_hueco`: `ruts_id: "43 21"`, `"a/b"` y 21 caracteres dan `ruts_id == ""` y `META-RUTS`.

En `tests/test_manifiesto.py`: `test_tramite_acepta_ruts_id_y_por_omision_es_vacio` y que `guardar` (exclude_defaults) no escribe la clave cuando está vacía.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_extractor_metadatos.py tests/test_manifiesto.py -q`
Expected: FAIL (`ruts_id` no existe en `Tramite`).

- [ ] **Step 3: Implement**

`Tramite.ruts_id: str = ""` (campo opcional, al final del modelo para no mover el orden de serialización). En `metadatos.extraer`, junto a la lectura de `dependencia`, leer `^ruts_id:\s*["']?([A-Za-z0-9]{1,20})["']?\s*$` (multilínea, insensible a mayúsculas en la clave) solo dentro del frontmatter (`_FRONTMATTER`), y pasarlo a `Tramite(ruts_id=…)`. Si no hay coincidencia, `ruts_id = ""` y se añade el hueco `META-RUTS` con el mensaje «no se encontró `ruts_id` en el frontmatter del AS-IS; sin él Simplifica no puede ver el estado de este expediente». Un valor presente pero inválido también deja `""` y el mismo hueco.

- [ ] **Step 4: Run the new tests and the whole suite**

Run: `.venv/bin/pytest -q`
Expected: los nuevos pasan. Si una prueba existente enumera la lista exacta de huecos de un expediente sin `ruts_id`, se le añade `META-RUTS` a lo esperado (es un hueco nuevo legítimo, no se ablanda ninguna aserción); anotar en el commit cuáles pruebas se tocaron. Todo en verde.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/manifiesto.py src/gpmc/extractores/metadatos.py tests
git commit -m "feat(metadatos): ruts_id del frontmatter en el manifiesto y hueco META-RUTS"
```

---

### Task 2: Registro persistente `estado.jsonl`

**Files:**
- Create: `src/gpmc/web/estado.py`
- Test: `tests/test_estado.py`

**Interfaces:**
- Produces (todas en `gpmc.web.estado`):
  - `ARCHIVO = "estado.jsonl"`, `ENTREGABLES = ("as-is", "to-be", "diccionario", "bpmn", "gpm", "aprobacion", "publicado")`
  - `RUTS_VALIDO: re.Pattern` = `\A[A-Za-z0-9]{1,20}\Z`
  - `hoy() -> str`: `AAAA-MM-DD` en `America/Mexico_City` (con `zoneinfo`; si la zona no existe en el sistema, desplazamiento fijo de −6 h, que es el vigente desde 2022).
  - `anotar(raiz: Path, ruts_id: str, entregable: str, cuando: Optional[str] = None) -> bool`: crea la línea si no existe; fija la fecha **solo si estaba en `null`**; ignora un `ruts_id` que no cumple `RUTS_VALIDO` o un entregable fuera de `ENTREGABLES` (devuelve `False`); nunca lanza.
  - `leer(raiz: Path) -> "list[dict]"`: tolerante, salta una línea corrupta y lo dice en el log.
  - `consultar(raiz: Path, ruts_id: str) -> "list[dict]"`: `[]` si no hay línea; si la hay, `[{"analista": "", "actualizado": <la fecha más reciente entre los entregables>, "entregables": {las 7 claves}}]`.

- [ ] **Step 1: Write the failing tests** (`tests/test_estado.py`, siguiendo `tests/test_tablero.py`)

- `test_anotar_crea_la_linea_con_siete_claves_y_solo_la_anotada_tiene_fecha`
- `test_anotar_no_reescribe_una_fecha_ya_puesta` (segunda llamada con otra fecha deja la primera)
- `test_anotar_rechaza_ruts_invalido_y_entregable_desconocido` (devuelve `False`; el archivo no se crea): `""`, `"4321&x=1"`, `"../x"`, `"a b"`, 21 caracteres, y entregable `"foo"`.
- `test_consultar_sin_linea_devuelve_lista_vacia` y `test_consultar_con_ruts_parecido_no_mezcla` (`4321` vs `43210` vs `4321a`; mayúsculas distintas son otro `ruts_id`).
- `test_consultar_actualizado_es_la_fecha_mas_reciente`
- `test_leer_salta_linea_corrupta_y_no_revienta` (con `caplog`, como el del tablero)
- `test_la_purga_de_sesiones_no_toca_estado_jsonl` (como el del tablero)
- `test_anotar_no_deja_archivo_temporal_y_no_pierde_lo_previo_si_falla_la_escritura` (monkeypatch de `os.replace`)
- `test_hoy_tiene_formato_de_fecha`

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_estado.py -q`
Expected: FAIL (módulo inexistente).

- [ ] **Step 3: Implement `gpmc/web/estado.py`**

Copia el patrón de `web/tablero.py`: reescritura atómica con temporal + `os.replace`, lectura tolerante. Un `threading.Lock` de módulo envuelve el ciclo leer-modificar-escribir de `anotar` (el extractor y una descarga pueden coincidir). Las líneas se ordenan por `ruts_id` al escribir.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_estado.py tests/test_tablero.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/estado.py tests/test_estado.py
git commit -m "feat(estado): registro persistente estado.jsonl por ruts_id"
```

---

### Task 3: Anotar los entregables al extraer y al descargar el `.gpm`

**Files:**
- Modify: `src/gpmc/web/api.py:364-395` (`extraer_y_persistir`) y `:1111-1140` (`descargar_gpm`)
- Modify: `src/gpmc/web/app.py:340-366` (rama `que == "gpm"` de `descargar`)
- Test: `tests/test_estado_hitos.py`

**Interfaces:**
- Consumes: `estado.anotar(raiz, ruts_id, entregable)` (Task 2); `Tramite.ruts_id` (Task 1); `INSUMOS` de `web/sesiones.py` (claves `as_is`, `to_be`, `diccionario`).
- Produces: tras extraer, la línea del `ruts_id` tiene fecha en `as-is`/`to-be`/`diccionario` según qué archivo de `INSUMOS` existe en la carpeta; tras una descarga de producción con 200, fecha en `gpm`.

- [ ] **Step 1: Write the failing tests** (`tests/test_estado_hitos.py`, con `TestClient(crear_app(almacen=tmp_path))` como `tests/test_api.py`)

- `test_extraer_anota_as_is_to_be_y_diccionario_de_los_archivos_subidos`: subir AS-IS (con frontmatter `ruts_id: "4321"`), TO-BE y Diccionario; `estado.consultar(tmp_path, "4321")` trae esas tres con fecha y `gpm` en `None`.
- `test_extraer_solo_con_diccionario_anota_solo_diccionario`
- `test_extraer_sin_ruts_id_no_crea_estado_jsonl`
- `test_reextraer_no_cambia_la_fecha_del_as_is` (monkeypatch de `estado.hoy` a otro día entre dos extracciones)
- `test_descargar_gpm_con_200_anota_gpm` (por `/api/v1/expedientes/{sid}/gpm` y por `/descargar/{sid}/gpm`)
- `test_descargar_gpm_bloqueado_409_no_anota_gpm`
- `test_descargar_gpm_de_pruebas_no_anota_gpm`

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_estado_hitos.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

En `extraer_y_persistir`, después de `guardar(...)`: si `res.manifiesto.tramite.ruts_id`, anotar cada entregable cuyo archivo de `INSUMOS` exista en `carpeta`. En las dos rutas de descarga de `.gpm`, justo antes de devolver la respuesta 200 en modo producción, anotar `gpm` con el `ruts_id` del manifiesto. Una función auxiliar privada en `estado.py` (`anotar_insumos(raiz, carpeta, ruts_id)`) evita duplicar el recorrido de `INSUMOS`; vive en `web/` porque `INSUMOS` es de `sesiones`.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_estado_hitos.py tests/test_api.py tests/test_web.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web tests/test_estado_hitos.py
git commit -m "feat(estado): anota insumos al extraer y gpm al descargar con la puerta abierta"
```

---

### Task 4: El endpoint `GET /api/v1/expedientes?ruts_id=…` con token de servicio

**Files:**
- Create: `src/gpmc/web/api_estado.py`
- Modify: `src/gpmc/web/app.py:73-77` (incluir el router) y `src/gpmc/web/acceso.py` (`_PROTEGIDAS`/middleware y auditoría)
- Test: `tests/test_api_estado.py`

**Interfaces:**
- Consumes: `estado.consultar`, `estado.RUTS_VALIDO` (Task 2).
- Produces: `crear_router_estado(raiz: Path, entorno: Optional[dict] = None) -> APIRouter`, con `GET /api/v1/expedientes`. `entorno=None` lee `os.environ` **en cada petición** (así se puede rotar el token y las pruebas lo inyectan).
- Orden de las respuestas: variable sin definir → 404 `{"error":"no encontrado"}`; token ausente, vacío, sin `Bearer` o distinto → 401 `{"error":"no autorizado"}` (el mismo cuerpo siempre, sin pistas); `ruts_id` ausente o que no cumple `RUTS_VALIDO` → 422; en otro caso 200 `{"expedientes": estado.consultar(...)}`.
- El manejador pone `request.state.servicio = True` solo con token válido.

- [ ] **Step 1: Write the failing tests** (`tests/test_api_estado.py`; `crear_app(almacen=tmp_path, entorno={"GPMC_TOKEN_SERVICIO": "tok-123"})`)

- `test_sin_variable_de_token_la_ruta_no_existe_404`
- `test_sin_token_o_con_token_malo_o_sin_bearer_da_401_con_el_mismo_cuerpo`
- `test_con_token_valido_y_sin_expediente_devuelve_lista_vacia`
- `test_contrato_exacto_siete_claves_y_nulos`: tras extraer un expediente con `ruts_id: "4321"` (AS-IS + Diccionario) y consultar, la respuesta es `{"expedientes":[{"analista":"","actualizado":"<hoy>","entregables":{"as-is":"<hoy>","to-be":null,"diccionario":"<hoy>","bpmn":null,"gpm":null,"aprobacion":null,"publicado":null}}]}` (compara el diccionario completo, claves incluidas).
- `test_ruts_id_ausente_o_invalido_da_422` (`""`, ausente, `4321&x=1`, `a b`, 21 caracteres, `../x`).
- `test_un_jwt_de_persona_en_la_cabecera_no_abre_la_ruta` (app con `usuarios` y `jwt_secreto` inyectados como en `tests/test_auditoria.py`/`test_usuarios.py`; el JWT válido de una persona da 401).
- `test_el_token_de_servicio_no_abre_otras_rutas` (con usuarios instalados, `GET /api/v1/historial` con el token de servicio da 401).
- `test_la_respuesta_no_trae_campos_del_ciudadano`: ninguna clave fuera de `analista`, `actualizado`, `entregables`.
- `test_la_consulta_con_token_valido_queda_auditada_como_servicio_simplifica` (acción `estado.consultar`, usuario `servicio:simplifica`) y `test_sin_almacen_de_usuarios_no_se_audita_y_responde_igual`.
- `test_registro_corrupto_no_da_500` (archivo `estado.jsonl` con basura: 200 con lista vacía).
- `test_post_expedientes_sigue_funcionando_igual` (el nuevo GET no pisa el POST de `/api/v1/expedientes`).

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_api_estado.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

`api_estado.py` con `hmac.compare_digest` sobre `str.encode`. En `acceso.py`, un patrón `_ESTADO_SERVICIO` (método GET, ruta exacta `/api/v1/expedientes`) que **excluye** esa ruta del 401 por falta de sesión; el manejador es quien valida. Después de `call_next`, si `getattr(request.state, "servicio", False)`, `usuarios.auditar("servicio:simplifica", "", "estado.consultar", None, f"{ruts_id} ({resp.status_code})", _ip(request))` con el `ruts_id` de `request.query_params`. En `app.py` incluir `crear_router_estado(raiz, entorno=entorno)` junto a los demás routers. Añadir `"estado.consultar"` al mapa de acciones legibles en `frontend/src/features/auditoria/lenguaje.ts` («Simplifica consultó el estado de un expediente») con su caso en `lenguaje.test.ts`.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest -q && bash scripts/check-frontend.sh`
Expected: todo en verde.

- [ ] **Step 5: Commit**

```bash
git add src tests frontend/src/features/auditoria
git commit -m "feat(api): GET /api/v1/expedientes?ruts_id con token de servicio para Simplifica"
```

---

### Task 5: Prueba de contrato contra el cliente real de Sistema-3.0

**Files:**
- Test: `tests/test_contrato_sistema3.py`

**Interfaces:**
- Consumes: el endpoint de Task 4.

- [ ] **Step 1: Write the test**

Un test que se **salta si no existe** la variable `SISTEMA3_RAIZ` o el archivo `shared/compilador.py` (como las pruebas de material real de `CLAUDE.md`): levanta la app con `uvicorn` en un hilo en `127.0.0.1` (el cliente exige https, así que el test usa la función de parseo del cliente directamente si la expone; si no, replica su lectura de `expedientes[0]` y de los siete entregables) y comprueba que la etapa calculada por Sistema-3.0 para un expediente con as-is + diccionario es «Diccionario de Datos». Cuenta como verificación del acuerdo entre los dos repos, no como prueba obligatoria.

- [ ] **Step 2: Run**

Run: `SISTEMA3_RAIZ=/Users/danielhernandezrubio/Desktop/Projects/Sistema-3.0 .venv/bin/pytest tests/test_contrato_sistema3.py -q`
Expected: PASS. Sin la variable: SKIPPED.

- [ ] **Step 3: Commit**

```bash
git add tests/test_contrato_sistema3.py
git commit -m "test(contrato): el estado entiende lo que espera shared/compilador.py de Sistema-3.0"
```

---

### Task 6: Token de servicio y despliegue

**Files:**
- Modify: `scripts/desplegar.sh` (función `entorno`)
- Modify: `scripts/aws/40-frontend.sh` solo si la prueba de cabeceras de abajo falla

**Interfaces:**
- Consumes: `GPMC_TOKEN_SERVICIO` en `scripts/aws/estado.env` (se genera una vez, igual que `GPMC_JWT_SECRETO`).

- [ ] **Step 1: Escribir el token en el entorno del servidor**

En la función `entorno`, después del bloque del JWT: `tok=$(leer GPMC_TOKEN_SERVICIO)`; si está vacío, generarlo con `openssl rand -hex 32` y `guardar GPMC_TOKEN_SERVICIO "$tok"`; añadir `echo "GPMC_TOKEN_SERVICIO=$tok"` al archivo que se instala. El token nunca se imprime en pantalla.

- [ ] **Step 2: Verificar el script**

Run: `bash -n scripts/desplegar.sh`
Expected: sin salida (sintaxis válida).

- [ ] **Step 3: Desplegar (acción de Daniel: toca producción)**

Pedir a Daniel que apruebe, y entonces: `scripts/desplegar.sh` (la suite corre primero). Daniel entrega el token a la sesión de Sistema-3.0 (`grep GPMC_TOKEN_SERVICIO scripts/aws/estado.env`, nunca por chat ni git).

- [ ] **Step 4: Verificar en producción que CloudFront deja pasar la cabecera `Authorization`**

Run: `curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" 'https://compilador-gpm.commit-lab.pro/api/v1/expedientes?ruts_id=0'` y la misma sin cabecera.
Expected: `200` con token y `401` sin él. Un `404` o un `401` con token correcto indica que la distribución no reenvía `Authorization` en `/api/*`: corregir la política de origen de esa regla en `scripts/aws/40-frontend.sh` (reenviar `Authorization`) y repetir.

- [ ] **Step 5: Comando para Simplifica**

Entregar a Daniel, para que lo corra en el repo de Sistema-3.0: `COMPILADOR_URL=https://compilador-gpm.commit-lab.pro COMPILADOR_TOKEN=<el mismo token> SISTEMA3_NOMBRE=sistema3-sandbox scripts/desplegar.sh entorno`.

- [ ] **Step 6: Commit**

```bash
git add scripts/desplegar.sh
git commit -m "chore(despliegue): token de servicio para Simplifica en el entorno del servidor"
```

---

### Task 7: Nombre visible «Telar»

**Files:**
- Modify: los textos de interfaz que digan «Compilador GPM» (`grep -rn "Compilador GPM" src frontend/src README.md`), incluido `FastAPI(title=…)` en `src/gpmc/web/app.py:64`.
- Test: las pruebas que fijen esos textos.

- [ ] **Step 1:** Listar cada aparición con `grep` y separar lo que ve la persona (título de la SPA, cabecera, `FastAPI(title)`, README) de lo que no se toca (paquete `gpmc`, CLI, notas históricas, actas).
- [ ] **Step 2:** Cambiar solo lo visible; actualizar las aserciones que fijan el texto viejo por el nuevo (es un cambio de producto, no un ablandamiento). Run: `.venv/bin/pytest -q && bash scripts/check-frontend.sh` → verde.
- [ ] **Step 3:** El dominio (`telar.commit-lab.pro`) **no** se toca aquí: se decide con Daniel al desplegar, y `COMPILADOR_URL` de Simplifica se actualiza entonces.
- [ ] **Step 4: Commit** `git commit -am "feat: el nombre visible del proyecto es Telar"`

---

## Self-Review

- **Spec coverage:** `ruts_id` y `META-RUTS` (T1), registro persistente y purga (T2), fechas por primera aparición, `gpm` solo con 200, `null` en bpmn/aprobacion/publicado, `analista` vacío (T2–T3), contrato exacto y siete claves (T4), token de servicio, 404/401/422, auditoría `servicio:simplifica`, token de persona rechazado (T4), despliegue y envío del mismo token a Simplifica (T6), nombre Telar (T7). Dominio nuevo: diferido por decisión del spec.
- **Desviación del spec, a confirmar con Daniel:** el spec dice que los hitos de `planeacion/registro` ganan sobre las fechas. Este plan **no** lo implementa: `registro` está indexado por nombre, sin `ruts_id`, y el servidor no tiene una ruta fija a su archivo; unirlos reintroduciría el emparejado por nombre que Daniel descartó. Las fechas salen solo de `estado.jsonl`.
- **Tipos:** `anotar`, `consultar`, `leer`, `hoy`, `ENTREGABLES`, `RUTS_VALIDO` y `crear_router_estado` se usan con las mismas firmas en T2, T3 y T4.
- **Riesgo conocido:** si CloudFront no reenvía `Authorization` en `/api/*`, la API funciona en el servidor pero no desde Simplifica; T6 lo verifica con curl antes de dar nada por hecho.
