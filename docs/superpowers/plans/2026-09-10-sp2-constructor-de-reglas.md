# SP2 — Constructor visual de reglas (MMD-04 + DIC-08) — Plan de implementación

> **Para ejecutores agénticos:** SUB-SKILL REQUERIDA: usar
> `superpowers:subagent-driven-development` (recomendado) o
> `superpowers:executing-plans` para ejecutar este plan task por task. Los pasos
> usan checkbox (`- [ ]`).

**Goal:** que `DIC-08` (visibilidad no interpretable) y `MMD-04` (compuerta sin
`@@campo`) se resuelvan enteros desde el wizard de la SPA, sin tocar el modelador.

**Architecture:** `Condicion` gana cláusulas "Y" opcionales (retrocompatible).
El compilador ya emite `Condicion` vía `reglas.emitir`, solo cambia el emisor.
El extractor gana un override de compuerta y un helper de ramas. La API extiende
`resolver` con 3 `tipo` nuevos + 1 read. La SPA gana un constructor de reglas
reutilizable.

**Tech Stack:** Python 3.9+ / Pydantic v2 / FastAPI; Vite 8 + React 19 + TS 6 +
Tailwind v4 + shadcn (base-ui).

**Spec:** `docs/superpowers/specs/2026-09-10-sp2-constructor-de-reglas-design.md`

## Global Constraints

- Python 3.9-safe: `Optional[X]`, `list[X]` (el repo ya usa `list[...]`); nada de
  `X | None`. Identificadores en español sin acentos.
- `nucleo/formato.py` y `SINTAXIS_ESTRICTA` **no se tocan**. `SINTAXIS_ESTRICTA`
  sigue en `False`.
- Retrocompatibilidad: todo `.gpm` y `manifiesto.yaml` con `Condicion` de una
  sola comparación sigue parseando y compilando igual. `guardar()` ya usa
  `exclude_defaults=True`, así que un `y` vacío nunca se escribe. Cero migración.
- Ningún `.gpm` de `~/Desktop/Projects/GPM/` se sobrescribe.
- Suite Python nunca baja de **329 passed / 22 skipped** (cierre de SP1); solo
  sube.
- Frontend: `bash scripts/check-frontend.sh` verde (tsc `-b --noEmit` +
  `vitest run` + `vite build`). Sin dependencias nuevas. Colores desde tokens
  (`--action-primary`, `--alert-error`, …); sin literales hex nuevos en `.tsx`.
- CSP del SPA intacta; `/vistas/{sid}` conserva `sandbox`.
- Rama de trabajo aislada (worktree). Commits con trailers
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` y
  `Claude-Session: https://claude.ai/code/session_01MkMx3dEJw13wEMho8kmzYP`.
  Sin `git push` durante la ejecución.
- El separador AND emitido es exactamente `"&&"` sin espacios, para casar con el
  estilo actual de `emitir` (`@@campo=='valor'`, validado en plataforma).
  `reglas.evaluar` tolera espacios porque hace `.strip()` por parte; no importa.

---

## Estructura de archivos

| Archivo | Rol en SP2 |
|---|---|
| `src/gpmc/nucleo/manifiesto.py` | `Clausula` nueva; `Condicion.y: list[Clausula] = []`; el validador cruzado recorre `y` |
| `src/gpmc/nucleo/reglas.py` | `_emitir_clausula(campo, operador, igual)`; `emitir` une base + `y` con `&&` |
| `src/gpmc/extractores/diccionario.py` | hueco `DIC-08` con `ubicacion = f"{pantalla.id}::{nombre}"` |
| `src/gpmc/extractores/expediente.py` | `_flujo_ramificado(rm, pantallas, overrides=None)`; `ramas_de_compuerta(rm, pantallas, gate_id)` |
| `src/gpmc/web/sesiones.py` | `compuertas_de(carpeta)`, `escribir_compuertas(carpeta, d)` |
| `src/gpmc/web/reensamblado.py` (nuevo) | `reensamblar_flujo(carpeta, manifiesto) -> Manifiesto` — re-parsea TO-BE, aplica overrides, re-corre `_flujo_ramificado`, empalma |
| `src/gpmc/web/api.py` | `Resolucion` unión discriminada (`dic08`/`mmd04campo`/`mmd04rama`); `GET /expedientes/{sid}/compuerta/{gate_id}` |
| `frontend/src/lib/types.ts` | `Clausula`, `Condicion`, `RamaCompuerta`, `EstructuraCompuerta` |
| `frontend/src/lib/api.ts` | `resolverDic08`, `resolverCompuertaCampo`, `resolverCompuertaRamas`, `leerCompuerta`, `camposDelManifiesto` |
| `frontend/src/features/huecos/controles/ConstructorRegla.tsx` (+ `.test.tsx`) | constructor "Y" reutilizable |
| `frontend/src/features/huecos/controles/ControlVisibilidad.tsx` (+ `.test.tsx`) | DIC-08 |
| `frontend/src/features/huecos/controles/ControlCompuerta.tsx` (+ `.test.tsx`) | MMD-04 (2 fases) |
| `frontend/src/features/huecos/TarjetaHueco.tsx` | cablea `DIC-08`/`MMD-04` + enlace "o lo configuro a mano" |
| `tests/test_manifiesto.py`, `test_reglas.py`, `test_validador.py`, `test_compilador.py`, `test_extractor_diccionario.py`, `test_extractor_expediente.py`, `test_sesiones.py`, `test_api.py` | pruebas |

---

## Task 1: `Clausula` + `Condicion.y` en el modelo

**Files:**
- Modify: `src/gpmc/nucleo/manifiesto.py` (bloque `Condicion`, ~línea 53)
- Test: `tests/test_manifiesto.py`

**Interfaces:**
- Produces: `Clausula(BaseModel)` con `campo: str`, `igual: str`,
  `operador: Literal["==", "!="] = "=="`. `Condicion` gana
  `y: list[Clausula] = []`.

- [ ] **Step 1: Prueba que falla** — en `tests/test_manifiesto.py`:

```python
def test_condicion_con_clausulas_y_round_trip(tmp_path):
    from gpmc.nucleo.manifiesto import Condicion, Clausula
    c = Condicion(campo="estado", igual="hidalgo", operador="!=",
                  y=[Clausula(campo="tipo", igual="foraneo")])
    d = c.model_dump()
    assert d["y"][0] == {"campo": "tipo", "igual": "foraneo", "operador": "=="}
    assert Condicion.model_validate(d) == c

def test_condicion_legada_sin_y_sigue_valida():
    from gpmc.nucleo.manifiesto import Condicion
    c = Condicion.model_validate({"campo": "x", "igual": "y"})
    assert c.y == []
    assert c.model_dump(exclude_defaults=True) == {"campo": "x", "igual": "y"}

def test_clausula_no_admite_campo_extra():
    import pytest
    from pydantic import ValidationError
    from gpmc.nucleo.manifiesto import Clausula
    with pytest.raises(ValidationError):
        Clausula(campo="x", igual="y", z=1)
```

