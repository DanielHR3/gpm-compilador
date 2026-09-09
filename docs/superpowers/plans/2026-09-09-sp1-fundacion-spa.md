# SP1 — Fundación de la SPA: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el asistente web tenga una SPA React (Vite + shadcn) servida por FastAPI en un solo origen, con `/api/v1/*` en JSON, y que las pantallas de carga de insumos y de resolución de huecos corran en React con paridad — sin big-bang y sin que la suite de Python baje de verde.

**Architecture:** FastAPI gana un `APIRouter` en `/api/v1` (solo JSON) y sirve `frontend/dist/` como estáticos con *fallback* SPA. El HTML actual (`web/plantillas.py`, `simulador/html.py`) convive hasta que React tenga paridad; el último task corta `/` y `/revisar/*` a la SPA y borra solo esos dos handlers. El servidor sigue siendo la fuente de verdad (carpetas de sesión en disco + purga TTL); React lleva una copia en memoria.

**Tech Stack:** Backend: Python 3.9+, FastAPI, Pydantic v2, pytest. Frontend: Vite, React 18, TypeScript, Tailwind, shadcn/ui, `hidalgo-design-token-system@latest`, Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-09-sp1-fundacion-spa-design.md`

## Global Constraints

- **Python:** compatible con 3.9 — nada de `X | None` en anotaciones, usar `Optional[X]`. Identificadores y módulos en español sin acentos.
- **Suite de Python:** nunca baja de verde. Estado de partida: `.venv/bin/pytest -v` = **318 passed, 22 skipped**. Cada task que toca Python la deja igual o con más verdes.
- **`nucleo/formato.py` NO se toca.** Su serialización asegura la compatibilidad byte a byte con PHP.
- **`SINTAXIS_ESTRICTA` NO se toca** (queda en `False`).
- **No se borran archivos `.gpm` existentes.**
- **El HTML viejo NO se toca** salvo el corte del Task 11 (que solo elimina los handlers `portada` y `revisar`).
- **CSP:** la SPA con `Content-Security-Policy: default-src 'self'`. `/vistas/{sid}` conserva su CSP `sandbox`. Las cabeceras `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: no-referrer` del middleware actual se mantienen en todas las respuestas.
- **`frontend/dist/` y `frontend/node_modules/` NO se comitean.**
- **Diseño y colores:** salen del paquete `hidalgo-design-token-system@latest`. Fallback si no está disponible: la paleta guinda actual (`#5e132c` / `#66132a`) como variables CSS con los nombres que espera shadcn.
- **Commits:** terminan con `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` y `Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP`. Commit directo a `main` (el proyecto no usa PRs).

---

## File Structure

**Backend (nuevo):**
- `src/gpmc/web/sesiones.py` — helpers de sesión (hoy anidados en `crear_app`): `carpeta_de`, `manifiesto_de`, `huecos_vivos`, `reconocidos_de`, `escribir_reconocidos`, `_SESION_VALIDA`. Sin lógica de dominio nueva.
- `src/gpmc/web/api.py` — `APIRouter(prefix="/api/v1")`, solo JSON. Un endpoint por función.

**Backend (modificado):**
- `src/gpmc/nucleo/huecos.py` — añade `HuecoOut` (Pydantic) para serializar/validar por FastAPI.
- `src/gpmc/web/app.py` — importa de `sesiones.py`, `include_router(api_router)`, monta `StaticFiles`, `503` si falta `dist/`, *fallback* SPA; en Task 11 quita `portada` y `revisar`.

**Frontend (nuevo, todo bajo `frontend/`):**
- `package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`, `tailwind.config.ts`, `postcss.config.js`, `components.json`, `vitest.config.ts`, `README.md`, `.gitignore`
- `src/main.tsx`, `src/App.tsx`, `src/index.css`, `src/vite-env.d.ts`, `src/test/setup.ts`
- `src/lib/types.ts` — tipos TS espejo del JSON de `/api/v1`
- `src/lib/api.ts` — cliente tipado
- `src/components/ui/*` — componentes shadcn (código propio)
- `src/features/carga/CargaInsumos.tsx` (+ `.test.tsx`)
- `src/features/huecos/WizardHuecos.tsx`, `TarjetaHueco.tsx` (+ tests)
- `src/features/huecos/controles/` — `ControlActor.tsx` (MMD-03), `ControlTexto.tsx` (META-01/02), `ControlCampoPadre.tsx` (API-03), `BotonReconocer.tsx`

**Otros (modificado):**
- `.gitignore` (raíz) — `frontend/node_modules/`, `frontend/dist/`
- `scripts/check-frontend.sh` — `tsc --noEmit && vite build && vitest run`
- `despliegue/instalar-servicio.sh`, `despliegue/LEEME.md`, `Abrir Compilador GPM.command` — paso de build
- `CLAUDE.md` — sección del frontend + flujo de dev

---

## Task 1: Extraer los helpers de sesión a `web/sesiones.py`

Refactor puro, sin cambio de comportamiento. Hoy `_carpeta`, `_manifiesto`, `_huecos_vivos`, `_reconocidos` son closures dentro de `crear_app` (cierran sobre `raiz`); `api.py` no puede importarlas. Se sacan a funciones de módulo que reciben `raiz` (o `carpeta`) como argumento.

**Files:**
- Create: `src/gpmc/web/sesiones.py`
- Modify: `src/gpmc/web/app.py` (imports + reemplazar las llamadas internas)
- Test: `tests/test_web.py` (añadir), `tests/test_sesiones.py` (crear)

**Interfaces:**
- Produces:
  - `_SESION_VALIDA: re.Pattern` (movido desde `app.py`)
  - `carpeta_de(raiz: Path, sid: str) -> Optional[Path]` — valida `sid` contra `_SESION_VALIDA`; devuelve `raiz / sid` si es un directorio, si no `None`
  - `manifiesto_de(raiz: Path, sid: str)` — `cargar(carpeta / "manifiesto.yaml")` o `None`
  - `huecos_vivos(carpeta: Path) -> list[Hueco]` — lee `huecos.json`
  - `reconocidos_de(carpeta: Path) -> set[tuple]` — lee `reconocidos.json`
  - `escribir_reconocidos(carpeta: Path, rec: set) -> None` — `json.dumps(sorted(rec), ensure_ascii=False)`

