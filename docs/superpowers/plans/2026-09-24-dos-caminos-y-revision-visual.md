# Dos caminos de entrada y revisión visual — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un inicio con dos caminos (expediente completo / solo AS-IS), migas de pan de máximo tres tramos, el Diccionario propuesto como vista por pantallas, el TO-BE como diagrama grande con zoom y pantalla completa, y ese mismo diagrama en la revisión de huecos.

**Architecture:** Backend: dos rutas pequeñas (`GET /capacidades`, `GET /expedientes/{sid}/insumos/to_be`), `insumos` en `GeneradosOut` y `vista` en el `Documento` del Diccionario (calculada en `agentes/fase3.py` con el manifiesto que ya se extrae). SPA: `lib/rutas.ts` (funciones puras de ruta y migas), `MigasDePan`, `Inicio`, `CargaAsIs`; `App` elige pantalla por `pathname` como hoy; `DiagramaMermaid` crece con zoom y pantalla completa; `Propuestas` pasa a un documento por pantalla.

**Tech Stack:** Python 3.9 (`Optional[X]`), FastAPI, pydantic; React + TS + Tailwind v4 + shadcn (`Card`, `Button`), vitest + testing-library. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-09-24-dos-caminos-y-revision-visual-design.md`

## Global Constraints

- Python ≥ 3.9: `Optional[X]`, nunca `X | None`.
- Identificadores en español sin acentos; textos al usuario con acentos.
- `agentes/` no escribe en la sesión; `nucleo/` no importa `agentes/`.
- **Sin dependencias nuevas** (ni enrutador ni librería de zoom).
- En la SPA solo tarjetas: ninguna `<table>`.
- Migas de pan: máximo tres tramos; solo «Inicio» es enlace (ver ruling abajo).
- Suite en verde antes de cada commit: `.venv/bin/pytest -q` y `bash scripts/check-frontend.sh`.
- No se modifica `CLAUDE.md` (nota propuesta al final, sin aplicar). No se sobrescribe ningún `.gpm`.

**Precisión respecto del spec (ruling del plan):** el spec dice «solo los tramos anteriores son enlaces». El único tramo anterior que lleva a algún lado útil es «Inicio»: «Expediente completo» desde la revisión abriría una carga nueva y perdería la sesión en pantalla, y «Solo AS-IS» igual. Se enlaza solo «Inicio».

## Review Focus

1. **Abrir `/expediente` o `/desde-as-is` directo** (marcador, recarga) → monta su pantalla con sus migas, no el Inicio (Task 4).
2. **`/revisar/{sid}` de una sesión de carpeta con `GET /generados` caído por red** → migas «Inicio › Revisión», sin error visible ni pantalla rota (Task 4).
3. **`GET /capacidades` falla** → la tarjeta «Solo tengo el AS-IS» sale activa; el error, si lo hay, llega al subir (Task 3).
4. **Diccionario propuesto que el extractor no lee** (`vista: []`) → se abre el texto directamente con el aviso «El compilador no pudo leer pantallas…» (Task 6).
5. **422 del extractor con los dos documentos ya resueltos** → la pantalla muestra las dos zonas de carga (Diccionario y TO-BE), no solo la del paso actual (Task 6).

---

### Task 1: Backend — `GET /capacidades`, `GET /expedientes/{sid}/insumos/to_be`, `insumos` en `GeneradosOut`

**Files:**
- Modify: `src/gpmc/web/api_fase3.py` (capacidades, `insumos` en la salida)
- Modify: `src/gpmc/web/api.py` (ruta `insumos/to_be`, junto a `leer_adjunto`)
- Test: `tests/test_api.py`, `tests/test_web.py`

**Interfaces:**
- Produces: `GET /api/v1/capacidades` → `{"proponer": bool, "motivo": Optional[str]}`; `GET /api/v1/expedientes/{sid}/insumos/to_be` → `text/markdown` o 404; `GeneradosOut.insumos: dict` = `{"diccionario": bool, "tobe": bool}` en `GET /generados`, `/decision` y `/subir` cuando devuelven `GeneradosOut`.

- [ ] **Step 1: Pruebas que fallan**

```python
# tests/test_api.py (añadir)
def test_capacidades_dice_si_se_puede_proponer(tmp_path):
    c = _cli_fase3(tmp_path, [])
    assert c.get("/api/v1/capacidades").json() == {"proponer": True, "motivo": None}
    c = _cli_fase3(tmp_path, [], entorno=_ENT_GEMINI)
    r = c.get("/api/v1/capacidades").json()
    assert r["proponer"] is False and "licencia" in r["motivo"]


def test_capacidades_sin_proveedor(tmp_path):
    r = _cli(tmp_path).get("/api/v1/capacidades").json()
    assert r["proponer"] is False and r["motivo"]


def test_insumo_to_be_se_lee_como_texto(tmp_path):
    from tests.test_extractor_expediente import _DICC_RAMA, _TOBE_RAMA
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC_RAMA.encode("utf-8"), "text/markdown"),
        "to_be": ("tb.md", _TOBE_RAMA.encode("utf-8"), "text/markdown")}).json()["sid"]
    r = c.get(f"/api/v1/expedientes/{sid}/insumos/to_be")
    assert r.status_code == 200 and r.text == _TOBE_RAMA
    assert r.headers["content-type"].startswith("text/markdown")


def test_insumo_to_be_404_sin_to_be_o_sin_sesion(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files={
        "diccionario": ("dd.md", _DICC.encode("utf-8"), "text/markdown")}).json()["sid"]
    assert c.get(f"/api/v1/expedientes/{sid}/insumos/to_be").status_code == 404
    assert c.get("/api/v1/expedientes/0123456789abcdef/insumos/to_be").status_code == 404
    assert c.get("/api/v1/expedientes/..%2F..%2Fetc/insumos/to_be").status_code == 404


def test_generados_dice_que_insumos_ya_existen(tmp_path):
    c, sid = _sesion_lista(tmp_path)
    assert c.get(f"/api/v1/expedientes/{sid}/generados").json()["insumos"] == {
        "diccionario": False, "tobe": False}
    r = _decidir(c, sid, "diccionario", "aceptada")
    assert r.json()["insumos"] == {"diccionario": True, "tobe": False}
```

```python
# tests/test_web.py (añadir)
def test_las_rutas_de_los_dos_caminos_sirven_la_spa(monkeypatch, tmp_path):
    dist = tmp_path / "dist"; dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    monkeypatch.setenv("GPMC_FRONTEND_DIST", str(dist))
    from gpmc.web.app import crear_app
    from fastapi.testclient import TestClient
    c = TestClient(crear_app(almacen=tmp_path))
    assert 'id=root' in c.get("/expediente").text
    assert 'id=root' in c.get("/desde-as-is").text
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `.venv/bin/pytest tests/test_api.py tests/test_web.py -q -k "capacidades or insumo or insumos or dos_caminos"`
Expected: FAIL (404 en las rutas; `KeyError: 'insumos'`). `test_las_rutas_de_los_dos_caminos_sirven_la_spa` puede pasar ya (la catch-all existe): es una guarda, se deja.

- [ ] **Step 3: Implementar en `api_fase3.py`**

En `GeneradosOut` añadir `insumos: dict = {}`. Dentro de `crear_router_fase3`, antes de `leer_generados`:

```python
    def _salida(carpeta: Path, d: dict) -> GeneradosOut:
        """Lo que ve la SPA: `generados.json` mas que insumos ya existen. Con
        eso decide el paso (Diccionario o TO-BE) aunque se recargue la pagina:
        `declinada` sola no dice si ya se subio el propio."""
        return GeneradosOut(**{**d, "insumos": {doc: _resuelto(carpeta, doc) for doc in CLAVE_INSUMO}})

    @r.get("/capacidades")
    async def leer_capacidades():
        """Si este servidor puede proponer desde el AS-IS. La SPA lo pregunta
        antes de que nadie suba nada: enterarse del candado despues de subir
        el AS-IS era la peor experiencia posible."""
        motivo = _motivo_para_no_generar()
        return {"proponer": motivo is None, "motivo": motivo}
```

Mover la definición de `_resuelto` (hoy más abajo) arriba de `_salida`. Sustituir `return GeneradosOut(**d)` por `return _salida(carpeta, d)` en `leer_generados` y en `_si_ambos_resueltos`.

- [ ] **Step 4: Implementar en `api.py`** (después de `leer_adjunto`)

```python
    @r.get("/expedientes/{sid}/insumos/to_be")
    async def leer_insumo_to_be(sid: str):
        """El texto del TO-BE de la sesion, para dibujarlo en la revision de
        huecos. Solo `to_be` (YAGNI); el nombre de la ruta deja sitio a los otros."""
        carpeta = carpeta_de(raiz, sid)
        ruta = carpeta / INSUMOS["to_be"] if carpeta else None
        if ruta is None or not ruta.is_file():
            return JSONResponse(status_code=404, content={"error": "sin TO-BE"})
        return Response(ruta.read_text(encoding="utf-8", errors="replace"),
                        media_type="text/markdown; charset=utf-8")
```