- [ ] **Step 2: Ver que falla** — `pytest tests/test_manifiesto.py -k clausula -v` → `ImportError: cannot import name 'Clausula'`.

- [ ] **Step 3: Implementar** — en `manifiesto.py`, justo antes de `class Condicion`:

```python
class Clausula(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campo: str
    igual: str
    operador: Literal["==", "!="] = "=="
```

y en `class Condicion`, tras `operador`:

```python
    y: list[Clausula] = []
```

- [ ] **Step 4: Correr** — `pytest tests/test_manifiesto.py -q` → PASS. `pytest -q` → sin regresiones (329+).

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/manifiesto.py tests/test_manifiesto.py
git commit -m "feat(modelo): Condicion gana clausulas Y opcionales (Clausula)"
```

---

## Task 2: `reglas.emitir` une con `&&` + emisión del compilador

**Files:**
- Modify: `src/gpmc/nucleo/reglas.py` (`emitir`, ~línea 42)
- Test: `tests/test_reglas.py`, `tests/test_compilador.py`

**Interfaces:**
- Consumes: `Condicion.y` (Task 1).
- Produces: `emitir(cond)` devuelve `"@@a=='x'&&@@b!='y'"` cuando `cond.y` no está
  vacío; idéntico a hoy cuando está vacío.

- [ ] **Step 1: Prueba que falla** — `tests/test_reglas.py`:

```python
def test_emitir_una_sola_clausula_no_cambia():
    from gpmc.nucleo.reglas import emitir
    from gpmc.nucleo.manifiesto import Condicion
    assert emitir(Condicion(campo="procede", igual="si")) == "@@procede=='si'"
    assert emitir(Condicion(campo="t", igual="u", operador="!=")) == "@@t!='u'"

def test_emitir_une_las_clausulas_y_con_and():
    from gpmc.nucleo.reglas import emitir, evaluar
    from gpmc.nucleo.manifiesto import Condicion, Clausula
    c = Condicion(campo="estado", igual="hidalgo", operador="!=",
                  y=[Clausula(campo="tipo", igual="foraneo")])
    regla = emitir(c)
    assert regla == "@@estado!='hidalgo'&&@@tipo=='foraneo'"
    assert evaluar(regla, {"estado": "puebla", "tipo": "foraneo"}) is True
    assert evaluar(regla, {"estado": "hidalgo", "tipo": "foraneo"}) is False
    assert evaluar(regla, {"estado": "puebla", "tipo": "local"}) is False
```

- [ ] **Step 2: Ver que falla** — `pytest tests/test_reglas.py -k clausulas_y -v` → `AssertionError` (hoy `emitir` ignora `y`).

- [ ] **Step 3: Implementar** — en `reglas.py`, reescribir `emitir`:

```python
def _emitir_clausula(campo: str, operador: str, igual: str) -> str:
    desigual = operador == "!="
    if SINTAXIS_ESTRICTA:
        op = "!==" if desigual else "==="
        return f"@@{campo}->value {op} '{igual}'"
    op = "!=" if desigual else "=="
    return f"@@{campo}{op}'{igual}'"


def emitir(cond: "Condicion") -> str:
    """Traduce una condicion del manifiesto a la sintaxis de regla del .gpm.

    Une la clausula base y las de `cond.y` con '&&' (conjuncion). El operador de
    cada clausula puede ser '==' o '!='.
    """
    base = _emitir_clausula(cond.campo, getattr(cond, "operador", "=="), cond.igual)
    extra = [
        _emitir_clausula(c.campo, c.operador, c.igual)
        for c in getattr(cond, "y", [])
    ]
    return "&&".join([base, *extra])
```

- [ ] **Step 4: Prueba del compilador** — en `tests/test_compilador.py`, añadir un caso que compile un manifiesto mínimo con un `Campo.condicion_visible` con `y` y un `Conexion.cuando` con `y`, y afirme que el texto del `.gpm` contiene `@@a=='x'&&@@b=='y'` en `dependiente_campo` y en la `regla` de la transición. (Reutilizar el patrón de manifiesto que ya usan las pruebas de `test_compilador.py`.)

- [ ] **Step 5: Correr** — `pytest tests/test_reglas.py tests/test_compilador.py -q` → PASS. `pytest -q` sin regresiones.

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/nucleo/reglas.py tests/test_reglas.py tests/test_compilador.py
git commit -m "feat(reglas): emitir une las clausulas Y con && (compilador incluido)"
```

---

## Task 3: el validador cruzado recorre `y`

**Files:**
- Modify: `src/gpmc/nucleo/manifiesto.py` (validador de `flujo.conexiones`, ~línea 194; y el equivalente de `condicion_visible` si existe)
- Test: `tests/test_validador.py`

**Interfaces:**
- Consumes: `Condicion.y` (Task 1).
- Produces: al validar el manifiesto, una cláusula de `y` que referencia un campo
  no declarado dispara `ValueError`.

- [ ] **Step 1: Prueba que falla** — `tests/test_validador.py`:

```python
def test_una_clausula_y_con_campo_no_declarado_falla():
    import pytest
    from gpmc.nucleo.manifiesto import Manifiesto
    datos = _manifiesto_minimo_valido()   # helper ya presente en el modulo; con 1 campo 'a'
    datos["flujo"]["conexiones"] = [{
        "de": "t1", "a": "t2",
        "cuando": {"campo": "a", "igual": "1", "y": [{"campo": "no_existe", "igual": "9"}]},
    }]
    with pytest.raises(ValueError, match="no_existe"):
        Manifiesto.model_validate(datos)
```

(Si `test_validador.py` no tiene un `_manifiesto_minimo_valido`, tomarlo de la
prueba de "campo no declarado" que ya existe para `cx.cuando.campo` y añadirle la
cláusula `y`.)

- [ ] **Step 2: Ver que falla** — la prueba pasa hoy NO (el validador solo mira `cx.cuando.campo`), así que la condición con `no_existe` en `y` NO lanza → el test falla por "DID NOT RAISE".

- [ ] **Step 3: Implementar** — en el bucle `for cx in self.flujo.conexiones`, sustituir:

```python
            if cx.cuando and cx.cuando.campo not in nombres_campo:
                raise ValueError(
                    f"la condicion de '{cx.de}' usa un campo no declarado: '{cx.cuando.campo}'"
                )
```

por:

```python
            if cx.cuando:
                for campo in [cx.cuando.campo, *(c.campo for c in cx.cuando.y)]:
                    if campo not in nombres_campo:
                        raise ValueError(
                            f"la condicion de '{cx.de}' usa un campo no declarado: '{campo}'"
                        )
```

Si hay un check análogo para `campo.condicion_visible` en el mismo validador,
aplicarle el mismo patrón. Si no lo hay, no se añade (fuera de alcance).

- [ ] **Step 4: Correr** — `pytest tests/test_validador.py -q` → PASS. `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/manifiesto.py tests/test_validador.py
git commit -m "feat(validador): el chequeo de campo no declarado recorre las clausulas Y"
```

---

## Task 4: hueco `DIC-08` con `ubicacion` estructurada

**Files:**
- Modify: `src/gpmc/extractores/diccionario.py` (dos `Hueco("falta_dato", "DIC-08", pantalla.id, …)`, ~líneas 486 y 492)
- Test: `tests/test_extractor_diccionario.py`

**Interfaces:**
- Produces: los huecos `DIC-08` llevan `ubicacion = f"{pantalla.id}::{nombre}"`
  (antes `pantalla.id`). El mensaje no cambia.

- [ ] **Step 1: Prueba que falla** — `tests/test_extractor_diccionario.py`:

```python
def test_dic08_lleva_pantalla_y_campo_en_la_ubicacion(tmp_path):
    # Un Diccionario con una condicion de visibilidad en prosa que el parser no
    # interpreta -> DIC-08. Reutilizar el fixture que ya provoca DIC-08 en este
    # modulo (buscar 'DIC-08' en el archivo) y afirmar la ubicacion.
    r = _extraer_diccionario_con_visibilidad_rara(tmp_path)
    dic08 = [h for h in r.huecos if h.codigo == "DIC-08"]
    assert dic08, "esperaba un DIC-08"
    assert "::" in dic08[0].ubicacion
    pantalla, campo = dic08[0].ubicacion.split("::", 1)
    assert pantalla and campo
```

- [ ] **Step 2: Ver que falla** — `AssertionError: assert '::' in 'p1'`.

- [ ] **Step 3: Implementar** — en los dos sitios, cambiar el 3º argumento de
  `pantalla.id` a `f"{pantalla.id}::{nombre}"`. `nombre` está en scope en ambos
  (es el nombre del campo que se está construyendo).

- [ ] **Step 4: Correr** — `pytest tests/test_extractor_diccionario.py -q` → PASS.
  `pytest -q` — puede haber pruebas que afirmen `ubicacion == "p1"` para DIC-08;
  actualizarlas al nuevo formato (no es ablandar: es el cambio de contrato de
  este task).

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/extractores/diccionario.py tests/test_extractor_diccionario.py
git commit -m "feat(extractor): DIC-08 lleva pantalla::campo en la ubicacion"
```

---

## Task 5: `_flujo_ramificado(overrides)` + `ramas_de_compuerta`

**Files:**
- Modify: `src/gpmc/extractores/expediente.py` (`_flujo_ramificado`, ~línea 62)
- Test: `tests/test_extractor_expediente.py`

**Interfaces:**
- Produces:
  - `_flujo_ramificado(rm, pantallas, overrides: Optional[dict[str, str]] = None)`
    — si `overrides` trae `{gate_id: nombre_campo}`, ese campo se usa como el
    `@@campo` de la compuerta aunque el Mermaid no lo nombre.
  - `ramas_de_compuerta(rm, pantallas, gate_id) -> Optional[dict]` con forma
    `{"predecesora": str, "ramas": [{"a": str, "a_nombre": str, "etiqueta": str}]}`.

- [ ] **Step 1: Prueba que falla** — `tests/test_extractor_expediente.py`. Usar un
  `rm` (resultado de `mermaid.extraer`) con una compuerta SIN `@@campo` y ramas
  con etiquetas que sí casan con un catálogo, y `pantallas` con ese campo:

```python
def test_flujo_ramificado_usa_el_override_de_compuerta():
    rm, pantallas = _mermaid_con_compuerta_sin_campo()   # helper local nuevo
    assert _flujo_ramificado(rm, pantallas) is None      # sin override: MMD-04
    tareas, conexiones, _ = _flujo_ramificado(
        rm, pantallas, overrides={"g1": "procede"})
    assert any(cx.cuando and cx.cuando.campo == "procede" for cx in conexiones)

def test_ramas_de_compuerta_devuelve_predecesora_y_ramas():
    rm, pantallas = _mermaid_con_compuerta_sin_campo()
    est = ramas_de_compuerta(rm, pantallas, "g1")
    assert est["predecesora"]
    assert {r["etiqueta"] for r in est["ramas"]} == {"si", "no"}   # segun el fixture
    assert ramas_de_compuerta(rm, pantallas, "no_existe") is None
```

- [ ] **Step 2: Ver que falla** — `TypeError: _flujo_ramificado() got an unexpected keyword argument 'overrides'`.

- [ ] **Step 3: Implementar** —
  - Firma: `def _flujo_ramificado(rm, pantallas, overrides=None):`. Al inicio,
    `overrides = overrides or {}`.
  - En el check de la condición 2, antes de mirar `g.campos`, construir el campo
    efectivo: `campos_gate = [overrides[g.id]] if g.id in overrides else list(g.campos)`
    y usar `campos_gate` en lugar de `g.campos` en ese check y donde se lee
    `compuertas[a.de].campos[0]` (usar el override si aplica). Copia local; no
    mutar `rm`.
  - `ramas_de_compuerta(rm, pantallas, gate_id)`: si `gate_id` no es un nodo
    `clase_nodo == "compuerta"`, devolver `None`. Predecesora = `a.de` de la
    arista cuyo `a.a == gate_id` y `a.de` es tarea. Ramas = por cada arista con
    `a.de == gate_id`: `{"a": arista.a, "a_nombre": <texto del nodo destino o
    nombre de la pantalla mapeada>, "etiqueta": arista.etiqueta or ""}`.
    Reutilizar `_mapear_nodos_a_pantallas` para `a_nombre` cuando el destino sea
    una tarea.

- [ ] **Step 4: Correr** — `pytest tests/test_extractor_expediente.py -q` → PASS.
  `pytest -q` sin regresiones (el `overrides=None` por defecto no cambia nada).

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/extractores/expediente.py tests/test_extractor_expediente.py
git commit -m "feat(extractor): _flujo_ramificado acepta override de campo de compuerta + ramas_de_compuerta"
```

---

## Task 6: helpers de sesión `compuertas.json` + `reensamblar_flujo`

**Files:**
- Modify: `src/gpmc/web/sesiones.py`
- Create: `src/gpmc/web/reensamblado.py`
- Test: `tests/test_sesiones.py`