- [ ] **Step 1: Escribir la prueba que falla** — `tests/test_sesiones.py`

```python
import json
from pathlib import Path
from gpmc.web.sesiones import carpeta_de, huecos_vivos, reconocidos_de, escribir_reconocidos


def test_carpeta_de_rechaza_un_sid_invalido(tmp_path):
    assert carpeta_de(tmp_path, "../../etc") is None
    assert carpeta_de(tmp_path, "no-hex") is None
    assert carpeta_de(tmp_path, "a" * 16) is None          # no existe el dir


def test_carpeta_de_acepta_un_sid_valido_y_existente(tmp_path):
    d = tmp_path / ("a" * 16)
    d.mkdir()
    assert carpeta_de(tmp_path, "a" * 16) == d


def test_huecos_vivos_y_reconocidos_ida_y_vuelta(tmp_path):
    d = tmp_path / ("b" * 16)
    d.mkdir()
    (d / "huecos.json").write_text(json.dumps(
        [{"nivel": "falta_dato", "codigo": "META-01", "ubicacion": "metadatos",
          "mensaje": "x", "propuesta": None}]), encoding="utf-8")
    hs = huecos_vivos(d)
    assert len(hs) == 1 and hs[0].codigo == "META-01"

    assert reconocidos_de(d) == set()
    escribir_reconocidos(d, {("DIC-07", "p1")})
    assert reconocidos_de(d) == {("DIC-07", "p1")}
```

- [ ] **Step 2: Correr y ver que falla**

Run: `.venv/bin/pytest tests/test_sesiones.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpmc.web.sesiones'`

- [ ] **Step 3: Crear `src/gpmc/web/sesiones.py`**

Copiar textualmente el cuerpo de los cuatro helpers de `app.py` (`_carpeta`, `_manifiesto`, `_huecos_vivos`, `_reconocidos`) y el de `_purgar_sesiones` **NO** (ese ya es de módulo). Firmas de arriba. `_SESION_VALIDA` se mueve aquí; en `app.py` se importa desde aquí. Ejemplo del más delicado:

```python
import json
import re
from pathlib import Path
from typing import Optional

from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import cargar

_SESION_VALIDA = re.compile(r"\A[0-9a-f]{16}\Z")


def carpeta_de(raiz: Path, sid: str) -> Optional[Path]:
    if not _SESION_VALIDA.match(sid or ""):
        return None
    destino = raiz / sid
    return destino if destino.is_dir() else None


def manifiesto_de(raiz: Path, sid: str):
    carpeta = carpeta_de(raiz, sid)
    if carpeta is None:
        return None
    ruta = carpeta / "manifiesto.yaml"
    return cargar(ruta) if ruta.exists() else None


def huecos_vivos(carpeta: Path) -> "list[Hueco]":
    ruta = carpeta / "huecos.json"
    if not ruta.exists():
        return []
    return [Hueco(**d) for d in json.loads(ruta.read_text(encoding="utf-8"))]


def reconocidos_de(carpeta: Path) -> set:
    ruta = carpeta / "reconocidos.json"
    if not ruta.exists():
        return set()
    return {tuple(x) for x in json.loads(ruta.read_text(encoding="utf-8"))}


def escribir_reconocidos(carpeta: Path, rec: set) -> None:
    (carpeta / "reconocidos.json").write_text(
        json.dumps(sorted(rec), ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 4: Reescribir `app.py` para usar el módulo**

En `app.py`: `from gpmc.web.sesiones import carpeta_de, manifiesto_de, huecos_vivos, reconocidos_de, escribir_reconocidos, _SESION_VALIDA`. Borrar las cuatro definiciones anidadas. Sustituir cada llamada: `_carpeta(sid)` → `carpeta_de(raiz, sid)`; `_manifiesto(sid)` → `manifiesto_de(raiz, sid)`; `_huecos_vivos(carpeta)` → `huecos_vivos(carpeta)`; `_reconocidos(carpeta)` → `reconocidos_de(carpeta)`; la escritura de `reconocidos.json` en el handler `/reconocer` → `escribir_reconocidos(carpeta, rec)`.

- [ ] **Step 5: Correr toda la suite**

Run: `.venv/bin/pytest -q`
Expected: `318 passed, 22 skipped` (más las 3 nuevas de `test_sesiones.py` = 321 passed).

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/web/sesiones.py src/gpmc/web/app.py tests/test_sesiones.py
git commit -m "refactor(web): extrae los helpers de sesion a web/sesiones.py

Sin cambio de comportamiento. Los helpers (_carpeta, _manifiesto,
_huecos_vivos, _reconocidos) eran closures dentro de crear_app; ahora son
funciones de modulo que reciben raiz, para que web/api.py pueda importarlas.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 2: `HuecoOut` — modelo Pydantic para serializar huecos

**Files:**
- Modify: `src/gpmc/nucleo/huecos.py` (añadir al final, sin tocar el `dataclass Hueco`)
- Test: `tests/test_huecos.py` (añadir)

**Interfaces:**
- Produces: `HuecoOut(BaseModel)` con `nivel: str`, `codigo: str`, `ubicacion: str`, `mensaje: str`, `propuesta: Optional[str]`; classmethod `HuecoOut.desde(h: Hueco) -> "HuecoOut"`.

- [ ] **Step 1: Prueba que falla** — `tests/test_huecos.py`

```python
def test_HuecoOut_serializa_un_Hueco():
    from gpmc.nucleo.huecos import Hueco, HuecoOut
    h = Hueco("falta_dato", "META-01", "metadatos", "falta el tiempo", propuesta=None)
    out = HuecoOut.desde(h)
    assert out.model_dump() == {
        "nivel": "falta_dato", "codigo": "META-01", "ubicacion": "metadatos",
        "mensaje": "falta el tiempo", "propuesta": None,
    }
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/pytest tests/test_huecos.py::test_HuecoOut_serializa_un_Hueco -v`
Expected: FAIL — `ImportError: cannot import name 'HuecoOut'`

- [ ] **Step 3: Implementar en `huecos.py`**

```python
from pydantic import BaseModel