- [ ] **Step 5: Correr la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/web/api_fase3.py src/gpmc/web/api.py tests/test_api.py tests/test_web.py
git commit -m "feat(web): GET /capacidades, GET /insumos/to_be e insumos en GeneradosOut"
```

---

### Task 2: Backend — `vista` del Diccionario propuesto

**Files:**
- Modify: `src/gpmc/agentes/fase3.py` (`Documento.vista`, `vista_de`, `_ronda_de_mejora` devuelve el manifiesto elegido)
- Test: `tests/test_fase3.py`

**Interfaces:**
- Produces: `fase3.vista_de(m: Optional[Manifiesto]) -> list[dict]` con `{"id", "nombre", "actor", "campos": [{"etiqueta", "tipo", "obligatorio", "opciones": list[str], "condicion": Optional[str]}]}`; `Documento.vista: list = []`; `_ronda_de_mejora(...) -> (elegido, huecos, manifiesto)`.

- [ ] **Step 1: Pruebas que fallan**

```python
# tests/test_fase3.py (añadir)
def test_el_diccionario_generado_lleva_su_vista_por_pantallas(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_OK), _json("tobe", _TOBE_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "4" * 16, mejorar=False)
    v = g.diccionario.vista
    assert [(p["nombre"], p["actor"]) for p in v] == [("Solicitud", "Ciudadano"), ("Revisión", "Funcionario")]
    curp = v[0]["campos"][0]
    assert curp == {"etiqueta": "CURP", "tipo": "text", "obligatorio": True, "opciones": [], "condicion": None}
    dictamen = v[1]["campos"][0]
    assert dictamen["tipo"] == "select" and dictamen["opciones"] == ["Aprobado", "Rechazado"]
    assert g.tobe.vista == []


def test_la_vista_escribe_la_condicion_en_palabras():
    from gpmc.agentes.fase3 import vista_de
    from gpmc.nucleo.manifiesto import Condicion
    m = _manifiesto([
        {"nombre": "tipo", "etiqueta": "Tipo de persona", "tipo": "select",
         "catalogo": [{"etiqueta": "Moral", "valor": "moral"}]},
        {"nombre": "poder", "etiqueta": "Poder notarial", "tipo": "file",
         "condicion_visible": Condicion(campo="tipo", igual="moral")}])
    campos = vista_de(m)[0]["campos"]
    assert campos[1]["condicion"] == "«Tipo de persona» es «Moral»"
    assert vista_de(None) == []


def test_sin_pantallas_la_vista_es_vacia_y_generar_no_falla(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_ROTO), _json("tobe", _TOBE_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "5" * 16, mejorar=False)
    assert g.estado == "listo" and g.diccionario.vista == []


def test_la_vista_es_la_de_la_ronda_elegida(tmp_path):
    from gpmc.agentes.fase3 import generar
    from gpmc.agentes.proveedor import ProveedorFalso
    prov = ProveedorFalso([_json("diccionario", _DICC_ROTO), _json("tobe", _TOBE_OK),
                           _json("diccionario", _DICC_OK)])
    g = generar(_ASIS_INLINE, prov, tmp_path, "6" * 16)
    assert g.diccionario.ronda == 2 and len(g.diccionario.vista) == 2
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `.venv/bin/pytest tests/test_fase3.py -q -k vista`
Expected: FAIL (`AttributeError: 'Documento' object has no attribute 'vista'` / `ImportError: vista_de`)

- [ ] **Step 3: Implementar**

En `Documento` añadir `vista: list = []` con el comentario «Pantallas y campos ya leidos por el extractor (solo el Diccionario). La SPA los pinta como tarjetas; el Markdown sigue a un clic.» Y en el módulo:

```python
def _condicion_en_palabras(cond, etiquetas: dict, opciones: dict) -> Optional[str]:
    if cond is None:
        return None
    def trozo(c):
        verbo = "es" if c.operador == "==" else "no es"
        valor = opciones.get((c.campo, c.igual), c.igual)
        return f"«{etiquetas.get(c.campo, c.campo)}» {verbo} «{valor}»"
    return " y ".join([trozo(cond), *(trozo(c) for c in cond.y)])


def vista_de(m) -> list:
    """Las pantallas del manifiesto como las ve una persona: actor con su
    nombre, campo con su etiqueta, opciones por etiqueta y la condicion en
    palabras. Sin manifiesto (el extractor no leyo pantallas), lista vacia."""
    if m is None:
        return []
    actores = {a.id: a.nombre for a in m.actores}
    campos = [c for p in m.pantallas for c in p.campos]
    etiquetas = {c.nombre: (c.etiqueta or c.nombre) for c in campos}
    opciones = {(c.nombre, o.valor): o.etiqueta for c in campos for o in c.catalogo}
    return [{
        "id": p.id, "nombre": p.nombre, "actor": actores.get(p.actor, p.actor),
        "campos": [{"etiqueta": c.etiqueta or c.nombre, "tipo": c.tipo,
                    "obligatorio": c.obligatorio,
                    "opciones": [o.etiqueta for o in c.catalogo],
                    "condicion": _condicion_en_palabras(c.condicion_visible, etiquetas, opciones)}
                   for c in p.campos],
    } for p in m.pantallas]
```

`_ronda_de_mejora` devuelve también el manifiesto de la pareja elegida: las tres salidas tempranas `return elegido, huecos` pasan a `return elegido, huecos, m_1`; `return final, huecos_2` pasa a `return final, huecos_2, m_2`; y la última usa `m_f, huecos_f = extraer_borradores(...)` y `return final, huecos_f, m_f`. En `_generar`:

```python
    m_final = m_1
    if mejorar:
        elegido, huecos, m_final = _ronda_de_mejora(as_is, proveedor, raiz, sid, elegido, huecos, m_1)
    ...
    docs["diccionario"].vista = vista_de(m_final)
```

(la asignación va después del bucle que construye `docs`, antes del `return`).

- [ ] **Step 4: Correr la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/agentes/fase3.py tests/test_fase3.py
git commit -m "feat(agentes): el Diccionario propuesto lleva su vista por pantallas"
```

---

### Task 3: SPA — rutas, migas, `Inicio` y cliente (`capacidades`, `leerToBe`)

**Files:**
- Create: `frontend/src/lib/rutas.ts`, `frontend/src/lib/rutas.test.ts`
- Create: `frontend/src/components/MigasDePan.tsx`, `frontend/src/components/MigasDePan.test.tsx`
- Create: `frontend/src/features/inicio/Inicio.tsx`, `frontend/src/features/inicio/Inicio.test.tsx`
- Modify: `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `frontend/src/lib/api.fase3.test.ts`

**Interfaces:**
- Produces (rutas.ts):
  ```ts
  export type Camino = "carpeta" | "as_is";
  export type Ruta =
    | { tipo: "inicio" } | { tipo: "expediente" } | { tipo: "desde_as_is" }
    | { tipo: "revisar"; sid: string } | { tipo: "catalogos" } | { tipo: "historial" }
    | { tipo: "tablero" };
  export function leerRuta(pathname: string): Ruta;          // desconocida -> inicio
  export type Pantalla = "inicio" | "carga" | "diccionario" | "tobe" | "revision";
  export type Tramo = { etiqueta: string; href?: string };
  export function migas(pantalla: Pantalla, camino: Camino | null): Tramo[];
  ```
- Produces (componentes): `MigasDePan({ tramos }: { tramos: Tramo[] })`; `Inicio()`.
- Produces (api.ts): `leerCapacidades(): Promise<Capacidades>`, `leerToBe(sid): Promise<string>`; (types.ts) `Capacidades = { proponer: boolean; motivo: string | null }`, `PantallaVista`, `CampoVista`, `DocumentoGenerado.vista?: PantallaVista[]`, `GeneradosOut.insumos?: { diccionario: boolean; tobe: boolean }`.

- [ ] **Step 1: Pruebas que fallan**

```ts
// frontend/src/lib/rutas.test.ts
import { describe, expect, it } from "vitest";

import { leerRuta, migas } from "./rutas";

describe("leerRuta", () => {
  it("reconoce cada pantalla y cae a inicio con lo desconocido", () => {
    expect(leerRuta("/")).toEqual({ tipo: "inicio" });
    expect(leerRuta("/expediente")).toEqual({ tipo: "expediente" });
    expect(leerRuta("/desde-as-is")).toEqual({ tipo: "desde_as_is" });
    expect(leerRuta(`/revisar/${"a".repeat(16)}`)).toEqual({ tipo: "revisar", sid: "a".repeat(16) });
    expect(leerRuta("/revisar/xyz")).toEqual({ tipo: "inicio" });
    expect(leerRuta("/tablero")).toEqual({ tipo: "tablero" });
    expect(leerRuta("/cualquier-cosa")).toEqual({ tipo: "inicio" });
  });
});

describe("migas", () => {
  const etiquetas = (t: { etiqueta: string }[]) => t.map((x) => x.etiqueta);
  it("tres tramos como maximo y solo Inicio es enlace", () => {
    const casos = [
      migas("inicio", null), migas("carga", "carpeta"), migas("carga", "as_is"),
      migas("diccionario", "as_is"), migas("tobe", "as_is"),
      migas("revision", "carpeta"), migas("revision", "as_is"), migas("revision", null),
    ];
    for (const c of casos) {
      expect(c.length).toBeLessThanOrEqual(3);
      c.slice(1).forEach((t) => expect(t.href).toBeUndefined());
    }
    expect(migas("inicio", null)).toEqual([{ etiqueta: "Inicio" }]);
    expect(migas("carga", "carpeta")[0]).toEqual({ etiqueta: "Inicio", href: "/" });
  });
  it("dice el camino y el paso", () => {
    expect(etiquetas(migas("carga", "carpeta"))).toEqual(["Inicio", "Expediente completo"]);
    expect(etiquetas(migas("carga", "as_is"))).toEqual(["Inicio", "Solo AS-IS"]);
    expect(etiquetas(migas("diccionario", "as_is"))).toEqual(["Inicio", "Solo AS-IS", "Diccionario (1 de 2)"]);
    expect(etiquetas(migas("tobe", "as_is"))).toEqual(["Inicio", "Solo AS-IS", "TO-BE (2 de 2)"]);
    expect(etiquetas(migas("revision", "carpeta"))).toEqual(["Inicio", "Expediente completo", "Revisión"]);
    expect(etiquetas(migas("revision", null))).toEqual(["Inicio", "Revisión"]);
  });
});
```