**Interfaces:**
- Consumes: `_flujo_ramificado(overrides=)` (Task 5); `carpeta_de`,
  `manifiesto_de` (SP1).
- Produces:
  - `compuertas_de(carpeta: Path) -> dict[str, str]` — lee `compuertas.json`
    (`{}` si no existe).
  - `escribir_compuertas(carpeta: Path, d: dict[str, str]) -> None`.
  - `reensamblar_flujo(carpeta: Path, m: Manifiesto) -> Manifiesto` — re-parsea el
    Mermaid del TO-BE de `carpeta`, aplica `compuertas_de(carpeta)` como
    `overrides`, corre `_flujo_ramificado`; si devuelve un `Flujo`, reemplaza
    `m.flujo` y devuelve `m`; si `None`, devuelve `m` intacto.

- [ ] **Step 1: Prueba que falla** — `tests/test_sesiones.py`:

```python
def test_compuertas_json_round_trip(tmp_path):
    from gpmc.web.sesiones import compuertas_de, escribir_compuertas
    assert compuertas_de(tmp_path) == {}
    escribir_compuertas(tmp_path, {"g1": "procede"})
    assert compuertas_de(tmp_path) == {"g1": "procede"}
```

- [ ] **Step 2: Ver que falla** — `ImportError`.

- [ ] **Step 3: Implementar** —
  - En `sesiones.py`, `compuertas_de` / `escribir_compuertas` copiando el patrón
    de `reconocidos_de` / `escribir_reconocidos` (JSON en `carpeta / "compuertas.json"`).
  - `reensamblado.py`: `reensamblar_flujo(carpeta, m)`. Localiza el `.md` del
    TO-BE en `carpeta` (el mismo criterio que usa la extracción; si la carpeta
    guarda el nombre del insumo, usarlo). `mermaid.extraer(texto)` → `rm`.
    `_flujo_ramificado(rm, [p for p in m.pantallas], overrides=compuertas_de(carpeta))`.
    Si no es `None`, construir el `Flujo` nuevo (`tareas`, `conexiones`) y
    `m.flujo = nuevo`. Devolver `m`. Documentar que si no hay `.md` de TO-BE en
    la carpeta (expediente subido solo con Diccionario), devuelve `m` intacto.

- [ ] **Step 4: Correr** — `pytest tests/test_sesiones.py -q` → PASS. `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/sesiones.py src/gpmc/web/reensamblado.py tests/test_sesiones.py
git commit -m "feat(web): compuertas.json + reensamblar_flujo (re-corre la ramificacion con overrides)"
```

---

## Task 7: API — `resolver` tipo `dic08`

**Files:**
- Modify: `src/gpmc/web/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `Condicion`/`Clausula` (Task 1); `carpeta_de`, `manifiesto_de`,
  `huecos_vivos`, `HuecoOut`, `guardar` (SP1).
- Produces: `POST /api/v1/expedientes/{sid}/resolver` acepta
  `{tipo: "dic08", ubicacion: "pantalla::campo", condicion: Condicion}` →
  `200 {manifiesto, huecos}`; pone `condicion_visible` en ese campo y quita el
  hueco `DIC-08` de esa `ubicacion`. `422 {error}` si el campo no existe.

- [ ] **Step 1: Prueba que falla** — `tests/test_api.py`. Crear un expediente que
  traiga un `DIC-08` (fixture con visibilidad rara), leer su `ubicacion`,
  resolver:

```python
def test_resolver_dic08_pone_la_condicion_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_DIC08).json()
    sid = est["sid"]
    ubic = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ubic,
        "condicion": {"campo": "estado", "igual": "hidalgo", "operador": "!=",
                      "y": [{"campo": "tipo_solicitante", "igual": "foraneo"}]},
    }]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "DIC-08" and h["ubicacion"] == ubic
                   for h in body["huecos"])
    pantalla_id, campo = ubic.split("::", 1)
    p = next(p for p in body["manifiesto"]["pantallas"] if p["id"] == pantalla_id)
    cv = next(cc for cc in p["campos"] if cc["nombre"] == campo)["condicion_visible"]
    assert cv["campo"] == "estado" and cv["y"][0]["campo"] == "tipo_solicitante"

def test_resolver_dic08_campo_inexistente_da_422(tmp_path):
    c = _cli(tmp_path)
    sid = c.post("/api/v1/expedientes", files=_INSUMOS_CON_DIC08).json()["sid"]
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": "p1::no_existe",
        "condicion": {"campo": "estado", "igual": "x"}}]})
    assert r.status_code == 422 and "error" in r.json()
```

- [ ] **Step 2: Ver que falla** — el `tipo` `dic08` no existe → Pydantic 422 por
  discriminador, o el handler lo ignora. La prueba falla.

- [ ] **Step 3: Implementar** —
  - `Resolucion` pasa a `Union` discriminada por `tipo` (o, más simple: un
    modelo con `tipo: str` y campos opcionales `valor`, `campo`, `condicion`,
    `ramas`, validado en el handler). Recomendado: modelos separados
    `ResolucionSimple` (SP1) y `ResolucionDic08`, unidos con
    `Field(discriminator="tipo")`.
  - `ResolucionDic08`: `tipo: Literal["dic08"]`, `ubicacion: str`,
    `condicion: Condicion`.
  - En el handler de `resolver`, por cada resolución `dic08`: partir `ubicacion`
    por `::`; localizar la pantalla y el campo; si no existe →
    `HTTPException(422, {"error": ...})`; `campo.condicion_visible = condicion`;
    `guardar(m, carpeta / "manifiesto.yaml")`; quitar de `huecos.json` el par
    `("DIC-08", ubicacion)`.
  - Respuesta: `{manifiesto: m.model_dump(mode="json"), huecos: [...huecos_vivos...]}`
    (igual que SP1).

- [ ] **Step 4: Correr** — `pytest tests/test_api.py -q` → PASS. `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/api.py tests/test_api.py
git commit -m "feat(api): resolver acepta tipo dic08 (condicion_visible con Y)"
```

---

## Task 8: API — `resolver` tipo `mmd04campo`

**Files:**
- Modify: `src/gpmc/web/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `compuertas_de`/`escribir_compuertas`, `reensamblar_flujo` (Task 6).
- Produces: `{tipo: "mmd04campo", ubicacion: gate_id, campo: str}` → escribe el
  override, corre `reensamblar_flujo`, guarda, quita los `MMD-04`/`FLU-01`/`FLU-02`
  que ya no apliquen. `200 {manifiesto, huecos}`. `422` si el `campo` no está en
  el manifiesto.

- [ ] **Step 1: Prueba que falla** — `tests/test_api.py`, con un expediente cuyo
  TO-BE tiene una compuerta sin `@@campo` y etiquetas resolubles:

```python
def test_resolver_mmd04campo_reensambla_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "procede"}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "MMD-04" for h in body["huecos"])
    assert any(cx.get("cuando", {}).get("campo") == "procede"
               for cx in body["manifiesto"]["flujo"]["conexiones"])

def test_resolver_mmd04campo_campo_inexistente_da_422(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "no_existe"}]})
    assert r.status_code == 422
```

- [ ] **Step 2: Ver que falla** — `tipo` desconocido.

- [ ] **Step 3: Implementar** — `ResolucionMmd04Campo`:
  `tipo: Literal["mmd04campo"]`, `ubicacion: str` (gate id), `campo: str`.
  En el handler:
  - Validar que `campo` está en `{c.nombre for p in m.pantallas for c in p.campos}`
    → si no, `422`.
  - `d = compuertas_de(carpeta); d[ubicacion] = campo; escribir_compuertas(carpeta, d)`.
  - `m = reensamblar_flujo(carpeta, m)`.
  - `guardar(m, carpeta / "manifiesto.yaml")`.
  - Recalcular huecos: re-correr el linter de flujo o, más simple, quitar de
    `huecos.json` los `("MMD-04", ubicacion)` y —si `reensamblar_flujo` produjo
    un flujo ramificado— los `("FLU-01","flujo")` / `("FLU-02","flujo")`.
    Regla concreta: si tras reensamblar `m.flujo.conexiones` tiene alguna
    `cuando`, se consideran resueltos `FLU-01`/`FLU-02`.
  - Respuesta estándar `{manifiesto, huecos}`.

- [ ] **Step 4: Correr** — `pytest tests/test_api.py -q` → PASS. `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/api.py tests/test_api.py
git commit -m "feat(api): resolver acepta tipo mmd04campo (override + reensamblado)"
```

---

## Task 9: API — `resolver` tipo `mmd04rama` + `GET /compuerta/{gate_id}`

**Files:**
- Modify: `src/gpmc/web/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `ramas_de_compuerta` (Task 5); `Condicion` (Task 1).
- Produces:
  - `GET /api/v1/expedientes/{sid}/compuerta/{gate_id}` →
    `200 {predecesora, ramas: [{a, a_nombre, etiqueta}]}`; `404` si el sid o el
    gate no existen.
  - `{tipo: "mmd04rama", ubicacion: gate_id, ramas: [{a: str, condicion: Condicion}]}`
    → reescribe las conexiones de esa compuerta (quita la que la saltaba, añade
    una `Conexion(de=predecesora, a=rama.a, cuando=rama.condicion)` por rama),
    guarda, quita el `MMD-04`. `422` si una `a` no es rama de esa compuerta.

- [ ] **Step 1: Prueba que falla** — `tests/test_api.py`:

```python
def test_leer_compuerta_devuelve_predecesora_y_ramas(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04_ETIQUETAS_RARAS).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    r = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}")
    assert r.status_code == 200
    body = r.json()
    assert body["predecesora"]
    assert len(body["ramas"]) >= 2 and all("a_nombre" in x for x in body["ramas"])
    assert c.get(f"/api/v1/expedientes/{sid}/compuerta/no_existe").status_code == 404

def test_resolver_mmd04rama_inyecta_condiciones_y_quita_el_hueco(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_MMD04_ETIQUETAS_RARAS).json()
    sid = est["sid"]
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    ramas = c.get(f"/api/v1/expedientes/{sid}/compuerta/{gate}").json()["ramas"]
    payload = {"tipo": "mmd04rama", "ubicacion": gate, "ramas": [
        {"a": ramas[0]["a"], "condicion": {"campo": "procede", "igual": "si"}},
        {"a": ramas[1]["a"], "condicion": {"campo": "procede", "igual": "no"}},
    ]}
    r = c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [payload]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(h["codigo"] == "MMD-04" for h in body["huecos"])
    cx = body["manifiesto"]["flujo"]["conexiones"]
    assert sum(1 for x in cx if x.get("cuando")) >= 2
```

- [ ] **Step 2: Ver que falla** — `404` en `/compuerta/...` (ruta no existe).

- [ ] **Step 3: Implementar** —
  - `crear_router` gana `@router.get("/expedientes/{sid}/compuerta/{gate_id}")`:
    carga el manifiesto; re-parsea el Mermaid del TO-BE de la carpeta;
    `est = ramas_de_compuerta(rm, m.pantallas, gate_id)`; `404` si `est is None`;
    devuelve `est`.
  - `ResolucionMmd04Rama`: `tipo: Literal["mmd04rama"]`, `ubicacion: str`,
    `ramas: list[RamaResuelta]` con `RamaResuelta(a: str, condicion: Condicion)`.
  - En el handler: `est = ramas_de_compuerta(rm, m.pantallas, ubicacion)`; `422`
    si `est is None` o si alguna `rama.a` no está en `{r["a"] for r in est["ramas"]}`.
    Quitar de `m.flujo.conexiones` la conexión `de == est["predecesora"]` que
    apuntaba a la rama única del flujo lineal; por cada `rama`, añadir
    `Conexion(de=est["predecesora"], a=rama.a, cuando=rama.condicion)`.
    `guardar`; quitar `("MMD-04", ubicacion)` de `huecos.json`.
  - Respuesta estándar.

- [ ] **Step 4: Correr** — `pytest tests/test_api.py -q` → PASS. `pytest -q` sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/api.py tests/test_api.py
git commit -m "feat(api): GET /compuerta/{id} + resolver tipo mmd04rama (condicion por rama)"
```

---

## Task 10: cliente tipado — `types.ts`, `api.ts`, `camposDelManifiesto`

**Files:**
- Modify: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Clausula = {campo: string; igual: string; operador: "=="|"!="}`;
    `Condicion = Clausula & {y: Clausula[]}`;
    `RamaCompuerta = {a: string; a_nombre: string; etiqueta: string}`;
    `EstructuraCompuerta = {predecesora: string; ramas: RamaCompuerta[]}`.
  - `api.ts`: `resolverDic08(sid, ubicacion, condicion)`,
    `resolverCompuertaCampo(sid, gateId, campo)`,
    `resolverCompuertaRamas(sid, gateId, ramas: {a, condicion}[])`,
    `leerCompuerta(sid, gateId): Promise<EstructuraCompuerta>`,
    `camposDelManifiesto(manifiesto): {nombre, etiqueta, catalogo: {etiqueta, valor}[]}[]`.

- [ ] **Step 1: Prueba que falla** — `frontend/src/lib/api.test.ts`:

```ts
it("resolverDic08 postea la resolucion con la condicion", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => ({ manifiesto: {}, huecos: [] }) });
  vi.stubGlobal("fetch", fetchMock);
  await resolverDic08("a".repeat(16), "p1::estado",
    { campo: "estado", igual: "hidalgo", operador: "!=", y: [] });
  const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
  expect(body.resoluciones[0]).toMatchObject(
    { tipo: "dic08", ubicacion: "p1::estado" });
});