class HuecoOut(BaseModel):
    """Vista serializable de Hueco para las respuestas de /api/v1."""
    nivel: str
    codigo: str
    ubicacion: str
    mensaje: str
    propuesta: Optional[str] = None

    @classmethod
    def desde(cls, h: "Hueco") -> "HuecoOut":
        return cls(nivel=h.nivel, codigo=h.codigo, ubicacion=h.ubicacion,
                   mensaje=h.mensaje, propuesta=h.propuesta)
```

- [ ] **Step 4: Pasa**

Run: `.venv/bin/pytest tests/test_huecos.py -v` → PASS. Luego `.venv/bin/pytest -q` → sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/huecos.py tests/test_huecos.py
git commit -m "feat(huecos): HuecoOut, modelo Pydantic para /api/v1

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 3: `/api/v1/expedientes` — crear y leer

**Files:**
- Create: `src/gpmc/web/api.py`
- Modify: `src/gpmc/web/app.py` (`from gpmc.web.api import crear_router` + `app.include_router(crear_router(raiz))`)
- Test: `tests/test_api.py` (crear)

**Interfaces:**
- Consumes: `carpeta_de`, `manifiesto_de`, `huecos_vivos` de Task 1; `HuecoOut` de Task 2; `_MAX_SUBIDA`, `_purgar_sesiones`, `INSUMOS`, `ARCHIVO_VISTAS` de `app.py` (se mueven a `sesiones.py` o se importan de `app.py` — decidir: para evitar ciclo, mover `_MAX_SUBIDA`, `INSUMOS`, `ARCHIVO_VISTAS` a `sesiones.py` en este task).
- Produces: `crear_router(raiz: Path) -> APIRouter`. Endpoints:
  - `POST /api/v1/expedientes` (multipart) → `201 {sid, manifiesto, huecos, estimacion, problemas, tiene_vistas}`; `413 {error, archivos}`; `422 {error}`
  - `GET /api/v1/expedientes/{sid}` → `200 {...}`; `404 {error}`
  - forma del cuerpo: `EstadoExpediente` (Pydantic): `sid: str`, `manifiesto: dict`, `huecos: list[HuecoOut]`, `estimacion: dict`, `problemas: list[str]`, `tiene_vistas: bool`.

- [ ] **Step 1: Prueba que falla** — `tests/test_api.py`

```python
from fastapi.testclient import TestClient
from gpmc.web.app import crear_app

_DICC = ("### Pantalla 1 — Solicitante — Datos\n\n"
         "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
         "| CURP | Texto | Input | Si | La CURP `@@curp` |\n")


def _cli(tmp_path):
    return TestClient(crear_app(almacen=tmp_path))


def test_post_expedientes_devuelve_json_con_sid_y_huecos(tmp_path):
    r = _cli(tmp_path).post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["sid"]) == 16
    assert body["manifiesto"]["tramite"]["nombre"]
    assert any(h["codigo"] == "INS-01" for h in body["huecos"])
    assert "estimacion" in body and "problemas" in body


def test_get_expediente_recupera_el_estado(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}")
    assert r.status_code == 200
    assert r.json()["sid"] == sid


def test_get_expediente_inexistente_da_404(tmp_path):
    r = _cli(tmp_path).get("/api/v1/expedientes/0123456789abcdef")
    assert r.status_code == 404


def test_post_expedientes_archivo_gigante_da_413(tmp_path):
    r = _cli(tmp_path).post("/api/v1/expedientes", files={
        "diccionario": ("enorme.md", b"x" * (11 * 1024 * 1024), "text/markdown")})
    assert r.status_code == 413
    assert "enorme.md" in r.json()["archivos"]
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: FAIL — `404` en todas (no existe el router).

- [ ] **Step 3: Implementar `api.py`**

`crear_router(raiz)` construye un `APIRouter(prefix="/api/v1")`. El handler de `POST /expedientes` reproduce la lógica de `POST /extraer` de `app.py` (purga, `_leer` con tope y lista `grandes`, escribir insumos + `Vistas.html`, `extraer_expediente`, escribir `manifiesto.yaml` + `huecos.json`) pero devuelve JSON en vez de HTML:

```python
from pathlib import Path
import json
import secrets
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpmc.estimador import estimar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.nucleo.huecos import Hueco, HuecoOut
from gpmc.nucleo.manifiesto import guardar
from gpmc.simulador.analisis import analizar
from gpmc.web.sesiones import (carpeta_de, manifiesto_de, huecos_vivos,
                               _MAX_SUBIDA, INSUMOS, ARCHIVO_VISTAS, _purgar_sesiones)


class EstadoExpediente(BaseModel):
    sid: str
    manifiesto: dict
    huecos: list[HuecoOut]
    estimacion: dict
    problemas: list[str]
    tiene_vistas: bool


def _estado(sid: str, carpeta: Path, manifiesto) -> EstadoExpediente:
    est = estimar(manifiesto)
    return EstadoExpediente(
        sid=sid,
        manifiesto=json.loads(manifiesto.model_dump_json()),
        huecos=[HuecoOut.desde(h) for h in huecos_vivos(carpeta)],
        estimacion={"nivel": est.nivel, "dias": est.dias,
                    "metricas": est.metricas.__dict__ if hasattr(est.metricas, "__dict__") else est.metricas,
                    "advertencia": est.advertencia},
        problemas=analizar(manifiesto).problemas,
        tiene_vistas=(carpeta / ARCHIVO_VISTAS).exists(),
    )


def crear_router(raiz: Path) -> APIRouter:
    r = APIRouter(prefix="/api/v1")

    @r.post("/expedientes", status_code=201)
    async def crear_expediente(
        as_is: UploadFile = File(None), to_be: UploadFile = File(None),
        diccionario: UploadFile = File(...), vistas: UploadFile = File(None),
    ):
        _purgar_sesiones(raiz)
        sid = secrets.token_hex(8)
        carpeta = raiz / sid
        carpeta.mkdir(parents=True, exist_ok=True)
        grandes: list[str] = []

        async def _leer(a):
            datos = await a.read(_MAX_SUBIDA + 1)
            if len(datos) > _MAX_SUBIDA:
                grandes.append(a.filename or "sin nombre")
                return None
            return datos

        for clave, a in {"as_is": as_is, "to_be": to_be, "diccionario": diccionario}.items():
            if a is None:
                continue
            c = await _leer(a)
            if c:
                (carpeta / INSUMOS[clave]).write_bytes(c)
        if vistas is not None:
            cv = await _leer(vistas)
            if cv:
                (carpeta / ARCHIVO_VISTAS).write_bytes(cv)

        if grandes:
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=413, content={
                "error": "archivo demasiado grande",
                "archivos": grandes,
                "limite_mb": _MAX_SUBIDA // (1024 * 1024)})

        try:
            res = extraer_expediente(carpeta)
        except SinPermiso as exc:
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={"error": str(exc)})
        if res.manifiesto is None:
            motivo = res.huecos[0].mensaje if res.huecos else "no se pudo extraer el manifiesto"
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
            return JSONResponse(status_code=422, content={"error": motivo})

        guardar(res.manifiesto, carpeta / "manifiesto.yaml")
        (carpeta / "huecos.json").write_text(json.dumps(
            [{"nivel": h.nivel, "codigo": h.codigo, "ubicacion": h.ubicacion,
              "mensaje": h.mensaje, "propuesta": h.propuesta} for h in res.huecos],
            ensure_ascii=False), encoding="utf-8")
        return _estado(sid, carpeta, res.manifiesto)

    @r.get("/expedientes/{sid}", response_model=EstadoExpediente)
    async def leer_expediente(sid: str):
        carpeta = carpeta_de(raiz, sid)
        m = manifiesto_de(raiz, sid)
        if carpeta is None or m is None:
            return JSONResponse(status_code=404, content={"error": "sesión no encontrada"})
        return _estado(sid, carpeta, m)

    return r
```