```tsx
// frontend/src/components/MigasDePan.test.tsx
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import MigasDePan from "./MigasDePan";

it("pinta los tramos, enlaza solo los que tienen href y marca el actual", () => {
  render(<MigasDePan tramos={[{ etiqueta: "Inicio", href: "/" }, { etiqueta: "Solo AS-IS" },
    { etiqueta: "Diccionario (1 de 2)" }]} />);
  const nav = screen.getByRole("navigation", { name: /migas de pan/i });
  expect(nav).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/");
  expect(screen.queryByRole("link", { name: "Solo AS-IS" })).not.toBeInTheDocument();
  expect(screen.getByText("Diccionario (1 de 2)")).toHaveAttribute("aria-current", "page");
});
```

```tsx
// frontend/src/features/inicio/Inicio.test.tsx
import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import Inicio from "./Inicio";

vi.mock("@/lib/api", () => ({ leerCapacidades: vi.fn() }));
afterEach(() => vi.clearAllMocks());

it("ofrece los dos caminos, cada uno con su enlace", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockResolvedValue({ proponer: true, motivo: null });
  render(<Inicio />);
  expect(screen.getByRole("heading", { name: /qué tienes del trámite/i })).toBeInTheDocument();
  expect(screen.getByRole("article", { name: /expediente completo/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /empezar con el expediente completo/i })).toHaveAttribute("href", "/expediente");
  expect(await screen.findByRole("link", { name: /empezar con el as-is/i })).toHaveAttribute("href", "/desde-as-is");
});

it("sin licencia, el camino del AS-IS sale desactivado con el motivo", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockResolvedValue({ proponer: false, motivo: "Sin licencia de Planeación." });
  render(<Inicio />);
  expect(await screen.findByText("Sin licencia de Planeación.")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /empezar con el as-is/i })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /empezar con el as-is/i })).toBeDisabled();
});

it("si no se puede consultar, el camino del AS-IS queda activo", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockRejectedValue(new Error("red"));
  render(<Inicio />);
  expect(await screen.findByRole("link", { name: /empezar con el as-is/i })).toBeInTheDocument();
});
```

```ts
// frontend/src/lib/api.fase3.test.ts (añadir dentro del describe)
  it("leerCapacidades y leerToBe", async () => {
    const f = vi.spyOn(globalThis, "fetch");
    f.mockResolvedValueOnce(json(200, { proponer: false, motivo: "x" }));
    expect(await leerCapacidades()).toEqual({ proponer: false, motivo: "x" });
    f.mockResolvedValueOnce(new Response("# TO-BE", { status: 200 }));
    expect(await leerToBe("a".repeat(16))).toBe("# TO-BE");
    expect(f.mock.calls[1][0]).toBe(`/api/v1/expedientes/${"a".repeat(16)}/insumos/to_be`);
    f.mockResolvedValueOnce(json(404, { error: "sin TO-BE" }));
    await expect(leerToBe("a".repeat(16))).rejects.toMatchObject({ status: 404 });
  });
```

(añadir `leerCapacidades, leerToBe` al import de ese archivo).

- [ ] **Step 2: Correr y ver que fallan**

Run: `cd frontend && npx vitest run src/lib/rutas.test.ts src/components/MigasDePan.test.tsx src/features/inicio src/lib/api.fase3.test.ts`
Expected: FAIL (módulos inexistentes / funciones no exportadas)

- [ ] **Step 3: `rutas.ts`**

```ts
// frontend/src/lib/rutas.ts
/**
 * Que pantalla toca y que migas de pan lleva, en funciones puras. `App` sigue
 * decidiendo por `pathname` (sin enrutador de terceros: cinco pantallas no lo
 * justifican y las ligas `/revisar/{sid}` que ya circulan siguen vivas).
 */
export type Camino = "carpeta" | "as_is";
export type Ruta =
  | { tipo: "inicio" }
  | { tipo: "expediente" }
  | { tipo: "desde_as_is" }
  | { tipo: "revisar"; sid: string }
  | { tipo: "catalogos" }
  | { tipo: "historial" }
  | { tipo: "tablero" };

const RE_REVISAR = /^\/revisar\/([0-9a-f]{16})$/;

export function leerRuta(pathname: string): Ruta {
  const m = RE_REVISAR.exec(pathname);
  if (m) return { tipo: "revisar", sid: m[1] };
  switch (pathname) {
    case "/expediente": return { tipo: "expediente" };
    case "/desde-as-is": return { tipo: "desde_as_is" };
    case "/catalogos": return { tipo: "catalogos" };
    case "/historial": return { tipo: "historial" };
    case "/tablero": return { tipo: "tablero" };
    default: return { tipo: "inicio" };
  }
}

export type Pantalla = "inicio" | "carga" | "diccionario" | "tobe" | "revision";
export type Tramo = { etiqueta: string; href?: string };

const NOMBRE_CAMINO: Record<Camino, string> = {
  carpeta: "Expediente completo",
  as_is: "Solo AS-IS",
};

/**
 * Maximo tres tramos y solo «Inicio» enlaza: volver a «Expediente completo»
 * desde la revision abriria una carga nueva y la sesion se perderia de vista.
 */
export function migas(pantalla: Pantalla, camino: Camino | null): Tramo[] {
  if (pantalla === "inicio") return [{ etiqueta: "Inicio" }];
  const inicio: Tramo = { etiqueta: "Inicio", href: "/" };
  const tramoCamino: Tramo[] = camino ? [{ etiqueta: NOMBRE_CAMINO[camino] }] : [];
  if (pantalla === "carga") return [inicio, ...tramoCamino];
  if (pantalla === "diccionario") return [inicio, { etiqueta: NOMBRE_CAMINO.as_is }, { etiqueta: "Diccionario (1 de 2)" }];
  if (pantalla === "tobe") return [inicio, { etiqueta: NOMBRE_CAMINO.as_is }, { etiqueta: "TO-BE (2 de 2)" }];
  return [inicio, ...tramoCamino, { etiqueta: "Revisión" }];
}
```

- [ ] **Step 4: `MigasDePan.tsx`**

```tsx
// frontend/src/components/MigasDePan.tsx
import { ChevronRight } from "lucide-react";

import type { Tramo } from "@/lib/rutas";

/** Donde esta la persona: camino y paso, arriba del contenido. */
export default function MigasDePan({ tramos }: { tramos: Tramo[] }) {
  return (
    <nav aria-label="Migas de pan" className="pb-4 text-sm text-muted-foreground">
      <ol className="flex flex-wrap items-center gap-1">
        {tramos.map((t, i) => {
          const ultimo = i === tramos.length - 1;
          return (
            <li key={`${t.etiqueta}-${i}`} className="flex items-center gap-1">
              {t.href && !ultimo ? (
                <a href={t.href} className="text-primary underline-offset-2 hover:underline">
                  {t.etiqueta}
                </a>
              ) : (
                <span aria-current={ultimo ? "page" : undefined}
                  className={ultimo ? "font-medium text-foreground" : undefined}>
                  {t.etiqueta}
                </span>
              )}
              {!ultimo ? <ChevronRight aria-hidden className="size-4" /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
```

- [ ] **Step 5: Tipos y cliente**

En `types.ts` (al final):

```ts
/** `GET /api/v1/capacidades`. */
export type Capacidades = { proponer: boolean; motivo: string | null };
/** Un campo del Diccionario propuesto, ya leido por el extractor. */
export type CampoVista = {
  etiqueta: string;
  tipo: string;
  obligatorio: boolean;
  opciones: string[];
  condicion: string | null;
};
export type PantallaVista = { id: string; nombre: string; actor: string; campos: CampoVista[] };
```

y en `DocumentoGenerado` añadir `vista?: PantallaVista[];`, en `GeneradosOut` añadir `insumos?: { diccionario: boolean; tobe: boolean };`.

En `api.ts` (al final; añadir `Capacidades` al import de tipos):

```ts
/** `GET /api/v1/capacidades` — si este servidor puede proponer desde el AS-IS. */
export async function leerCapacidades(): Promise<Capacidades> {
  return pedirJson<Capacidades>(`${BASE}/capacidades`);
}

/** `GET /api/v1/expedientes/{sid}/insumos/to_be` — el TO-BE de la sesion, en texto. */
export async function leerToBe(sid: string): Promise<string> {
  const res = await fetch(`${BASE}/expedientes/${sid}/insumos/to_be`);
  if (!res.ok) {
    let cuerpo: unknown;
    try { cuerpo = await res.json(); } catch { cuerpo = undefined; }
    throw ErrorApi.desde(res.status, cuerpo);
  }
  return res.text();
}
```