it("camposDelManifiesto aplana pantallas y catalogos", () => {
  const m = { pantallas: [{ campos: [
    { nombre: "estado", etiqueta: "Estado",
      catalogo: [{ etiqueta: "Hidalgo", valor: "hidalgo" }] }] }] };
  const cs = camposDelManifiesto(m as unknown as Record<string, unknown>);
  expect(cs).toEqual([{ nombre: "estado", etiqueta: "Estado",
    catalogo: [{ etiqueta: "Hidalgo", valor: "hidalgo" }] }]);
});
```

- [ ] **Step 2: Ver que falla** — `Cannot find name 'resolverDic08'`.

- [ ] **Step 3: Implementar** — añadir los tipos a `types.ts`; en `api.ts`,
  las 4 funciones sobre el helper `pedirJson` de SP1 (POST a
  `/api/v1/expedientes/{sid}/resolver` con `{resoluciones: [...]}` para las de
  resolver; GET para `leerCompuerta`). `camposDelManifiesto` con narrowing
  (`Array.isArray`, `typeof`) sobre `Record<string, unknown>`; catálogo ausente
  → `[]`.

- [ ] **Step 4: Correr** — `cd frontend && npx vitest run src/lib` → PASS.
  `bash scripts/check-frontend.sh` → verde.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib
git commit -m "feat(frontend): cliente tipado para dic08/mmd04 + camposDelManifiesto"
```

---

## Task 11: `ConstructorRegla.tsx`

**Files:**
- Create: `frontend/src/features/huecos/controles/ConstructorRegla.tsx`,
  `ConstructorRegla.test.tsx`

**Interfaces:**
- Consumes: `Condicion`, `Clausula` (Task 10); `Select`, `Input`, `Button` de
  `@/components/ui/*`.
- Produces: `<ConstructorRegla campos={...} value={Condicion|null} onChange={(c: Condicion)=>void} />`.

- [ ] **Step 1: Prueba que falla** — `ConstructorRegla.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import ConstructorRegla from "./ConstructorRegla";

const campos = [
  { nombre: "estado", etiqueta: "Estado",
    catalogo: [{ etiqueta: "Hidalgo", valor: "hidalgo" },
               { etiqueta: "Otro", valor: "otro" }] },
  { nombre: "folio", etiqueta: "Folio", catalogo: [] },
];

it("emite una Condicion con clausula Y al añadir una fila", async () => {
  const onChange = vi.fn();
  render(<ConstructorRegla campos={campos} value={null} onChange={onChange} />);
  // fila 1: estado != hidalgo
  await userEvent.selectOptions(screen.getByLabelText(/campo 1/i), "estado");
  await userEvent.selectOptions(screen.getByLabelText(/operador 1/i), "!=");
  await userEvent.selectOptions(screen.getByLabelText(/valor 1/i), "hidalgo");
  await userEvent.click(screen.getByRole("button", { name: /añadir.*y/i }));
  // fila 2: folio == 123 (texto libre, sin catalogo)
  await userEvent.selectOptions(screen.getByLabelText(/campo 2/i), "folio");
  await userEvent.type(screen.getByLabelText(/valor 2/i), "123");
  const ultima = onChange.mock.calls.at(-1)[0];
  expect(ultima).toEqual({
    campo: "estado", operador: "!=", igual: "hidalgo",
    y: [{ campo: "folio", operador: "==", igual: "123" }],
  });
});

it("el valor es un select si el campo tiene catalogo y un input si no", async () => {
  render(<ConstructorRegla campos={campos} value={null} onChange={vi.fn()} />);
  await userEvent.selectOptions(screen.getByLabelText(/campo 1/i), "estado");
  expect(screen.getByLabelText(/valor 1/i).tagName).toBe("SELECT");
  await userEvent.selectOptions(screen.getByLabelText(/campo 1/i), "folio");
  expect(screen.getByLabelText(/valor 1/i).tagName).toBe("INPUT");
});
```

- [ ] **Step 2: Ver que falla** — módulo no existe.

- [ ] **Step 3: Implementar** — estado local `filas: {campo, operador, igual}[]`
  (sembrado de `value` si viene, si no `[{campo:"",operador:"==",igual:""}]`).
  Cada fila: `<label>` accesible "Campo N" / "Operador N" / "Valor N";
  `Select` de `campos` por nombre; `Select` `==`/`!=`; valor = `Select` de
  `catalogo` si el campo elegido tiene catálogo (no vacío), si no `Input` texto.
  Botón "Añadir Y" (`name` casa `/añadir.*y/i`); "×" por fila (menos la 1ª).
  En cada cambio: filtrar filas completas (`campo` y `igual` no vacíos), y si hay
  ≥1, llamar `onChange({...fila0, y: filasRestantes})`. Colores por token; sin hex.

- [ ] **Step 4: Correr** — `cd frontend && npx vitest run src/features/huecos/controles`
  → PASS. `bash scripts/check-frontend.sh` → verde.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/controles/ConstructorRegla.tsx frontend/src/features/huecos/controles/ConstructorRegla.test.tsx
git commit -m "feat(frontend): ConstructorRegla — constructor de condiciones con Y"
```

---

## Task 12: `ControlVisibilidad.tsx` (DIC-08) + cableado

**Files:**
- Create: `frontend/src/features/huecos/controles/ControlVisibilidad.tsx`,
  `ControlVisibilidad.test.tsx`
- Modify: `frontend/src/features/huecos/TarjetaHueco.tsx`

**Interfaces:**
- Consumes: `ConstructorRegla` (Task 11); `resolverDic08`, `camposDelManifiesto`
  (Task 10).
- Produces: `<ControlVisibilidad hueco={Hueco} sid={string} manifiesto={...} onResuelto={(resp)=>void} />`.
  `TarjetaHueco` enruta `codigo === "DIC-08"` a este control.

- [ ] **Step 1: Prueba que falla** — `ControlVisibilidad.test.tsx`:

```tsx
vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  camposDelManifiesto: () => ([
    { nombre: "estado", etiqueta: "Estado", catalogo: [] }]),
}));