> Nota: `_MAX_SUBIDA`, `INSUMOS`, `ARCHIVO_VISTAS` se **mueven** de `app.py` a `sesiones.py` en este task (y `app.py` los importa de vuelta) para no crear un ciclo `api.py → app.py → api.py`.

En `app.py`, dentro de `crear_app`, tras crear `app`: `from gpmc.web.api import crear_router` (import local, no top-level, para evitar ciclo) y `app.include_router(crear_router(raiz))`.

- [ ] **Step 4: Verificar el shape de `estimar()`**

Run: `.venv/bin/python -c "from gpmc.estimador import estimar; help(estimar)"` y revisar `src/gpmc/estimador.py` para los nombres reales de los campos del objeto que devuelve (`nivel`, `dias`, `metricas`, `advertencia` son los usados por `plantillas.revision`; confirmar). Ajustar `_estado` a los nombres reales.

- [ ] **Step 5: Correr**

Run: `.venv/bin/pytest tests/test_api.py -v` → PASS (4). Luego `.venv/bin/pytest -q` → 318 + nuevas, sin regresiones.

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/web/api.py src/gpmc/web/app.py src/gpmc/web/sesiones.py tests/test_api.py
git commit -m "feat(api): /api/v1/expedientes — crear (multipart) y leer (JSON)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 4: `/api/v1/expedientes/{sid}/resolver` y `/reconocer`

**Files:**
- Modify: `src/gpmc/web/api.py`
- Test: `tests/test_api.py` (añadir)

**Interfaces:**
- Consumes: los helpers de Task 1; el cuerpo de los handlers `/resolver` y `/reconocer` de `app.py` como referencia.
- Produces:
  - `POST /api/v1/expedientes/{sid}/resolver` — body `{"resoluciones": [{"tipo": "mmd03|meta01|meta02|api03", "ubicacion": str, "valor": str}]}` → `200 {"manifiesto": dict, "huecos": [HuecoOut]}`; `404`
  - `POST /api/v1/expedientes/{sid}/reconocer` — body `{"codigo": str, "ubicacion": str}` → `200 {"huecos": [HuecoOut], "reconocidos": [[str,str]]}`; `404`

- [ ] **Step 1: Prueba que falla**

```python
def test_resolver_aplica_meta01_y_devuelve_el_estado_nuevo(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={
        "resoluciones": [{"tipo": "meta01", "ubicacion": "metadatos", "valor": "5 dias habiles"}]})
    assert r.status_code == 200
    assert not any(h["codigo"] == "META-01" for h in r.json()["huecos"])
    man = c.get(f"/api/v1/expedientes/{sid}/manifiesto").text  # existe tras Task 5; aquí basta con el manifiesto del body
    assert "5 dias habiles" in r.json()["manifiesto"]["tramite"]["ruts"]["tiempo_entrega"]


def test_reconocer_marca_el_hueco_y_lo_devuelve(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/reconocer", json={"codigo": "INS-01", "ubicacion": ""})
    assert r.status_code == 200
    assert ["INS-01", ""] in r.json()["reconocidos"]
```

- [ ] **Step 2: Ver que falla** — `404`.

- [ ] **Step 3: Implementar**

Portar la lógica de `POST /resolver` de `app.py` (el bucle sobre `form.items()` con `mmd03_`, `meta01`, `meta02`, `api03_`) a un handler que recibe `{"resoluciones": [...]}` JSON. Cada `{tipo, ubicacion, valor}`:
- `mmd03`: `next(t for t in m.flujo.tareas if t.id == ubicacion).actor = valor`
- `meta01`: `m.tramite.ruts.tiempo_entrega = valor`
- `meta02`: `m.tramite.dependencia = valor`
- `api03`: `m.campo_por_nombre(ubicacion).dependencia_campo = valor`

Tras aplicar, `guardar(m, carpeta / "manifiesto.yaml")`, limpiar de `huecos.json` los `(codigo, ubicacion)` resueltos (el mapeo tipo→codigo: `mmd03→MMD-03`, `meta01→META-01`, `meta02→META-02`, `api03→API-03`), devolver `{"manifiesto": json.loads(m.model_dump_json()), "huecos": [...]}`.

`reconocer`: `rec = reconocidos_de(carpeta); rec.add((codigo, ubicacion)); escribir_reconocidos(carpeta, rec)`; devolver `{"huecos": [...], "reconocidos": [list(t) for t in sorted(rec)]}`.