- [ ] **Step 6: `Inicio.tsx`**

```tsx
// frontend/src/features/inicio/Inicio.tsx
import { FolderOpen, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { leerCapacidades } from "@/lib/api";
import type { Capacidades } from "@/lib/types";

/**
 * La primera pregunta: ¿que tienes del tramite? Cada camino con una frase de
 * cuando usarlo. Sin licencia, el del AS-IS lo dice aqui, antes de subir nada.
 */
export default function Inicio() {
  // Mientras no se sepa, el camino se muestra activo: si la consulta falla,
  // el error llega al subir, como antes de que existiera esta pregunta.
  const [cap, setCap] = useState<Capacidades>({ proponer: true, motivo: null });

  useEffect(() => {
    let vivo = true;
    leerCapacidades()
      .then((c) => { if (vivo) setCap(c); })
      .catch(() => {});
    return () => { vivo = false; };
  }, []);

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">¿Qué tienes del trámite?</h1>
        <p className="text-sm text-muted-foreground">
          Elige un camino. Los dos terminan en la misma revisión, el simulador y el .gpm.
        </p>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <Card role="article" aria-label="Tengo el expediente completo" className="py-4">
          <CardHeader>
            <FolderOpen aria-hidden className="size-8 text-primary" />
            <CardTitle className="text-lg">Tengo el expediente completo</CardTitle>
            <CardDescription>
              AS-IS, TO-BE y Diccionario ya están listos. Sube la carpeta y el compilador te
              dice qué le falta para generar el .gpm.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <a href="/expediente" aria-label="Empezar con el expediente completo"
              className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/80">
              Empezar →
            </a>
          </CardFooter>
        </Card>
        <Card role="article" aria-label="Solo tengo el AS-IS" className="py-4">
          <CardHeader>
            <Sparkles aria-hidden className="size-8 text-primary" />
            <CardTitle className="text-lg">Solo tengo el AS-IS</CardTitle>
            <CardDescription>
              El compilador propone el Diccionario y el TO-BE a partir del AS-IS. Tú los revisas,
              los corriges si hace falta y decides si se usan.
            </CardDescription>
          </CardHeader>
          {!cap.proponer && cap.motivo ? (
            <CardContent>
              <p className="rounded-md border border-border bg-muted p-3 text-sm">{cap.motivo}</p>
            </CardContent>
          ) : null}
          <CardFooter>
            {cap.proponer ? (
              <a href="/desde-as-is" aria-label="Empezar con el AS-IS"
                className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/80">
                Empezar →
              </a>
            ) : (
              <Button type="button" disabled aria-label="Empezar con el AS-IS">Empezar →</Button>
            )}
          </CardFooter>
        </Card>
      </div>
      <footer className="text-sm text-muted-foreground">
        <a className="text-primary underline underline-offset-2" href="/historial">
          Ver expedientes anteriores
        </a>
      </footer>
    </section>
  );
}
```

- [ ] **Step 7: Correr y ver que pasan**

Run: `cd frontend && npx vitest run src/lib src/components src/features/inicio && npx tsc -b --noEmit`
Expected: PASS, sin errores de tipos

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib frontend/src/components/MigasDePan.tsx frontend/src/components/MigasDePan.test.tsx frontend/src/features/inicio
git commit -m "feat(spa): inicio con dos caminos, migas de pan y rutas en funciones puras"
```

---

### Task 4: SPA — `CargaAsIs`, `CargaInsumos` sin «Proponer», y `App` con los dos caminos

**Files:**
- Create: `frontend/src/features/carga/CargaAsIs.tsx`, `frontend/src/features/carga/CargaAsIs.test.tsx`
- Modify: `frontend/src/features/carga/CargaInsumos.tsx`, `frontend/src/features/carga/CargaInsumos.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `leerRuta`, `migas`, `Camino` (Task 3); `MigasDePan`, `Inicio` (Task 3); `proponerExpediente`, `leerGenerados`, `leerExpediente`, `ErrorApi`.
- Produces: `CargaAsIs({ onPropuesta }: { onPropuesta: (sid: string) => void })`; `CargaInsumos({ onListo })` (sin `onPropuesta`).

- [ ] **Step 1: Pruebas que fallan**

```tsx
// frontend/src/features/carga/CargaAsIs.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import CargaAsIs from "./CargaAsIs";

vi.mock("@/lib/api", () => ({
  proponerExpediente: vi.fn(),
  ErrorApi: class extends Error { status = 0; error = ""; archivos?: string[];
    constructor(m: string) { super(m); this.error = m; } },
}));

it("el boton se habilita con el AS-IS y manda el AS-IS y los adjuntos", async () => {
  const { proponerExpediente } = await import("@/lib/api");
  vi.mocked(proponerExpediente).mockResolvedValue({ sid: "b".repeat(16), estado: "generando" });
  const onPropuesta = vi.fn();
  render(<CargaAsIs onPropuesta={onPropuesta} />);
  const btn = screen.getByRole("button", { name: /proponer to-be y diccionario/i });
  expect(btn).toBeDisabled();
  expect(screen.getByText(/redacta un borrador/i)).toBeInTheDocument();
  await userEvent.upload(screen.getByLabelText(/análisis as-is/i), new File(["# x"], "as.md", { type: "text/markdown" }));
  await userEvent.upload(screen.getByLabelText(/documentos de apoyo/i), new File(["png"], "d.png", { type: "image/png" }));
  expect(btn).toBeEnabled();
  await userEvent.click(btn);
  const fd = vi.mocked(proponerExpediente).mock.calls[0][0];
  expect(fd.get("as_is")).toBeInstanceOf(File);
  expect(fd.getAll("adjuntos")).toHaveLength(1);
  expect(onPropuesta).toHaveBeenCalledWith("b".repeat(16));
});

it("un error del servidor se muestra y no navega", async () => {
  const { proponerExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("archivo demasiado grande"); e.status = 413;
  vi.mocked(proponerExpediente).mockRejectedValue(e);
  const onPropuesta = vi.fn();
  render(<CargaAsIs onPropuesta={onPropuesta} />);
  await userEvent.upload(screen.getByLabelText(/análisis as-is/i), new File(["# x"], "as.md"));
  await userEvent.click(screen.getByRole("button", { name: /proponer/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/demasiado grande/);
  expect(onPropuesta).not.toHaveBeenCalled();
});
```

En `CargaInsumos.test.tsx`: **sustituir** las dos pruebas de la Fase 3 («Proponer… solo se habilita…» y «proponer manda el AS-IS…», que se mudan a `CargaAsIs`) por:

```tsx
it("la carga del expediente completo ya no ofrece proponer: eso es el otro camino", () => {
  render(<CargaInsumos onListo={() => {}} />);
  expect(screen.queryByRole("button", { name: /proponer/i })).not.toBeInTheDocument();
});
```

En `App.test.tsx`: añadir al `vi.mock("@/lib/api")` `leerCapacidades: vi.fn().mockResolvedValue({ proponer: true, motivo: null })` y `leerToBe: vi.fn().mockRejectedValue(new Error("sin TO-BE"))`. **Sustituir** la primera prueba («arranca en la pantalla de carga… 'Extraer' deshabilitado») — la raíz ya no es la carga — por estas, y añadir las del camino:

```tsx
  it("la raiz es el Inicio con los dos caminos", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: /qué tienes del trámite/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent("Inicio");
  });

  it("/expediente abre la carga de siempre con sus migas", () => {
    window.history.pushState({}, "", "/expediente");
    render(<App />);
    expect(screen.getByRole("button", { name: /extraer/i })).toBeDisabled();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent(/Inicio.*Expediente completo/);
    window.history.pushState({}, "", "/");
  });

  it("/desde-as-is abre la carga del AS-IS con sus migas", () => {
    window.history.pushState({}, "", "/desde-as-is");
    render(<App />);
    expect(screen.getByRole("button", { name: /proponer to-be y diccionario/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent(/Inicio.*Solo AS-IS/);
    window.history.pushState({}, "", "/");
  });

  it("/revisar/:sid de una sesion de carpeta: migas «Expediente completo › Revisión»", async () => {
    const { leerExpediente, leerGenerados, ErrorApi } = await import("@/lib/api");
    vi.mocked(leerExpediente).mockResolvedValue({
      sid: "d".repeat(16), manifiesto: { tramite: { nombre: "X" }, pantallas: [], flujo: { tareas: [], conexiones: [] } },
      huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false,
    } as any);
    const e = new (ErrorApi as any)("no"); e.status = 404;
    vi.mocked(leerGenerados).mockRejectedValue(e);
    window.history.pushState({}, "", `/revisar/${"d".repeat(16)}`);
    render(<App />);
    expect(await screen.findByText("Expediente completo")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent(/Revisión/);
    window.history.pushState({}, "", "/");
  });

  it("/revisar/:sid con /generados caido por red: migas «Inicio › Revisión», sin romper", async () => {
    const { leerExpediente, leerGenerados } = await import("@/lib/api");
    vi.mocked(leerExpediente).mockResolvedValue({
      sid: "e".repeat(16), manifiesto: { tramite: { nombre: "X" }, pantallas: [], flujo: { tareas: [], conexiones: [] } },
      huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false,
    } as any);
    vi.mocked(leerGenerados).mockRejectedValue(new TypeError("Failed to fetch"));
    window.history.pushState({}, "", `/revisar/${"e".repeat(16)}`);
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: /migas de pan/i });
    await vi.waitFor(() => expect(nav).toHaveTextContent(/Revisión/));
    expect(nav).not.toHaveTextContent(/Expediente completo|Solo AS-IS/);
    window.history.pushState({}, "", "/");
  });
```