it("muestra la frase cruda y al guardar llama resolverDic08", async () => {
  const { resolverDic08 } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(<ControlVisibilidad
    hueco={{ nivel: "falta_dato", codigo: "DIC-08", ubicacion: "p1::domicilio",
             mensaje: "no se pudo interpretar: «visible si es de otro estado»",
             propuesta: null }}
    sid={"a".repeat(16)} manifiesto={{}} onResuelto={onResuelto} />);
  expect(screen.getByText(/otro estado/)).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText(/campo 1/i), "estado");
  await userEvent.type(screen.getByLabelText(/valor 1/i), "hidalgo");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolverDic08).toHaveBeenCalledWith(
    "a".repeat(16), "p1::domicilio",
    expect.objectContaining({ campo: "estado", igual: "hidalgo" }));
  expect(onResuelto).toHaveBeenCalled();
});
```

- [ ] **Step 2: Ver que falla** — módulo no existe.

- [ ] **Step 3: Implementar** — el control muestra `hueco.mensaje` (la frase cruda
  va dentro), un `ConstructorRegla` con `campos={camposDelManifiesto(manifiesto)}`,
  y "Guardar" (deshabilitado sin condición válida). `onClick` →
  `resolverDic08(sid, hueco.ubicacion, condicion)` → `onResuelto(resp)`; `catch`
  con `ErrorApi` como en SP1. En `TarjetaHueco`, añadir la rama
  `codigo === "DIC-08"` al switch, pasándole `sid`, `manifiesto`, `onResuelto`.

- [ ] **Step 4: Correr** — `npx vitest run src/features/huecos` → PASS.
  `bash scripts/check-frontend.sh` → verde.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/controles/ControlVisibilidad.tsx frontend/src/features/huecos/controles/ControlVisibilidad.test.tsx frontend/src/features/huecos/TarjetaHueco.tsx
git commit -m "feat(frontend): ControlVisibilidad (DIC-08) cableado en TarjetaHueco"
```

---

## Task 13: `ControlCompuerta.tsx` (MMD-04, 2 fases) + cableado

**Files:**
- Create: `frontend/src/features/huecos/controles/ControlCompuerta.tsx`,
  `ControlCompuerta.test.tsx`
- Modify: `frontend/src/features/huecos/TarjetaHueco.tsx`

**Interfaces:**
- Consumes: `ConstructorRegla` (Task 11); `resolverCompuertaCampo`,
  `resolverCompuertaRamas`, `leerCompuerta`, `camposDelManifiesto` (Task 10).
- Produces: `<ControlCompuerta hueco={Hueco} sid={string} manifiesto={...} onResuelto={(resp)=>void} />`.
  `TarjetaHueco` enruta `codigo === "MMD-04"` a este control.

- [ ] **Step 1: Prueba que falla** — `ControlCompuerta.test.tsx`:

```tsx
const respConHueco = { manifiesto: {}, huecos: [
  { nivel: "falta_dato", codigo: "MMD-04", ubicacion: "g1", mensaje: "x", propuesta: null }] };
const respSinHueco = { manifiesto: {}, huecos: [] };

vi.mock("@/lib/api", () => ({
  resolverCompuertaCampo: vi.fn(),
  resolverCompuertaRamas: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  leerCompuerta: vi.fn().mockResolvedValue({ predecesora: "t1", ramas: [
    { a: "t2", a_nombre: "Aprobar", etiqueta: "procede" },
    { a: "t3", a_nombre: "Rechazar", etiqueta: "no procede" }] }),
  camposDelManifiesto: () => ([{ nombre: "procede", etiqueta: "Procede", catalogo: [] }]),
}));

it("fase 1: elegir campo llama resolverCompuertaCampo; si basta, sube el estado", async () => {
  const { resolverCompuertaCampo } = await import("@/lib/api");
  (resolverCompuertaCampo as any).mockResolvedValue(respSinHueco);
  const onResuelto = vi.fn();
  render(<ControlCompuerta hueco={respConHueco.huecos[0]} sid={"a".repeat(16)}
    manifiesto={{}} onResuelto={onResuelto} />);
  await userEvent.selectOptions(screen.getByLabelText(/campo de la compuerta/i), "procede");
  await userEvent.click(screen.getByRole("button", { name: /usar este campo/i }));
  expect(resolverCompuertaCampo).toHaveBeenCalledWith("a".repeat(16), "g1", "procede");
  expect(onResuelto).toHaveBeenCalledWith(respSinHueco);
});

it("fase 2: si el campo no basta, aparece el constructor por rama", async () => {
  const { resolverCompuertaCampo, leerCompuerta, resolverCompuertaRamas } =
    await import("@/lib/api");
  (resolverCompuertaCampo as any).mockResolvedValue(respConHueco);   // sigue el MMD-04
  render(<ControlCompuerta hueco={respConHueco.huecos[0]} sid={"a".repeat(16)}
    manifiesto={{}} onResuelto={vi.fn()} />);
  await userEvent.selectOptions(screen.getByLabelText(/campo de la compuerta/i), "procede");
  await userEvent.click(screen.getByRole("button", { name: /usar este campo/i }));
  expect(await screen.findByText(/no resolvieron solas/i)).toBeInTheDocument();
  expect(leerCompuerta).toHaveBeenCalled();
  // una fila de constructor por rama (Aprobar / Rechazar)
  expect(await screen.findByText(/Aprobar/)).toBeInTheDocument();
  await userEvent.selectOptions(screen.getAllByLabelText(/campo 1/i)[0], "procede");
  await userEvent.type(screen.getAllByLabelText(/valor 1/i)[0], "si");
  await userEvent.selectOptions(screen.getAllByLabelText(/campo 1/i)[1], "procede");
  await userEvent.type(screen.getAllByLabelText(/valor 1/i)[1], "no");
  await userEvent.click(screen.getByRole("button", { name: /guardar ramas/i }));
  expect(resolverCompuertaRamas).toHaveBeenCalledWith("a".repeat(16), "g1",
    expect.arrayContaining([expect.objectContaining({ a: "t2" })]));
});
```

- [ ] **Step 2: Ver que falla** — módulo no existe.

- [ ] **Step 3: Implementar** — estado `fase: 1 | 2`. Fase 1: `<Select>` "Campo de
  la compuerta" (de `camposDelManifiesto`) + botón "Usar este campo" →
  `resolverCompuertaCampo(sid, hueco.ubicacion, campo)`; si
  `resp.huecos` sigue con un `MMD-04` de `hueco.ubicacion` → `setFase(2)` y
  `leerCompuerta(sid, hueco.ubicacion)`; si no → `onResuelto(resp)`.
  Fase 2: aviso "las ramas no resolvieron solas", y por cada `rama` de la
  estructura, `→ {a_nombre} (etiqueta "{etiqueta}")` + un `ConstructorRegla`;
  botón "Guardar ramas" → `resolverCompuertaRamas(sid, hueco.ubicacion,
  ramas.map(r => ({a: r.a, condicion: condPorRama[r.a]})))` → `onResuelto(resp)`.
  `ErrorApi` como SP1. En `TarjetaHueco`, rama `codigo === "MMD-04"`.