- [ ] **Step 4: Correr** — `tests/test_api.py` PASS; `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/api.py tests/test_api.py
git commit -m "feat(api): resolver y reconocer huecos en /api/v1 (JSON)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 5: `/api/v1/expedientes/{sid}/gpm` y `/manifiesto`

**Files:**
- Modify: `src/gpmc/web/api.py`
- Test: `tests/test_api.py` (añadir)

**Interfaces:**
- Consumes: `bloquean` de `gpmc.nucleo.huecos`; `compilar` de `gpmc.compilador.a_gpm`; `serializar` de `gpmc.nucleo.formato`; `huecos_vivos`, `reconocidos_de`, `manifiesto_de`.
- Produces:
  - `GET /api/v1/expedientes/{sid}/gpm?modo=produccion|pruebas` → `200` `application/octet-stream` con `Content-Disposition`; `409 {"bloqueantes": [{"codigo","ubicacion","mensaje"}]}`; `404`
  - `GET /api/v1/expedientes/{sid}/manifiesto` → `200` `text/yaml`; `404`

- [ ] **Step 1: Prueba que falla**

```python
def test_gpm_bloqueado_da_409_con_lista(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 409
    assert any(b["codigo"] == "INS-01" for b in r.json()["bloqueantes"])


def test_gpm_se_descarga_cuando_no_hay_bloqueantes(tmp_path):
    # Diccionario + TO-BE lineal + AS-IS con dependencia y tiempo -> sin bloqueantes
    ...  # reusar _exp_limpio de test_cli/test_web adaptado a multipart
```

- [ ] **Step 2: Ver que falla** — `404`.

- [ ] **Step 3: Implementar** — el gate: `faltan = bloquean(huecos_vivos(carpeta), reconocidos_de(carpeta))`; si `faltan` → `409` con la lista; si no → `Response(serializar(compilar(m, modo_pruebas=(modo == "pruebas"))), media_type="application/octet-stream", headers={"content-disposition": f'attachment; filename="{base}.gpm"'})`. `/manifiesto` devuelve `(carpeta / "manifiesto.yaml").read_text()` con `media_type="text/yaml"`.

- [ ] **Step 4: Correr** — PASS; `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/api.py tests/test_api.py
git commit -m "feat(api): descarga del .gpm con la puerta del linter (409) y del manifiesto

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 6: FastAPI sirve `frontend/dist/` (montado en `/app`)

**Files:**
- Modify: `src/gpmc/web/app.py`
- Modify: `.gitignore` (raíz)
- Test: `tests/test_web.py` (añadir)

**Interfaces:**
- Produces: FastAPI monta los estáticos en `/app` (temporal; Task 11 lo pasa a `/`). Variable `GPMC_FRONTEND_DIST` (por defecto `<repo>/frontend/dist`). Si falta `index.html`, `GET /app` → `503` con texto claro.

- [ ] **Step 1: Prueba que falla** — `tests/test_web.py`

```python
def test_sin_dist_construido_la_ruta_app_da_503(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(tmp_path / "no-existe"))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    r = c.get("/app")
    assert r.status_code == 503
    assert "npm run build" in r.text


def test_con_dist_falso_la_ruta_app_sirve_index(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "x.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    assert c.get("/app").status_code == 200
    assert "SPA" in c.get("/app").text
    assert c.get("/app/assets/x.js").status_code == 200
    assert c.get("/app").headers["content-security-policy"].startswith("default-src 'self'")
```

- [ ] **Step 2: Ver que falla** — `404` en `/app`.

- [ ] **Step 3: Implementar en `app.py`**

```python
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse

# dentro de crear_app, al final:
dist = Path(os.environ.get("GPMC_FRONTEND_DIST", Path(__file__).resolve().parents[3] / "frontend" / "dist"))

@app.get("/app/{ruta:path}")
def _spa(ruta: str = ""):
    if not (dist / "index.html").exists():
        return PlainTextResponse(
            "El frontend no está compilado. Corre `cd frontend && npm ci && npm run build`.",
            status_code=503)
    candidato = (dist / ruta)
    if ruta and candidato.is_file():
        return FileResponse(candidato)
    resp = FileResponse(dist / "index.html")
    resp.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self' data:"
    return resp
```

(El middleware de cabeceras seguras ya añade `nosniff`/`X-Frame-Options`.)

- [ ] **Step 4: `.gitignore`** — añadir:

```
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 5: Correr** — PASS; `pytest -q` sin regresiones.

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/web/app.py .gitignore tests/test_web.py
git commit -m "feat(web): FastAPI sirve frontend/dist en /app (503 si no esta construido)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 7: Scaffold `frontend/` (Vite + React + TS + Tailwind + shadcn + tokens)

**Preludio obligatorio (confirmar antes de instalar nada):**
1. `node --version` y `npm --version` — si no hay Node, **detener** y avisar: SP1 no puede continuar sin Node en esta máquina.
2. `npm view hidalgo-design-token-system version` — confirma que el paquete existe y en qué registro. Si falla: revisar si hay `.npmrc` con registro privado; si sigue sin resolver, usar el **fallback** (paleta guinda como CSS vars) y anotarlo en `frontend/README.md`.
3. Si resuelve: `npm view hidalgo-design-token-system` para ver `main`/`exports`/`files` — determina cómo se integra (preset de Tailwind, `@import` de CSS, o JSON).

**Files:**
- Create: todo `frontend/` (ver "File Structure")
- Create: `scripts/check-frontend.sh`
- Modify: `CLAUDE.md` (sección "Frontend" + flujo dev)

- [ ] **Step 1: Andamiaje**

```bash
cd frontend
npm create vite@latest . -- --template react-ts   # responder: no sobreescribir si pregunta
npm i
npm i -D tailwindcss postcss autoprefixer vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
npx tailwindcss init -p
npx shadcn@latest init          # preset: Vite; baseColor: neutral; CSS variables: yes
npx shadcn@latest add button card input select progress tabs dialog sonner
npm i hidalgo-design-token-system@latest   # o fallback
```

- [ ] **Step 2: `vite.config.ts`** — plugin React + proxy de dev + salida a `dist`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "/app/",                       // Task 11 lo cambia a "/"
  build: { outDir: "dist" },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
```

- [ ] **Step 3: Integrar los tokens** — según lo visto en el preludio: si es preset de Tailwind → `tailwind.config.ts` `presets: [require("hidalgo-design-token-system/tailwind")]`; si es CSS → `@import "hidalgo-design-token-system/tokens.css";` al inicio de `src/index.css`, mapeando sus variables a las que espera shadcn (`--background`, `--foreground`, `--primary`, `--radius`, …). Fallback: definir esas variables con la guinda actual.

- [ ] **Step 4: `vitest.config.ts` + `src/test/setup.ts`**

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["src/test/setup.ts"], globals: true },
});
```
```ts
// src/test/setup.ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 5: `App.tsx` mínimo con un `Button`** para probar la cadena completa:

```tsx
import { Button } from "@/components/ui/button";
export default function App() {
  return <Button>Compilador GPM</Button>;
}
```

- [ ] **Step 6: `scripts/check-frontend.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
npx tsc --noEmit
npx vitest run
npm run build
```
`chmod +x scripts/check-frontend.sh`

- [ ] **Step 7: Correr** — `bash scripts/check-frontend.sh` → todo verde, `frontend/dist/index.html` generado.

- [ ] **Step 8: Verificar la integración con FastAPI** — `.venv/bin/pytest tests/test_web.py -k dist -v` (los tests de Task 6 ahora corren contra un `dist/` real si `GPMC_FRONTEND_DIST` apunta ahí; o dejar los tests con el `dist` falso — ambos deben pasar).

- [ ] **Step 9: `CLAUDE.md`** — añadir sección:

```markdown
## Frontend (SPA React) — SP1 en curso

`frontend/` es un proyecto Vite + React + TS + Tailwind + shadcn/ui. El diseño
sale de `hidalgo-design-token-system`. Node/npm **solo en build** (`npm run build`
-> `frontend/dist/`, que NO se comitea). FastAPI sirve `dist/` (hoy en `/app`,
tras el corte en `/`). Desarrollo: `cd frontend && npm run dev` (:5173, proxy /api
a :8000) + `gpmc servir` (:8000). Chequeo: `bash scripts/check-frontend.sh`.
```

- [ ] **Step 10: Commit**

```bash
git add frontend scripts/check-frontend.sh CLAUDE.md .gitignore
git commit -m "feat(frontend): scaffold Vite+React+TS+Tailwind+shadcn + hidalgo-design-token-system

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 8: Cliente tipado de `/api/v1` (`frontend/src/lib/`)

**Files:**
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/api.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Hueco` (`nivel, codigo, ubicacion, mensaje, propuesta`), `Estimacion`, `EstadoExpediente` (`sid, manifiesto, huecos: Hueco[], estimacion, problemas: string[], tieneVistas`), `Resolucion` (`tipo: "mmd03"|"meta01"|"meta02"|"api03"`, `ubicacion, valor`).
  - `api.ts`: `crearExpediente(files) -> Promise<EstadoExpediente>` (lanza `ErrorApi` con `{status, error, archivos?}` en 4xx), `leerExpediente(sid)`, `resolver(sid, Resolucion[])`, `reconocer(sid, codigo, ubicacion)`, `urlGpm(sid, modo)`, `urlManifiesto(sid)`.

- [ ] **Step 1: Prueba que falla** — `api.test.ts`

```ts
import { describe, it, expect, vi } from "vitest";
import { crearExpediente, ErrorApi } from "./api";

describe("crearExpediente", () => {
  it("devuelve el estado en 201", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true, status: 201,
      json: async () => ({ sid: "a".repeat(16), manifiesto: {}, huecos: [],
        estimacion: {}, problemas: [], tiene_vistas: false }),
    }));
    const est = await crearExpediente(new FormData());
    expect(est.sid).toHaveLength(16);
  });

  it("lanza ErrorApi con los nombres en 413", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 413, json: async () => ({ error: "grande", archivos: ["x.md"] }),
    }));
    await expect(crearExpediente(new FormData())).rejects.toMatchObject(
      { status: 413, archivos: ["x.md"] });
  });
});
```

- [ ] **Step 2: Ver que falla** — `Cannot find module './api'`.

- [ ] **Step 3: Implementar `types.ts` y `api.ts`** — `fetch` relativo (`/api/v1/...`, mismo origen). `EstadoExpediente` mapea `tiene_vistas`→`tieneVistas` en el borde. `ErrorApi extends Error` con `status`, `archivos?`.

- [ ] **Step 4: Correr** — `cd frontend && npx vitest run src/lib` → PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib
git commit -m "feat(frontend): cliente tipado de /api/v1

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 9: Pantalla de carga de insumos (`CargaInsumos.tsx`)

**Files:**
- Create: `frontend/src/features/carga/CargaInsumos.tsx`, `frontend/src/features/carga/CargaInsumos.test.tsx`
- Modify: `frontend/src/App.tsx` (ruta `/` de la SPA → `CargaInsumos`)

**Interfaces:**
- Consumes: `crearExpediente`, `ErrorApi` de Task 8; componentes `Card`, `Button` de shadcn.
- Produces: `<CargaInsumos onListo={(est: EstadoExpediente) => void} />` — 4 zonas de arrastre (as_is, to_be, diccionario obligatorio, vistas). Drop real (asigna el archivo, muestra el nombre). Botón "Extraer" deshabilitado sin diccionario. En `ErrorApi` 413 → alerta roja con `err.archivos`.