(La prueba existente del 409 → Propuestas se conserva tal cual.)

- [ ] **Step 2: Correr y ver que fallan**

Run: `cd frontend && npx vitest run src/features/carga src/App.test.tsx`
Expected: FAIL (`CargaAsIs` no existe; la raíz sigue mostrando la carga)

- [ ] **Step 3: `CargaAsIs.tsx`**

```tsx
// frontend/src/features/carga/CargaAsIs.tsx
import { Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ErrorApi, proponerExpediente } from "@/lib/api";

const CLASE_INPUT =
  "text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground";

/**
 * Camino «Solo tengo el AS-IS»: se sube el AS-IS (y adjuntos, si hay) y el
 * compilador redacta el Diccionario y el TO-BE en segundo plano.
 */
export default function CargaAsIs({ onPropuesta }: { onPropuesta: (sid: string) => void }) {
  const [asIs, setAsIs] = useState<File | null>(null);
  const [apoyo, setApoyo] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const proponer = async () => {
    if (!asIs) return;
    setError(null);
    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("as_is", asIs);
      apoyo.forEach((a) => fd.append("adjuntos", a));
      const { sid } = await proponerExpediente(fd);
      onPropuesta(sid);
    } catch (e) {
      if (!(e instanceof ErrorApi)) throw e;
      setError(e.error || e.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Sube el Análisis AS-IS</h1>
        <p className="text-sm text-muted-foreground">
          El compilador redacta un borrador del Diccionario de Datos y de la Propuesta TO-BE a
          partir del AS-IS. Después los revisas uno por uno y decides si se usan. Suele tardar
          uno o dos minutos.
        </p>
      </header>

      <div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-4">
        <label htmlFor="as-is" className="text-sm font-medium">Análisis AS-IS</label>
        <input id="as-is" type="file" accept=".md,.docx,.pdf,text/markdown" className={CLASE_INPUT}
          onChange={(e) => setAsIs(e.target.files?.[0] ?? null)} />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-4">
        <label htmlFor="apoyo-as-is" className="text-sm font-medium">Documentos de apoyo (opcional)</label>
        <p className="text-sm text-muted-foreground">Diagramas o PDF que quieras tener a la vista al revisar.</p>
        <input id="apoyo-as-is" type="file" multiple className={CLASE_INPUT}
          onChange={(e) => setApoyo(Array.from(e.target.files ?? []))} />
      </div>

      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}

      <Button type="button" size="lg" onClick={proponer} disabled={asIs === null || enviando}
        className="h-11 self-stretch text-base sm:self-start">
        <Sparkles aria-hidden className="size-4" />
        Proponer TO-BE y Diccionario
      </Button>
    </section>
  );
}
```

- [ ] **Step 4: Quitar «Proponer» de `CargaInsumos.tsx`**

Borrar la prop `onPropuesta` (y su tipo), la función `proponer`, el `<div>` con el botón «Proponer TO-BE y Diccionario» y su párrafo, y `proponerExpediente` del import.

- [ ] **Step 5: `App.tsx` con los dos caminos**

Imports: `MigasDePan`, `Inicio`, `CargaAsIs`, `{ leerRuta, migas, type Camino }` de `@/lib/rutas`, `leerGenerados` de `@/lib/api`. Quitar la constante `RE_REVISAR` (vive en `rutas.ts`). Cuerpo:

```tsx
export default function App() {
  const ruta = leerRuta(window.location.pathname);
  const [est, setEst] = useState<EstadoExpediente | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [sidPropuesta, setSidPropuesta] = useState<string | null>(null);
  // Por que camino llego la persona. Se sabe al elegir la tarjeta; al abrir
  // una liga `/revisar/{sid}` se deduce: si la sesion tiene propuestas, vino
  // por el AS-IS. Sin respuesta, las migas no nombran camino.
  const [camino, setCamino] = useState<Camino | null>(
    ruta.tipo === "expediente" ? "carpeta" : ruta.tipo === "desde_as_is" ? "as_is" : null,
  );
  const [cargando, setCargando] = useState(ruta.tipo === "revisar");

  useUrlDeRevision(est?.sid ?? sidPropuesta);

  useEffect(() => {
    if (ruta.tipo !== "revisar") return;
    const sid = ruta.sid;
    leerExpediente(sid)
      .then((e) => {
        setEst(e);
        leerGenerados(sid)
          .then(() => setCamino("as_is"))
          .catch((err: unknown) => {
            if (err instanceof ErrorApi && err.status === 404) setCamino("carpeta");
          });
      })
      .catch((e: unknown) => {
        // 409: la sesion nacio en la Fase 3 y aun no tiene manifiesto.
        if (e instanceof ErrorApi && e.status === 409) {
          setSidPropuesta(sid);
          setCamino("as_is");
        } else setAviso("La sesion expiro o no existe. Vuelve a subir los insumos.");
      })
      .finally(() => setCargando(false));
    // La ruta se lee una sola vez al montar: los cambios de pantalla dentro
    // de la SPA no recargan.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const titulo =
    ruta.tipo === "catalogos" ? "Catálogos"
    : ruta.tipo === "historial" ? "Historial"
    : ruta.tipo === "tablero" ? "Tablero"
    : est ? "Revisión del expediente"
    : sidPropuesta ? "Propuesta del compilador"
    : ruta.tipo === "expediente" ? "Expediente completo"
    : ruta.tipo === "desde_as_is" ? "Solo AS-IS"
    : "Inicio";

  let contenido: ReactNode;
  if (ruta.tipo === "catalogos") contenido = <Catalogos />;
  else if (ruta.tipo === "historial") contenido = <Historial />;
  else if (ruta.tipo === "tablero") contenido = <Tablero />;
  else if (est) contenido = (<>
    <MigasDePan tramos={migas("revision", camino)} />
    <WizardHuecos estado={est} onEstado={setEst} />
  </>);
  else if (sidPropuesta) contenido = (
    <Propuestas sid={sidPropuesta} onListo={(e) => { setSidPropuesta(null); setEst(e); }} />
  );
  else if (cargando) contenido = <p className="text-sm text-muted-foreground">Abriendo el expediente…</p>;
  else if (ruta.tipo === "expediente") contenido = (<>
    <MigasDePan tramos={migas("carga", "carpeta")} />
    <CargaInsumos onListo={setEst} />
  </>);
  else if (ruta.tipo === "desde_as_is") contenido = (<>
    <MigasDePan tramos={migas("carga", "as_is")} />
    <CargaAsIs onPropuesta={setSidPropuesta} />
  </>);
  else contenido = (<>
    <MigasDePan tramos={migas("inicio", null)} />
    <Inicio />
  </>);
```

y en el JSX: `<AppHeader titulo={titulo} />`, el `aviso` como hoy, y `{contenido}` en lugar de la cadena de ternarios. Importar `type ReactNode` de `react`. (Si el proyecto no usa la regla `react-hooks/exhaustive-deps`, quitar ese comentario.)

- [ ] **Step 6: Correr el chequeo completo**

Run: `bash scripts/check-frontend.sh`
Expected: `tsc` limpio, vitest PASS, build OK

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/carga frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(spa): los dos caminos — /expediente, /desde-as-is y migas en cada pantalla"
```

---

### Task 5: SPA — diagrama con zoom y pantalla completa, y en la revisión de huecos

**Files:**
- Modify: `frontend/src/features/propuestas/DiagramaMermaid.tsx`, `DiagramaMermaid.test.tsx`
- Create: `frontend/src/features/huecos/DiagramaToBe.tsx`, `DiagramaToBe.test.tsx`
- Modify: `frontend/src/features/huecos/WizardHuecos.tsx` (tras `<Adjuntos …/>`), `WizardHuecos.test.tsx` (mock `leerToBe`)

**Interfaces:**
- Produces: `DiagramaMermaid({ texto, retardoMs?, grande?: boolean })` — con `grande`, lienzo de 70 vh, controles «Acercar», «Alejar», «Ajustar» y «Pantalla completa» (solo si `document.fullscreenEnabled`); `DiagramaToBe({ sid, manifiesto })`.

- [ ] **Step 1: Pruebas que fallan**

```tsx
// DiagramaMermaid.test.tsx (añadir)
import userEvent from "@testing-library/user-event";

it("en grande trae zoom: acercar y alejar cambian la escala y ajustar la regresa", async () => {
  render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} grande />);
  await screen.findByTestId("svg-mermaid");
  const lienzo = screen.getByTestId("lienzo-diagrama");
  await userEvent.click(screen.getByRole("button", { name: "Acercar" }));
  expect(lienzo.style.transform).toBe("scale(1.25)");
  await userEvent.click(screen.getByRole("button", { name: "Alejar" }));
  await userEvent.click(screen.getByRole("button", { name: "Alejar" }));
  expect(lienzo.style.transform).toBe("scale(0.75)");
  await userEvent.click(screen.getByRole("button", { name: "Ajustar" }));
  expect(lienzo.style.transform).toBe("scale(1)");
});