- [ ] **Step 4: Correr** — `npx vitest run src/features/huecos` → PASS.
  `bash scripts/check-frontend.sh` → verde.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/controles/ControlCompuerta.tsx frontend/src/features/huecos/controles/ControlCompuerta.test.tsx frontend/src/features/huecos/TarjetaHueco.tsx
git commit -m "feat(frontend): ControlCompuerta (MMD-04, campo + respaldo por rama)"
```

---

## Task 14: integración "cero clics" + escape hatch + docs

**Files:**
- Modify: `frontend/src/features/huecos/TarjetaHueco.tsx` (enlace "o lo configuro a mano" en DIC-08/MMD-04)
- Modify: `frontend/src/features/huecos/TarjetaHueco.test.tsx` (o el de cada control)
- Test: `tests/test_api.py` (integración end-to-end)
- Modify: `CLAUDE.md` (sección de huecos / "a mano") — **requiere aprobación humana; el ejecutor la pide**

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: la prueba de que un expediente con `DIC-08` + `MMD-04` compila a un
  `.gpm` sin `falta_dato` tras usar la API; y el enlace de escape en las tarjetas.

- [ ] **Step 1: Prueba de integración que falla** — `tests/test_api.py`:

```python
def test_cero_clics_dic08_y_mmd04_compila_gpm_completo(tmp_path):
    c = _cli(tmp_path)
    est = c.post("/api/v1/expedientes", files=_INSUMOS_CON_DIC08_Y_MMD04).json()
    sid = est["sid"]
    assert any(h["codigo"] == "DIC-08" for h in est["huecos"])
    assert any(h["codigo"] == "MMD-04" for h in est["huecos"])
    ub = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "DIC-08")
    gate = next(h["ubicacion"] for h in est["huecos"] if h["codigo"] == "MMD-04")
    c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "dic08", "ubicacion": ub,
        "condicion": {"campo": "estado", "igual": "hidalgo", "operador": "!="}}]})
    c.post(f"/api/v1/expedientes/{sid}/resolver", json={"resoluciones": [{
        "tipo": "mmd04campo", "ubicacion": gate, "campo": "procede"}]})
    r = c.get(f"/api/v1/expedientes/{sid}/gpm")
    assert r.status_code == 200, r.text          # la puerta del linter ya deja pasar
```

- [ ] **Step 2: Ver que falla / pasa** — si Tasks 7–9 quedaron bien, puede pasar
  directo; si falla, es un hueco `falta_dato` residual (revisar el barrido de
  `huecos.json` en `mmd04campo`).

- [ ] **Step 3: Escape hatch** — en `TarjetaHueco`, para `DIC-08` y `MMD-04`,
  debajo del control, un enlace pequeño "o lo configuro a mano" que llama al
  `reconocer` de SP1 (`reconocer(sid, hueco.codigo, hueco.ubicacion)` →
  `onResuelto`). Prueba: click en el enlace llama `reconocer` con esos args.

- [ ] **Step 4: `CLAUDE.md`** — actualizar la nota sobre "configuración a mano":
  `DIC-08` y `MMD-04` ya se resuelven en el wizard (constructor de reglas);
  `FLU-01` y `API-05` siguen siendo "a mano" hasta su sub-proyecto. **Pedir
  aprobación humana antes de commitear el cambio de `CLAUDE.md`.**

- [ ] **Step 5: Correr TODO** — `.venv/bin/pytest -q` (verde, ≥ 329 + nuevas) y
  `bash scripts/check-frontend.sh` (verde).

- [ ] **Step 6: Commit**

```bash
git add tests/test_api.py frontend/src/features/huecos CLAUDE.md
git commit -m "feat(sp2): integracion cero-clics DIC-08+MMD-04 + escape hatch"
```

---

## Verificación final (tras las 14 tasks)

1. `.venv/bin/pytest -q` → verde, sin regresiones, con las pruebas nuevas.
2. `bash scripts/check-frontend.sh` → exit 0.
3. **End-to-end manual:** `cd frontend && npm run build`; `gpmc servir`; subir un
   expediente con visibilidad rara + compuerta sin `@@campo`; resolver ambos en
   el wizard sin recarga; descargar el `.gpm`; abrirlo y confirmar que lleva la
   condición de visibilidad (`dependiente_campo` con `&&` si hubo "Y") y la
   transición condicional.
4. **Plataforma (ritual del usuario):** importar ese `.gpm` a
   `modelador.hidalgo.gob.mx` y al portal del ciudadano; confirmar que la
   visibilidad y la rama disparan sin tocar el modelador. Acta en
   `planeacion/actas/`.

## Self-review del plan

- **Cobertura del spec:** §3 modelo → Tasks 1–3. §4 extractor/compilador → Tasks
  2 (compilador), 4 (DIC-08), 5 (`_flujo_ramificado`/`ramas`), 6 (reensamblado).
  §5 API → Tasks 7–9. §6 componentes → Tasks 10–13. §7 pruebas → cada task +
  Task 14. §8 riesgos → cubiertos por las pruebas de retrocompat (Task 1–2), la
  validación 422 (Tasks 7–9) y la de "fila incompleta" (Task 11). ✔
- **Sin placeholders:** los `_INSUMOS_CON_*` y `_mermaid_con_compuerta_sin_campo`
  son fixtures a construir en la primera task que los usa, con la forma descrita
  (Diccionario con `@@`, TO-BE con compuerta sin `@@campo` y etiquetas de arista
  = valores de catálogo / Sí-No). El ejecutor los arma reutilizando el estilo de
  `tests/test_cli.py::_exp_limpio` y `tests/test_extractor_mermaid.py`. No hay
  "TBD".
- **Consistencia de tipos:** `Condicion` (Pydantic, Task 1) ↔ `Condicion` (TS,
  Task 10): mismos campos, `y: Clausula[]`. `tipo` de `Resolucion`
  (`dic08`/`mmd04campo`/`mmd04rama`) igual en `api.py` (Tasks 7–9) y en `api.ts`
  (Task 10). `EstructuraCompuerta` (`predecesora`, `ramas[{a,a_nombre,etiqueta}]`)
  igual en `ramas_de_compuerta` (Task 5), el endpoint (Task 9) y `types.ts`
  (Task 10). ✔
- **Orden:** 1→2→3 (modelo antes que emisor/validador); 5→6 (helper antes que
  reensamblado); 6→8 (reensamblado antes que `mmd04campo`); 5→9 (`ramas` antes
  que el endpoint); 10 antes que 11–13 (tipos antes que UI); 11 antes que 12–13
  (constructor antes que los controles que lo usan). ✔