- [ ] **Step 1: Prueba que falla** — `CargaInsumos.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import CargaInsumos from "./CargaInsumos";

vi.mock("@/lib/api", () => ({
  crearExpediente: vi.fn(),
  ErrorApi: class extends Error { status = 0; archivos?: string[]; },
}));

it("el boton Extraer se habilita al elegir un Diccionario", async () => {
  render(<CargaInsumos onListo={() => {}} />);
  const btn = screen.getByRole("button", { name: /extraer/i });
  expect(btn).toBeDisabled();
  const input = screen.getByLabelText(/diccionario/i);
  await userEvent.upload(input, new File(["# x"], "dd.md", { type: "text/markdown" }));
  expect(btn).toBeEnabled();
});

it("muestra el error de tamano cuando la API lanza 413", async () => {
  const { crearExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("grande"); e.status = 413; e.archivos = ["enorme.md"];
  (crearExpediente as any).mockRejectedValue(e);
  render(<CargaInsumos onListo={() => {}} />);
  const input = screen.getByLabelText(/diccionario/i);
  await userEvent.upload(input, new File(["# x"], "dd.md", { type: "text/markdown" }));
  await userEvent.click(screen.getByRole("button", { name: /extraer/i }));
  expect(await screen.findByText(/enorme\.md/)).toBeInTheDocument();
  expect(screen.getByText(/10 MB/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver que falla** — módulo no existe.

- [ ] **Step 3: Implementar** — `useState` para los 4 `File | null`; zonas con `onDragOver`/`onDrop` (preventDefault, tomar `e.dataTransfer.files[0]`); `<input type="file">` accesible con `aria-label`/`<label>`. Submit → `FormData` con los presentes → `crearExpediente` → `onListo(est)`. `catch (e) { if (e instanceof ErrorApi) setError(...) }`.

- [ ] **Step 4: Correr** — `npx vitest run src/features/carga` → PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/carga frontend/src/App.tsx
git commit -m "feat(frontend): pantalla de carga de insumos (drag-drop real, error de tamano)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 10: Wizard de resolución de huecos (`WizardHuecos.tsx`)

**Files:**
- Create: `frontend/src/features/huecos/WizardHuecos.tsx`, `TarjetaHueco.tsx`, `WizardHuecos.test.tsx`
- Create: `frontend/src/features/huecos/controles/ControlActor.tsx`, `ControlTexto.tsx`, `ControlCampoPadre.tsx`, `BotonReconocer.tsx`
- Modify: `frontend/src/App.tsx` (ruta `/revisar/:sid`)

**Interfaces:**
- Consumes: `EstadoExpediente`, `Hueco` de Task 8; `resolver`, `reconocer`, `leerExpediente`, `urlGpm`, `urlManifiesto` de Task 8; `Card`, `Button`, `Progress`, `Select`, `Input` de shadcn.
- Produces: `<WizardHuecos estado={EstadoExpediente} onEstado={(e)=>void} />` — una `Card` por hueco, `Progress` = resueltos/total. Controles por código:
  - `MMD-03` → `ControlActor` (`Select` con `estado.manifiesto.actores`)
  - `META-01`/`META-02` → `ControlTexto` (`Input`)
  - `API-03` → `ControlCampoPadre` (`Select` con los campos de las pantallas)
  - resto `falta_dato` → `BotonReconocer`
  Cada control, al confirmar, llama `resolver(sid, [{tipo, ubicacion, valor}])` o `reconocer(...)`, y `onEstado(nuevoEstado)` con la respuesta. **Sin recarga.** Al llegar a `bloquean = 0` (ningún `bloqueante` y ningún `falta_dato` sin reconocer) muestra los enlaces de descarga (`urlGpm`, `urlManifiesto`) y los enlaces a `/simulador/{sid}` y `/aprobacion/{sid}` (HTML viejo, `target` en la misma pestaña).

- [ ] **Step 1: Prueba que falla** — `WizardHuecos.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import WizardHuecos from "./WizardHuecos";

vi.mock("@/lib/api", () => ({
  resolver: vi.fn(), reconocer: vi.fn(),
  urlGpm: () => "/api/v1/x/gpm", urlManifiesto: () => "/api/v1/x/manifiesto",
}));

const estado = {
  sid: "a".repeat(16),
  manifiesto: { actores: [{ id: "ciudadano", nombre: "Ciudadano" }], pantallas: [], flujo: { tareas: [] } },
  huecos: [
    { nivel: "falta_dato", codigo: "META-01", ubicacion: "metadatos", mensaje: "falta el tiempo", propuesta: null },
    { nivel: "por_confirmar", codigo: "META-05", ubicacion: "metadatos", mensaje: "sin homoclave", propuesta: null },
  ],
  estimacion: {}, problemas: [], tieneVistas: false,
};

it("una tarjeta por hueco y barra de progreso", () => {
  render(<WizardHuecos estado={estado as any} onEstado={() => {}} />);
  expect(screen.getByText(/falta el tiempo/)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});

it("META-01 se resuelve por la API y sube el estado, sin recargar", async () => {
  const { resolver } = await import("@/lib/api");
  (resolver as any).mockResolvedValue({ ...estado, huecos: [estado.huecos[1]] });
  const onEstado = vi.fn();
  render(<WizardHuecos estado={estado as any} onEstado={onEstado} />);
  await userEvent.type(screen.getByLabelText(/tiempo/i), "5 dias habiles");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolver).toHaveBeenCalledWith("a".repeat(16),
    [{ tipo: "meta01", ubicacion: "metadatos", valor: "5 dias habiles" }]);
  expect(onEstado).toHaveBeenCalled();
});
```

- [ ] **Step 2: Ver que falla** — módulo no existe.

- [ ] **Step 3: Implementar** los controles y el wizard. `TarjetaHueco` recibe `hueco` + `manifiesto` + `onResuelto` y elige el control por `hueco.codigo`. `Progress value={100 * resueltos / total}`.

- [ ] **Step 4: Correr** — `npx vitest run src/features/huecos` → PASS. Luego `bash scripts/check-frontend.sh` → todo verde.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos frontend/src/App.tsx
git commit -m "feat(frontend): wizard de resolucion de huecos (una card por hueco, sin recarga)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
```

---

## Task 11: El corte — la SPA toma `/` y `/revisar/*`

**Files:**
- Modify: `src/gpmc/web/app.py` (quitar `portada` y `revisar`; mover el static de `/app` a `/`)
- Modify: `frontend/vite.config.ts` (`base: "/"`)
- Modify: `despliegue/instalar-servicio.sh`, `despliegue/LEEME.md`, `Abrir Compilador GPM.command`
- Modify: `CLAUDE.md`
- Test: `tests/test_web.py`, `tests/test_api.py`

**Interfaces:**
- Produces: `GET /` y `GET /revisar/{sid}` sirven `dist/index.html` (SPA). `GET /simulador/{sid}`, `/aprobacion/{sid}`, `/historial`, `/vistas/{sid}`, `/descargar-plantilla`, `/descargar/{sid}/{que}` **siguen** en HTML. `plantillas.portada` y `plantillas.revision` quedan sin uso (los borra SP3).

- [ ] **Step 1: Prueba que falla / se actualiza**

```python
def test_la_raiz_sirve_la_spa_no_html_viejo(monkeypatch, tmp_path):
    dist = tmp_path / "dist"; dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    assert 'id=root' in c.get("/").text
    assert 'id=root' in c.get("/revisar/" + "a" * 16).text     # fallback SPA
    assert c.get("/historial").status_code == 200               # HTML viejo sigue
```