it("pantalla completa solo si el navegador la permite", async () => {
  const { rerender } = render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} grande />);
  expect(screen.queryByRole("button", { name: /pantalla completa/i })).not.toBeInTheDocument();
  Object.defineProperty(document, "fullscreenEnabled", { value: true, configurable: true });
  const pedir = vi.fn().mockResolvedValue(undefined);
  HTMLElement.prototype.requestFullscreen = pedir;
  rerender(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> C\n```"} retardoMs={0} grande key="otra" />);
  await userEvent.click(await screen.findByRole("button", { name: /pantalla completa/i }));
  expect(pedir).toHaveBeenCalled();
  Object.defineProperty(document, "fullscreenEnabled", { value: undefined, configurable: true });
});

it("sin grande no hay controles", async () => {
  render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} />);
  await screen.findByTestId("svg-mermaid");
  expect(screen.queryByRole("button", { name: "Acercar" })).not.toBeInTheDocument();
});
```

```tsx
// frontend/src/features/huecos/DiagramaToBe.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import DiagramaToBe from "./DiagramaToBe";

vi.mock("@/lib/api", () => ({ leerToBe: vi.fn() }));
vi.mock("mermaid", () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: '<svg data-testid="svg-mermaid"></svg>' })) },
}));
afterEach(() => vi.clearAllMocks());

const manifiesto = { flujo: {
  tareas: [{ id: "t1", pantallas: ["p1"] }, { id: "t2", pantallas: ["p2"] }, { id: "t_fin", pantallas: [] }],
  conexiones: [{ de: "t1", a: "t2", cuando: { campo: "x" } }, { de: "t1", a: "t_fin", cuando: { campo: "x" } }],
} };

it("sin TO-BE en la sesion no aparece", async () => {
  const { leerToBe } = await import("@/lib/api");
  vi.mocked(leerToBe).mockRejectedValue(new Error("404"));
  const { container } = render(<DiagramaToBe sid={"a".repeat(16)} manifiesto={manifiesto} />);
  await vi.waitFor(() => expect(leerToBe).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
});

it("plegada con el conteo; al abrir dibuja el diagrama grande", async () => {
  const { leerToBe } = await import("@/lib/api");
  vi.mocked(leerToBe).mockResolvedValue("```mermaid\nflowchart TD\n A --> B\n```");
  render(<DiagramaToBe sid={"a".repeat(16)} manifiesto={manifiesto} />);
  const tarjeta = await screen.findByRole("article", { name: /diagrama del to-be/i });
  expect(tarjeta).toHaveTextContent("2 tareas · 1 decisión");
  expect(screen.queryByTestId("svg-mermaid")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /ver el diagrama/i }));
  expect(await screen.findByTestId("svg-mermaid", {}, { timeout: 2000 })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Acercar" })).toBeInTheDocument();
});
```

En `WizardHuecos.test.tsx`, añadir al `vi.mock("@/lib/api")`: `leerToBe: vi.fn().mockRejectedValue(new Error("sin TO-BE")),`.

- [ ] **Step 2: Correr y ver que fallan**

Run: `cd frontend && npx vitest run src/features/propuestas/DiagramaMermaid.test.tsx src/features/huecos/DiagramaToBe.test.tsx`
Expected: FAIL

- [ ] **Step 3: `DiagramaMermaid.tsx` con `grande`**

Añadir `grande?: boolean` a `Props`, estado `const [escala, setEscala] = useState(1)`, `const marco = useRef<HTMLDivElement>(null)`, y sustituir el bloque del SVG por:

```tsx
      {svg ? (
        <div ref={marco}
          className={cn("relative overflow-auto rounded-md border border-border bg-card p-3",
            grande && "h-[70vh]")}>
          {grande ? (
            <div className="sticky top-0 z-10 flex justify-end gap-1 pb-2">
              <Button type="button" size="sm" variant="outline" aria-label="Alejar"
                onClick={() => setEscala((e) => Math.max(0.5, e - 0.25))}>−</Button>
              <Button type="button" size="sm" variant="outline" aria-label="Ajustar"
                onClick={() => setEscala(1)}>Ajustar</Button>
              <Button type="button" size="sm" variant="outline" aria-label="Acercar"
                onClick={() => setEscala((e) => Math.min(3, e + 0.25))}>+</Button>
              {document.fullscreenEnabled ? (
                <Button type="button" size="sm" variant="outline" aria-label="Pantalla completa"
                  onClick={() => void marco.current?.requestFullscreen()}>
                  Pantalla completa
                </Button>
              ) : null}
            </div>
          ) : null}
          <div data-testid="lienzo-diagrama" className="origin-top-left transition-transform"
            style={{ transform: `scale(${escala})` }}
            // SVG que produce mermaid con securityLevel strict (DOMPurify) a
            // partir del texto del TO-BE: puede venir del modelo o de otra
            // persona; lo protege strict mas la CSP, que no permite scripts
            // en linea.
            dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      ) : null}
```

Imports: `useRef` de `react`, `Button` de `@/components/ui/button`, `cn` de `cn`. (Este comentario corrige el menor diferido m7 de la revisión: el SVG no viene solo del texto de la persona.)

- [ ] **Step 4: `DiagramaToBe.tsx`**

```tsx
// frontend/src/features/huecos/DiagramaToBe.tsx
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DiagramaMermaid from "@/features/propuestas/DiagramaMermaid";
import { leerToBe } from "@/lib/api";

type Flujo = { tareas?: { pantallas?: string[] }[]; conexiones?: { de: string; cuando?: unknown }[] };

function plural(n: number, s: string, p: string) {
  return `${n} ${n === 1 ? s : p}`;
}

/** «2 tareas · 1 decisión», contado del manifiesto que ya se extrajo. */
function conteo(manifiesto: Record<string, unknown>): string {
  const f = (manifiesto.flujo ?? {}) as Flujo;
  const tareas = (f.tareas ?? []).filter((t) => (t.pantallas ?? []).length > 0).length;
  const decisiones = new Set((f.conexiones ?? []).filter((c) => c.cuando).map((c) => c.de)).size;
  return `${plural(tareas, "tarea", "tareas")} · ${plural(decisiones, "decisión", "decisiones")}`;
}

/**
 * El TO-BE dibujado en la revision de huecos. Plegado por omision: la lista
 * de huecos sigue siendo lo principal; el diagrama se abre cuando ayuda
 * (sobre todo con los huecos de flujo). Sin TO-BE en la sesion, no aparece.
 */
export default function DiagramaToBe({ sid, manifiesto }: { sid: string; manifiesto: Record<string, unknown> }) {
  const [texto, setTexto] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const t = await leerToBe(sid);
        if (vivo) setTexto(t);
      } catch {
        if (vivo) setTexto(null);
      }
    })();
    return () => { vivo = false; };
  }, [sid]);

  if (texto === null) return null;
  return (
    <Card role="article" aria-label="Diagrama del TO-BE" className="py-4">
      <CardHeader>
        <CardTitle>Diagrama del TO-BE · {conteo(manifiesto)}</CardTitle>
        <CardAction>
          <Button type="button" variant="outline" size="sm" onClick={() => setAbierto((a) => !a)}>
            {abierto ? "Ocultar el diagrama" : "Ver el diagrama"}
          </Button>
        </CardAction>
      </CardHeader>
      {abierto ? (
        <CardContent>
          <DiagramaMermaid texto={texto} grande />
        </CardContent>
      ) : null}
    </Card>
  );
}
```

En `WizardHuecos.tsx`, después de `<Adjuntos sid={estado.sid} adjuntos={estado.adjuntos ?? []} />`:

```tsx
        <DiagramaToBe sid={estado.sid} manifiesto={manifiesto} />
```

(importar `DiagramaToBe from "./DiagramaToBe"`; `manifiesto` ya existe en ese componente).

- [ ] **Step 5: Correr el chequeo completo**

Run: `bash scripts/check-frontend.sh`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/propuestas/DiagramaMermaid.tsx frontend/src/features/propuestas/DiagramaMermaid.test.tsx frontend/src/features/huecos
git commit -m "feat(spa): diagrama grande con zoom y pantalla completa, tambien en la revision de huecos"
```

---

### Task 6: SPA — la propuesta, un documento por pantalla

**Files:**
- Create: `frontend/src/features/propuestas/VistaDiccionario.tsx`, `VistaDiccionario.test.tsx`
- Modify: `frontend/src/features/propuestas/TarjetaPropuesta.tsx`, `TarjetaPropuesta.test.tsx`
- Modify: `frontend/src/features/propuestas/Propuestas.tsx`, `Propuestas.test.tsx`

**Interfaces:**
- Consumes: `PantallaVista`, `GeneradosOut.insumos` (Task 3); `DiagramaMermaid` con `grande` (Task 5); `MigasDePan`, `migas` (Task 3).
- Produces: `VistaDiccionario({ pantallas }: { pantallas: PantallaVista[] })`; `TarjetaPropuesta` con las mismas props de hoy (la `vista` sale de `documento.vista`).

- [ ] **Step 1: Pruebas que fallan**

```tsx
// frontend/src/features/propuestas/VistaDiccionario.test.tsx
import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import VistaDiccionario from "./VistaDiccionario";

const pantallas = [
  { id: "p1", nombre: "Solicitud", actor: "Ciudadano", campos: [
    { etiqueta: "CURP", tipo: "text", obligatorio: true, opciones: [], condicion: null },
    { etiqueta: "Poder notarial", tipo: "file", obligatorio: false, opciones: [],
      condicion: "«Tipo de persona» es «Moral»" }] },
  { id: "p2", nombre: "Revisión", actor: "Funcionario", campos: [
    { etiqueta: "Dictamen", tipo: "select", obligatorio: true, opciones: ["Aprobado", "Rechazado"], condicion: null }] },
];

it("una tarjeta por pantalla y un campo por tarjeta, en palabras", () => {
  render(<VistaDiccionario pantallas={pantallas} />);
  const p1 = screen.getByRole("article", { name: "Pantalla 1 · Ciudadano · Solicitud" });
  expect(within(p1).getByText("CURP")).toBeInTheDocument();
  expect(within(p1).getByText(/Texto/)).toBeInTheDocument();
  expect(within(p1).getAllByLabelText("obligatorio")).toHaveLength(1);
  expect(within(p1).getByText(/Archivo/)).toBeInTheDocument();
  expect(within(p1).getByText("Visible solo si «Tipo de persona» es «Moral»")).toBeInTheDocument();
  const p2 = screen.getByRole("article", { name: "Pantalla 2 · Funcionario · Revisión" });
  expect(within(p2).getByText(/Lista/)).toBeInTheDocument();
  expect(within(p2).getByText("Aprobado · Rechazado")).toBeInTheDocument();
  expect(document.querySelector("table")).toBeNull();
});
```

`TarjetaPropuesta.test.tsx`: **sustituir** la prueba «muestra el texto editable…» (el Diccionario ya no abre en texto) y **añadir**; las demás (editar→corregida, aceptar/declinar, sin documento, aceptado cerrado, TO-BE vs Diccionario con diagrama) se conservan, ajustando `doc` para que traiga `vista` y cambiando el primer paso de las de edición para pulsar antes «Editar texto»:

```tsx
const vista = [{ id: "p1", nombre: "Solicitud", actor: "Ciudadano",
  campos: [{ etiqueta: "CURP", tipo: "text", obligatorio: true, opciones: [], condicion: null }] }];
// `doc` pasa a: { ...lo de hoy, vista }

it("el Diccionario abre como pantallas; «Editar texto» muestra el Markdown y conserva lo editado", async () => {
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={doc}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByRole("article", { name: /pantalla 1 · ciudadano · solicitud/i })).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.getByText(/El AS-IS dice que el ciudadano entrega «CURP»/)).toBeInTheDocument();
  expect(screen.getByText(/lo propuso un modelo/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  await userEvent.type(screen.getByRole("textbox"), "más");
  await userEvent.click(screen.getByRole("button", { name: /ver como pantallas/i }));
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /aceptar con mis cambios/i })).toBeEnabled();
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  expect(screen.getByRole("textbox")).toHaveValue(doc.texto + "más");
});