Y **borrar/ajustar** los tests de `test_web.py` que dependían del HTML de `portada`/`revisar` (`test_la_portada_pide_los_tres_insumos`, `test_el_paso_de_revision_agrupa_huecos_por_nivel`, `test_revision_enlaza_al_simulador...`, `test_subir_vistas...`, `test_la_revision_manda_el_reconocer...`, `test_el_boton_guardar...`, `test_descargar_gpm_bloqueado...`, `test_reconocer_los_huecos...`, `test_la_revision_ofrece_configurar...`, `test_la_portada_intercepta_el_drop...`) — su cobertura se movió a `test_api.py` y a los tests de Vitest. Mantener los de `/simulador`, `/aprobacion`, `/historial`, `/vistas`, `/descargar`, cabeceras, purga.

- [ ] **Step 2: Ver el estado** — `.venv/bin/pytest tests/test_web.py -q` mostrará los fallos de los tests a borrar; borrarlos uno por uno confirmando que su equivalente existe en `test_api.py`.

- [ ] **Step 3: Implementar en `app.py`** — quitar `@app.get("/", response_class=HTMLResponse) def portada()` y `@app.get("/revisar/{sid}", ...) def revisar(...)`. Cambiar el handler de estáticos de `@app.get("/app/{ruta:path}")` a `@app.get("/{ruta:path}")` **al final** de todas las rutas (para que `/api`, `/simulador`, etc. ganen precedencia), con una lista de prefijos que NO son SPA (`api`, `simulador`, `aprobacion`, `historial`, `vistas`, `descargar`, `descargar-plantilla`) → esos dejan pasar (`raise HTTPException(404)` no; simplemente no registrar el catch-all para ellos — FastAPI resuelve por orden de declaración, así que declarar el catch-all al final basta, pero un `path` como `historial` casaría con `{ruta:path}`; solución: en el catch-all, si `ruta.split("/")[0]` está en el set de prefijos HTML → `404` para que no lo intercepte... **no**: mejor, el catch-all sirve `index.html` para cualquier ruta que no sea un archivo real de `dist/` NI empiece por uno de esos prefijos; si empieza por un prefijo conocido y llegó aquí, es un 404 legítimo → devolver `PlainTextResponse(status_code=404)`).

- [ ] **Step 4: `vite.config.ts`** — `base: "/"`. Rebuild: `bash scripts/check-frontend.sh`.

- [ ] **Step 5: Despliegue** — en `despliegue/instalar-servicio.sh`, antes de arrancar uvicorn, añadir:

```bash
if command -v npm >/dev/null 2>&1; then
  ( cd "$RAIZ/frontend" && npm ci && npm run build )
else
  echo "AVISO: npm no está; se sirve el frontend/dist/ existente (o 503 si no hay)."
fi
```

Igual en `Abrir Compilador GPM.command`. En `despliegue/LEEME.md`, documentar el paso de build y `GPMC_FRONTEND_DIST`.

- [ ] **Step 6: `CLAUDE.md`** — actualizar la sección Frontend: la SPA ya está en `/`; `/simulador` y `/aprobacion` siguen en HTML hasta SP3; `plantillas.portada`/`revision` quedan muertos.

- [ ] **Step 7: Correr TODO**

Run: `.venv/bin/pytest -q` (con `GPMC_FRONTEND_DIST` apuntando a un `dist/` real o al falso de los tests) + `bash scripts/check-frontend.sh`.
Expected: Python verde (con el nuevo conteo, sin los tests borrados), frontend verde.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(web): la SPA React toma / y /revisar; se quitan los handlers portada y revisar

SP1 completo: carga de insumos y wizard de huecos en React contra /api/v1.
/simulador, /aprobacion, /historial, /vistas, /descargar siguen en HTML
(SP3 los migra). plantillas.portada/revision quedan sin uso.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP"
git push origin main
```

---

## Self-Review

**Spec coverage:**
- §3 Arquitectura y rutas → Tasks 1, 6, 11. ✔
- §4 Superficie REST (7 endpoints) → Tasks 3 (2), 4 (2), 5 (2). El 7º (`simulador-datos`/`aprobacion-datos`) es explícitamente SP3 en el spec — no va aquí. ✔
- §5 Modelo de sesión (disco fuente de verdad) → Task 1 (helpers) + Tasks 3-5 los usan. ✔
- §6 Build/stack/tokens → Task 7. ✔
- §7 Orden de migración (5 pasos) → Task 1-2 (paso 1), Task 3-5 (paso 1), Task 6-7 (paso 2), Task 9 (paso 3), Task 10 (paso 4), Task 11 (paso 5). ✔
- §8 Pruebas → cada task tiene `pytest`/`vitest`; `scripts/check-frontend.sh` = `tsc`+`vite build`+`vitest`. Playwright: fuera (opcional en el spec). ✔
- §9 Riesgos → corte de `/` (Task 11 con fallback SPA); shadcn+Vite (Task 7 step 5); `dist/` ausente (Task 6, `503`); doble fuente de verdad (Tasks 4-5 devuelven estado completo, React reemplaza); regresión HTML (solo Task 11 toca `app.py` de forma destructiva, y solo esos dos handlers); proxy de dev enmascarando (Task 6 prueba el `dist/` real); `vite build`/`tsc` rotos (`scripts/check-frontend.sh` en cada task de frontend); token package (Task 7 preludio). ✔

**Placeholder scan:** los `...` en Task 5 Step 1 y Task 9 (mock) son fixtures a reusar de archivos nombrados (`_exp_limpio` de `test_cli.py`) — el ejecutor los tiene a la vista. Sin "TBD"/"implementar después".

**Type consistency:** `EstadoExpediente` (backend Pydantic, Task 3) ↔ `EstadoExpediente` (TS, Task 8) — el TS mapea `tiene_vistas`→`tieneVistas` en `api.ts`, documentado. `Resolucion.tipo` usa los mismos literales (`mmd03|meta01|meta02|api03`) en Task 4 (backend) y Task 8/10 (frontend). `HuecoOut` (Task 2) ↔ `Hueco` TS (Task 8): mismos 5 campos.