it("si el compilador no leyo pantallas, abre el texto con el aviso", () => {
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={{ ...doc, vista: [] }}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByText(/no pudo leer pantallas/i)).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toHaveValue(doc.texto);
});

it("el TO-BE abre con el diagrama grande; «Editar texto» pone texto y diagrama lado a lado", async () => {
  const tobe = { ...doc, vista: undefined, texto: "```mermaid\nflowchart TD\n A --> B\n```" };
  render(<TarjetaPropuesta titulo="Propuesta TO-BE" clave="tobe" documento={tobe}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(await screen.findByTestId("svg-mermaid", {}, { timeout: 2000 })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Acercar" })).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  expect(screen.getByRole("textbox")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /ver el diagrama grande/i }));
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
```

(En «editar habilita… corregida» y «TO-BE vs Diccionario», pulsar `«Editar texto»` antes de escribir o comprobar.)

`Propuestas.test.tsx`: **sustituir** las cuatro pruebas de estado listo (hoy esperan dos tarjetas a la vez) por estas; se conservan «sin licencia…» y «un fallo pasajero…» con `toHaveLength(1)`:

```tsx
const conVista = { ...doc, vista: [{ id: "p1", nombre: "Solicitud", actor: "Ciudadano", campos: [] }] };
const listo = { estado: "listo" as const, motivo: null, nombre: "Constancia",
  diccionario: conVista, tobe: { ...doc, version_prompt: "tobe-v1" },
  insumos: { diccionario: false, tobe: false } };

it("primero el Diccionario (1 de 2), despues el TO-BE (2 de 2)", async () => {
  const { leerGenerados, decidirDocumento } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue(listo);
  vi.mocked(decidirDocumento).mockResolvedValueOnce({ tipo: "generados", generados: {
    ...listo, diccionario: { ...conVista, decision: "aceptada" }, insumos: { diccionario: true, tobe: false } } });
  render(<Propuestas sid={SID} onListo={() => {}} />);
  expect(await screen.findByRole("navigation", { name: /migas de pan/i })).toHaveTextContent("Diccionario (1 de 2)");
  expect(screen.getAllByRole("article", { name: /diccionario de datos|propuesta to-be/i })).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: /aceptar tal cual/i }));
  expect(await screen.findByText("TO-BE (2 de 2)")).toBeInTheDocument();
  expect(screen.getByRole("article", { name: /propuesta to-be/i })).toBeInTheDocument();
});

it("al recargar con el Diccionario ya subido, abre en el TO-BE", async () => {
  const { leerGenerados } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue({ ...listo,
    diccionario: { ...conVista, decision: "declinada" }, insumos: { diccionario: true, tobe: false } });
  render(<Propuestas sid={SID} onListo={() => {}} />);
  expect(await screen.findByText("TO-BE (2 de 2)")).toBeInTheDocument();
});

it("cuando la decision devuelve el expediente, entra al wizard por onListo", async () => {
  const { leerGenerados, decidirDocumento } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue({ ...listo,
    diccionario: { ...conVista, decision: "aceptada" }, insumos: { diccionario: true, tobe: false } });
  const est = { sid: SID, manifiesto: {}, huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false };
  vi.mocked(decidirDocumento).mockResolvedValueOnce({ tipo: "expediente", estado: est });
  const onListo = vi.fn();
  render(<Propuestas sid={SID} onListo={onListo} />);
  await userEvent.click(await screen.findByRole("button", { name: /aceptar tal cual/i }));
  await waitFor(() => expect(onListo).toHaveBeenCalledWith(est));
});

it("422 con los dos resueltos: muestra las dos zonas de carga", async () => {
  const { leerGenerados, decidirDocumento, ErrorApi } = await import("@/lib/api");
  const soloDicc = { ...listo, diccionario: { ...conVista, decision: "aceptada" as const },
    insumos: { diccionario: true, tobe: false } };
  vi.mocked(leerGenerados)
    .mockResolvedValueOnce(soloDicc)
    .mockResolvedValueOnce({ ...soloDicc, tobe: { ...doc, version_prompt: "tobe-v1", decision: "aceptada" },
      insumos: { diccionario: true, tobe: true } });
  const e = new (ErrorApi as any)("no se extrajo ninguna pantalla"); e.status = 422;
  vi.mocked(decidirDocumento).mockRejectedValue(e);
  render(<Propuestas sid={SID} onListo={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: /aceptar tal cual/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se extrajo ninguna pantalla/);
  expect(await screen.findByLabelText(/subir mi diccionario/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/subir mi to-be/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `cd frontend && npx vitest run src/features/propuestas`
Expected: FAIL

- [ ] **Step 3: `VistaDiccionario.tsx`**

```tsx
// frontend/src/features/propuestas/VistaDiccionario.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PantallaVista } from "@/lib/types";

/** El tipo de campo como lo diria una persona, no como lo guarda GPM. */
const TIPO: Record<string, string> = {
  text: "Texto", textarea: "Texto largo", select: "Lista", radio: "Opción única",
  file: "Archivo", date: "Fecha", date_time: "Fecha y hora", paragraph: "Párrafo",
  subtitle: "Subtítulo", cart: "Carrito", api_ajax: "Consulta a otro sistema",
  documento: "Documento",
};

/**
 * El Diccionario propuesto como lo veria quien llena el tramite: una tarjeta
 * por pantalla y una tarjeta chica por campo. Lo arma el servidor con el
 * extractor de siempre (`vista` en generados.json); aqui solo se pinta.
 */
export default function VistaDiccionario({ pantallas }: { pantallas: PantallaVista[] }) {
  return (
    <div className="flex flex-col gap-4">
      {pantallas.map((p, i) => {
        const titulo = `Pantalla ${i + 1} · ${p.actor} · ${p.nombre}`;
        return (
          <Card key={p.id} role="article" aria-label={titulo} className="py-4">
            <CardHeader><CardTitle className="text-base">{titulo}</CardTitle></CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {p.campos.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin campos.</p>
              ) : p.campos.map((c, j) => (
                <div key={`${c.etiqueta}-${j}`} className="flex flex-col gap-1 rounded-md border border-border p-3 text-sm">
                  <span className="font-medium">
                    {c.etiqueta}
                    {c.obligatorio ? <span aria-label="obligatorio" className="text-destructive"> *</span> : null}
                  </span>
                  <span className="text-muted-foreground">{TIPO[c.tipo] ?? c.tipo}</span>
                  {c.opciones.length > 0 ? <span>{c.opciones.join(" · ")}</span> : null}
                  {c.condicion ? <span className="text-muted-foreground">Visible solo si {c.condicion}</span> : null}
                </div>
              ))}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: `TarjetaPropuesta.tsx` — modos de lectura y edición**

Añadir estado `const [editando, setEditando] = useState(clave === "diccionario" && (documento?.vista ?? []).length === 0);` y sustituir el bloque «pendiente» (el `<>…</>` con la nota, el `textarea`, el diagrama y los huecos) por:

```tsx
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                Esto lo propuso un modelo a partir del AS-IS. Revísalo como revisarías el
                trabajo de alguien nuevo.
              </p>
              <Button type="button" variant="outline" size="sm" onClick={() => setEditando((e) => !e)}>
                {!editando ? "Editar texto" : clave === "tobe" ? "Ver el diagrama grande" : "Ver como pantallas"}
              </Button>
            </div>
            {clave === "diccionario" && (documento.vista ?? []).length === 0 ? (
              <p role="status" className="text-sm text-muted-foreground">
                El compilador no pudo leer pantallas en este borrador; revisa el texto.
              </p>
            ) : null}
            {!editando ? (
              clave === "tobe" ? <DiagramaMermaid texto={texto} grande /> : <VistaDiccionario pantallas={documento.vista ?? []} />
            ) : (
              <div className={cn("grid gap-4", clave === "tobe" && "lg:grid-cols-2")}>
                <textarea aria-label={`Texto propuesto de ${titulo}`}
                  className="min-h-[60vh] w-full rounded-md border border-border bg-card p-3 font-mono text-sm"
                  value={texto} disabled={ocupado} onChange={(e) => setTexto(e.target.value)} spellCheck={false} />
                {clave === "tobe" ? <DiagramaMermaid texto={texto} /> : null}
              </div>
            )}
            {documento.huecos.length > 0 ? (
              /* la misma <ul> de pendientes de hoy, sin cambios */
            ) : null}
          </>
```

(la `<ul>` de pendientes se conserva idéntica; importar `VistaDiccionario` y `cn`). El estado `texto` ya vive en la tarjeta, así que alternar modos no pierde la edición.

- [ ] **Step 5: `Propuestas.tsx` — un documento por pantalla**

Importar `MigasDePan` y `migas`. Sustituir el bloque `g && g.estado !== "generando"` por:

```tsx
      {g && g.estado !== "generando" ? (() => {
        const hay = g.insumos ?? { diccionario: false, tobe: false };
        // Sin propuesta (error, sin licencia) o con los dos ya resueltos
        // (un 422 del extractor): las dos tarjetas, para poder subir encima
        // de cualquiera. Si no, un documento por pantalla.
        const ambos = !g.diccionario || !g.tobe || (hay.diccionario && hay.tobe);
        const paso: "diccionario" | "tobe" = hay.diccionario ? "tobe" : "diccionario";
        const tarjeta = (clave: "diccionario" | "tobe") => (
          <TarjetaPropuesta key={clave}
            titulo={clave === "diccionario" ? "Diccionario de Datos" : "Propuesta TO-BE"}
            clave={clave} documento={g[clave]}
            onDecidir={decidir(clave)} onSubir={subir(clave)} ocupado={ocupado} />
        );
        return (
          <>
            {g.motivo ? <p className="text-sm text-foreground">{g.motivo}</p> : null}
            {ambos ? (
              <div className="grid items-start gap-6 lg:grid-cols-2">
                {tarjeta("diccionario")}
                {tarjeta("tobe")}
              </div>
            ) : tarjeta(paso)}
          </>
        );
      })() : null}
```

Y arriba del `<header>`, las migas: `<MigasDePan tramos={migas(paso, "as_is")} />`, calculando `paso` también fuera del bloque (misma regla: `g?.insumos?.diccionario ? "tobe" : "diccionario"`).

- [ ] **Step 6: Correr el chequeo completo**

Run: `bash scripts/check-frontend.sh`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/propuestas
git commit -m "feat(spa): la propuesta paso a paso — Diccionario por pantallas y TO-BE con diagrama grande"
```

---

### Task 7: Documentación, despliegue y verificación en pantalla

**Files:**
- Modify: `README.md` (sección «Asistente web»)
- Modify: `docs/superpowers/specs/2026-09-24-dos-caminos-y-revision-visual-design.md:4` (estado)

- [ ] **Step 1: README**

En «Asistente web», sustituir el primer párrafo tras el bloque `gpmc servir` por:

```markdown
Abre `http://127.0.0.1:8000`. El inicio pregunta qué tienes del trámite: **el
expediente completo** (se elige la carpeta —o los archivos uno a uno— y el
asistente los reparte entre AS-IS, TO-BE, Diccionario y documentos de salida) o
**solo el AS-IS** (ver «Proponer desde el AS-IS» abajo). Unas migas de pan dicen
en qué camino y paso vas. Los insumos valen en `.md`, `.docx` o PDF con texto.
De ahí salen el `.gpm`, el manifiesto, el simulador y el reporte de huecos; en
la revisión, el TO-BE se puede ver dibujado, con zoom y a pantalla completa.
```

- [ ] **Step 2: Estado del spec**

Línea 4: `**Estado:** implementado el 2026-09-24 (plan: docs/superpowers/plans/2026-09-24-dos-caminos-y-revision-visual.md)`.

- [ ] **Step 3: Verificación completa y despliegue**

Run:
```bash
.venv/bin/pytest -q && bash scripts/check-frontend.sh
launchctl kickstart -k gui/$(id -u)/local.gpmc.servidor
```
Expected: todo en verde; `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/` → `200`.

- [ ] **Step 4: Mirarlo en pantalla** (Playwright, capturas en `.playwright-mcp/`, que se borran al terminar)

1. `/` → dos tarjetas; la del AS-IS desactivada con el motivo (el servidor corre con Gemini).
2. `/expediente` → la carga de siempre con «Inicio › Expediente completo».
3. Subir `ejemplos/expedientes/constancia-de-residencia/` por la carga (o `POST /api/v1/expedientes` con curl) y abrir `/revisar/{sid}` → migas «Inicio › Expediente completo › Revisión» y tarjeta «Diagrama del TO-BE · 4 tareas · 1 decisión»; al abrirla, diagrama grande con zoom.
4. La sesión de prueba con `generados.json` armado a mano (como el 2026-09-24): Diccionario como pantallas; al aceptar, TO-BE con el diagrama grande.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/specs/2026-09-24-dos-caminos-y-revision-visual-design.md
git commit -m "docs: dos caminos y revision visual en el LEEME; spec implementado"
```

- [ ] **Step 6: Nota propuesta para `CLAUDE.md` (NO aplicar; entregar al usuario)**

```markdown
### 12. Dos caminos de entrada y revisión visual (2026-09-24)

- `/` es el **Inicio** con dos caminos: `/expediente` (la carga de carpeta de
  siempre) y `/desde-as-is` (Fase 3). `lib/rutas.ts` decide pantalla y migas en
  funciones puras; `App` sigue sin enrutador. Migas de máximo tres tramos y solo
  «Inicio» enlaza.
- `GET /api/v1/capacidades` dice si el servidor puede proponer; sin licencia, la
  tarjeta del AS-IS sale desactivada con el motivo, antes de subir nada.
- La propuesta es un documento por pantalla: Diccionario como pantallas (`vista`
  en `generados.json`, armada con el extractor) y TO-BE con `DiagramaMermaid
  grande` (zoom CSS y pantalla completa, sin librería). `GeneradosOut.insumos`
  dice qué documento ya tiene archivo, para abrir en el paso correcto al recargar.
- La revisión de huecos muestra el TO-BE dibujado (`DiagramaToBe`, plegado; lee
  `GET /expedientes/{sid}/insumos/to_be`).
```

---

## Self-review

**Spec coverage.** Parte 1 (rutas, Inicio, capacidades, migas, camino deducido, `CargaAsIs`, `CargaInsumos` sin Proponer): Tasks 1, 3, 4. Parte 2 (`vista`, Diccionario por pantallas con «Editar texto», TO-BE grande con zoom/pantalla completa y panel lateral, orden Diccionario→TO-BE, generando/error/sin licencia): Tasks 2, 5, 6. Parte 3 (`insumos/to_be`, tarjeta plegable con conteo, oculta sin TO-BE): Tasks 1, 5. Pruebas del spec: repartidas en cada tarea. Fuera de alcance: nada de ello aparece.

**Añadido que el spec no nombraba:** `GeneradosOut.insumos` (Task 1). Sin él, al recargar con el Diccionario declinado y ya subido, el cliente no sabe en qué paso está; el servidor ya tiene el dato (`_resuelto`).

**Placeholder scan.** El único «(la misma `<ul>` de hoy)» en Task 6 Step 4 remite a código existente que no cambia, no a código por escribir.

**Type consistency.** `Camino`, `Pantalla`, `Tramo`, `migas`, `leerRuta` (Task 3) = usados en Tasks 4 y 6. `PantallaVista`/`CampoVista` (Task 3) = `vista_de` (Task 2) campo por campo (`etiqueta, tipo, obligatorio, opciones, condicion`). `DiagramaMermaid.grande` (Task 5) = usado en Tasks 5 y 6. `leerToBe` (Task 3) = usado en Task 5.

**Review Focus.** 1 → pruebas `/expediente` y `/desde-as-is` en Task 4. 2 → «/generados caído por red» en Task 4. 3 → «si no se puede consultar» en Task 3. 4 → «si el compilador no leyó pantallas» en Task 6. 5 → «422 con los dos resueltos» en Task 6.
