# Catálogos de APIs: registro (A) y sección (D) — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que el registro de endpoints distinga catálogo de consulta, resuelva lo que un Diccionario escribe de verdad, produzca `API-05` (nunca silencio) para lo de pago o llave, y que el asistente tenga una sección «Catálogos» de solo lectura que lo enseñe.

**Architecture:** todo el conocimiento de endpoints sigue en `nucleo/integraciones.py` (datos puros, sin red). Un endpoint nuevo `GET /api/v1/catalogos` lo expone. La SPA gana una vista `features/catalogos/` y un ítem de menú fuera de los cuatro pasos, alcanzable sin expediente; `App.tsx` la enruta por `pathname === "/catalogos"` (el servidor ya sirve `index.html` para rutas desconocidas).

**Tech Stack:** Python 3.9+ (`Optional[X]`, no `X | None`), pydantic 2, FastAPI, pytest; Vite + React + TS + shadcn/ui, vitest + testing-library.

**Spec:** `docs/superpowers/specs/2026-09-22-catalogos-y-consulta-design.md` (piezas A y D).

## Global Constraints

- Identificadores en español sin acentos; comentarios explican el *por qué*; compatible con Python 3.9.
- **Una URL observada en un export auténtico gana** sobre la de cualquier documento. El registro emitible se queda en cuatro: `mgee`, `mgem`, `zip_codes`, `consultacurpn`.
- **Solo se emiten endpoints públicos y gratuitos.** Los de pago, llave o convenio van a `APIS_CON_TOKEN`, no aparecen en la sección, y un Diccionario que los nombre produce `API-05`.
- El núcleo **no toca la red**. Nada de lo de aquí llama a una API.
- Nada se comitea sin `.venv/bin/pytest` en verde; el frontend pasa `bash scripts/check-frontend.sh`.
- Mensajes de commit en español, sin acentos en el asunto, con el porqué en el cuerpo.

---

### Task 1: `tipo` en el registro — catálogo o consulta

**Files:**
- Modify: `src/gpmc/nucleo/integraciones.py:17-33` (dataclass) y `:41-75` (entradas)
- Test: `tests/test_integraciones.py`

**Interfaces:**
- Produces: `Catalogo.tipo: str` con valores `"catalogo"` | `"consulta"`. `CATALOGOS["consultacurpn"].tipo == "consulta"`; las otras tres `"catalogo"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_integraciones.py — al final del archivo

def test_cada_entrada_dice_si_es_catalogo_o_consulta():
    """El catalogo de la Direccion mezcla dos cosas que el registro no
    distinguia: una LISTA para poblar un select (estados, colonias) y una
    CONSULTA que recibe un dato y devuelve otros para autollenar (CURP ->
    nombre). La segunda es un `api_ajax` y necesita `campos_respuesta`; la
    primera no. Sin el tipo, el compilador no sabe cual emitir."""
    from gpmc.nucleo.integraciones import CATALOGOS
    tipos = {clave: c.tipo for clave, c in CATALOGOS.items()}
    assert tipos == {
        "mgee": "catalogo", "mgem": "catalogo", "zip_codes": "catalogo",
        "consultacurpn": "consulta",
    }


def test_una_consulta_declara_que_devuelve_y_un_catalogo_no():
    from gpmc.nucleo.integraciones import CATALOGOS
    assert CATALOGOS["consultacurpn"].campos_respuesta == ("nombres", "apePat", "apeMat")
    assert CATALOGOS["mgee"].campos_respuesta == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_integraciones.py -q -k "catalogo_o_consulta or declara_que_devuelve"`
Expected: FAIL con `AttributeError: 'Catalogo' object has no attribute 'tipo'`

- [ ] **Step 3: Write minimal implementation**

En la dataclass, después de `requiere_padre: bool = False`:

```python
    # Dos cosas distintas que el catalogo de la Direccion (2026-08-11) mezcla:
    # "catalogo" devuelve una LISTA para poblar un select; "consulta" recibe
    # un dato y devuelve otros para autollenar (un `api_ajax`). Solo la
    # segunda usa `campos_respuesta`.
    tipo: str = "catalogo"
```

En la entrada de SIPUBEH, añadir `tipo="consulta",` junto a `campos_respuesta=(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_integraciones.py -q`
Expected: PASS (todas)

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/integraciones.py tests/test_integraciones.py
git commit -m "feat(integraciones): cada entrada dice si es catalogo o consulta

El catalogo de la Direccion mezcla listas para un select y consultas que
autollenan (api_ajax). Sin el tipo, el compilador no sabe cual emitir. SIPUBEH
pasa a consulta; las otras tres siguen como catalogo."
```

---

### Task 2: sinónimos con lo que un Diccionario escribe de verdad

**Files:**
- Modify: `src/gpmc/nucleo/integraciones.py:83-104` (`SINONIMOS`, `resolver`)
- Modify: `src/gpmc/extractores/diccionario.py` (`_clave_endpoint`, ~línea 410)
- Test: `tests/test_integraciones.py`, `tests/test_extractor_diccionario.py`

**Interfaces:**
- Produces: `integraciones.clave_de(texto: Optional[str]) -> Optional[str]` — devuelve la clave técnica (`"mgem"`) a partir de una clave o de una frase del Diccionario (`"Código Postal"`, `"CURP"`), o `None`. `resolver()` la usa por dentro. `_clave_endpoint` devuelve `clave_de(celda)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_integraciones.py — al final

import pytest


@pytest.mark.parametrize("texto,clave", [
    ("CURP", "consultacurpn"),
    ("curp", "consultacurpn"),
    ("Código Postal", "zip_codes"),
    ("codigo postal", "zip_codes"),
    ("CP", "zip_codes"),
    ("colonia", "zip_codes"),
    ("Municipio", "mgem"),
    ("estado", "mgee"),
    ("INEGI", "mgee"),
    ("`mgem` (INEGI)", "mgem"),
    ("mgee", "mgee"),
])
def test_clave_de_resuelve_lo_que_escribe_un_diccionario(texto, clave):
    # Los Diccionarios escriben el proveedor o el concepto —«CURP», «Código
    # Postal»—, no la clave tecnica. Y lo escriben con acentos y mayusculas.
    from gpmc.nucleo.integraciones import clave_de
    assert clave_de(texto) == clave


def test_clave_de_no_inventa():
    from gpmc.nucleo.integraciones import clave_de
    assert clave_de("consultarfc") is None
    assert clave_de("") is None
    assert clave_de(None) is None
```

```python
# tests/test_extractor_diccionario.py — al final

def test_un_endpoint_escrito_como_concepto_se_resuelve():
    """El Diccionario hibrido escribe `\\`mgem\\` (INEGI)`; el estandar, cuando
    trae columna Endpoint, escribe «Código Postal» o «CURP». El extractor solo
    entendia la primera forma."""
    from gpmc.extractores.diccionario import _clave_endpoint
    assert _clave_endpoint("`mgem` (INEGI)") == "mgem"
    assert _clave_endpoint("Código Postal") == "zip_codes"
    assert _clave_endpoint("CURP") == "consultacurpn"
    assert _clave_endpoint("N/A") is None


def test_un_endpoint_desconocido_sigue_llegando_como_texto():
    # El contrapeso: si lo desconocido volviera como None, `expediente.py`
    # lo saltaria (`if not c.endpoint: continue`) y el hueco API-01 «no esta
    # en el registro» desapareceria. Tiene que llegar como el token crudo.
    from gpmc.extractores.diccionario import _clave_endpoint
    assert _clave_endpoint("`consultarfc` (SAT)") == "consultarfc"
    assert _clave_endpoint("REPUVE") == "REPUVE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_integraciones.py tests/test_extractor_diccionario.py -q -k "clave_de or escrito_como_concepto"`
Expected: FAIL con `ImportError: cannot import name 'clave_de'`

- [ ] **Step 3: Write minimal implementation**

En `integraciones.py`, reemplazar `SINONIMOS` y `resolver` por:

```python
# Sinonimos: lo que un Diccionario escribe de verdad, no la clave tecnica.
# Se resuelven sin acentos ni mayusculas. Un proveedor con dos endpoints
# (INEGI) cae al que no requiere padre; "municipio" y "mgem" van al que si.
SINONIMOS = {
    "inegi": "mgee", "estado": "mgee", "entidad": "mgee",
    "municipio": "mgem",
    "sepomex": "zip_codes", "codigo postal": "zip_codes", "cp": "zip_codes",
    "colonia": "zip_codes",
    "sipubeh": "consultacurpn", "curp": "consultacurpn",
}


def _normalizar(texto: str) -> str:
    import unicodedata
    sin_acentos = "".join(
        ch for ch in unicodedata.normalize("NFD", texto) if unicodedata.category(ch) != "Mn"
    )
    return " ".join(sin_acentos.lower().split())


def clave_de(texto: Optional[str]) -> Optional[str]:
    """Clave tecnica a partir de una clave o de una frase del Diccionario.

    Acepta «mgem», «`mgem` (INEGI)», «Código Postal» o «CURP». Devuelve None
    para lo que no conoce: el compilador lo reporta como API-01 en vez de
    inventar una URL.
    """
    if not texto:
        return None
    limpio = _normalizar(texto.replace("`", ""))
    # Primero la clave tecnica sola o seguida de su proveedor entre parentesis.
    primera = limpio.split("(")[0].strip()
    if primera in CATALOGOS:
        return primera
    if primera in SINONIMOS:
        return SINONIMOS[primera]
    return None


def resolver(clave: Optional[str]) -> Optional[Catalogo]:
    """Un endpoint no registrado devuelve None: el compilador lo reporta como
    hueco API-01 en vez de inventar una URL."""
    resuelta = clave_de(clave)
    return CATALOGOS.get(resuelta) if resuelta else None
```

En `diccionario.py`, `_clave_endpoint` pasa a:

```python
def _clave_endpoint(celda: str) -> Optional[str]:
    """'`mgem` (INEGI)' -> 'mgem'; «Código Postal» -> 'zip_codes'.

    Primero el token tecnico, como siempre. Si no resuelve, se prueba la celda
    entera como frase del Diccionario. Y si tampoco, se devuelve el TOKEN
    crudo, no None: `expediente.py` salta los campos sin endpoint, y un
    endpoint desconocido tiene que llegar hasta alli para producir API-01.
    N/A y vacio si devuelven None.
    """
    limpio = _limpiar_celda(celda)
    if not limpio or limpio.upper() == "N/A":
        return None
    m = _ENDPOINT.match(limpio)
    token = m.group(1) if m else None
    if token and _resolver(token) is not None:
        return token
    return _clave_de(limpio) or token
```

y arriba, junto a los imports:
`from gpmc.nucleo.integraciones import clave_de as _clave_de, resolver as _resolver`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS. Las pruebas existentes con `consultarfc` (`test_extractor_expediente.py:198`, `test_simulador.py`, `test_integraciones.py:39`) siguen en verde: un token desconocido sigue llegando crudo y `resolver()` sigue dando `None`.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/integraciones.py src/gpmc/extractores/diccionario.py tests/test_integraciones.py tests/test_extractor_diccionario.py
git commit -m "feat(integraciones): los sinonimos resuelven lo que un Diccionario escribe

«CURP», «Código Postal», «colonia», «municipio»: el proveedor o el concepto,
con acentos y mayusculas. Antes solo se entendia la clave tecnica entre
comillas invertidas. Un texto desconocido sigue dando None y API-01."
```

---

### Task 3: lo de pago o llave produce `API-05` con nombre, nunca silencio

**Files:**
- Modify: `src/gpmc/nucleo/integraciones.py:95-108` (`APIS_CON_TOKEN`, `requiere_token`)
- Modify: `src/gpmc/extractores/expediente.py:405-411` (mensaje de `API-05`)
- Test: `tests/test_integraciones.py`, `tests/test_extractor_expediente.py`

**Interfaces:**
- Produces: `integraciones.PROPUESTAS: dict[str, str]` — clave → nombre legible del servicio de pago o convenio. `requiere_token(texto)` acepta frases (`"REPUVE"`) además de claves. `nombre_propuesta(texto) -> Optional[str]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_integraciones.py — al final

@pytest.mark.parametrize("texto", ["REPUVE", "repuve", "Tláloc", "tlaloc", "RFC", "INE", "codigos.zip", "SAT"])
def test_lo_de_pago_o_llave_se_reconoce_y_no_se_emite(texto):
    # Del catalogo de la Direccion: Tlaloc (CURP con defuncion, RFC),
    # ApiMarket (REPUVE), INE y codigos.zip piden llave, pago o convenio. NO
    # se emiten (SEG-04) y NO aparecen en la seccion; pero un Diccionario que
    # los nombre tiene que producir API-05, no silencio.
    from gpmc.nucleo.integraciones import requiere_token, resolver, nombre_propuesta
    assert requiere_token(texto) is True
    assert resolver(texto) is None
    assert nombre_propuesta(texto)


def test_ninguna_propuesta_esta_en_el_registro_emitible():
    from gpmc.nucleo.integraciones import CATALOGOS, PROPUESTAS
    assert not set(CATALOGOS) & set(PROPUESTAS)
```

```python
# tests/test_extractor_expediente.py — al final

def test_un_diccionario_que_nombra_repuve_produce_api05_con_nombre(tmp_path):
    """Un endpoint de pago o convenio se reporta con lo que ES, para que el
    analista sepa que existe y por que no sale solo."""
    from gpmc.extractores.expediente import extraer_expediente
    (tmp_path / "Diccionario de Datos.md").write_text(
        "### Pantalla 1 — CIUDADANO — Datos\n\n"
        "| Nombre del Campo | Tipo de Dato | Componente | Obligatorio | Endpoint / API | Descripción |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Placa | String | Campo de texto | Sí | REPUVE | [Captura] Campo `@@placa`. |\n",
        encoding="utf-8",
    )
    r = extraer_expediente(tmp_path)
    (h,) = [x for x in r.huecos if x.codigo == "API-05"]
    assert "REPUVE" in h.mensaje
    assert "Acción PHP" in h.mensaje
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_integraciones.py tests/test_extractor_expediente.py -q -k "pago_o_llave or propuesta or repuve"`
Expected: FAIL con `ImportError: cannot import name 'nombre_propuesta'`

- [ ] **Step 3: Write minimal implementation**

En `integraciones.py`, reemplazar `APIS_CON_TOKEN` y `requiere_token` por:

```python
# Propuestas: servicios del «Catalogo Maestro de APIs» de la Direccion
# (2026-08-11) que piden llave, pago o convenio. NO se emiten en cliente
# (SEG-04: la llave quedaria a la vista) y NO aparecen en la seccion de
# catalogos. Se registran para que un Diccionario que los nombre produzca
# API-05 con su nombre, en vez de silencio. Quedan como propuesta pendiente
# de convenio; el dia que uno tenga via publica, pasa a CATALOGOS con prueba.
PROPUESTAS = {
    "sat": "SAT (validacion de RFC y CFDI)",
    "rfc": "SAT (validacion de RFC)",
    "tlaloc": "Tlaloc (CURP con estatus de defuncion, RFC) — de pago",
    "tlaloc_curp": "Tlaloc (CURP con estatus de defuncion) — de pago",
    "renapo_directo": "RENAPO directo — requiere convenio",
    "repuve": "REPUVE via ApiMarket — de pago",
    "ine": "INE (verificacion de credencial) — requiere convenio",
    "codigos.zip": "codigos.zip (codigos postales) — requiere API Key",
}
APIS_CON_TOKEN = frozenset(PROPUESTAS)


def nombre_propuesta(texto: Optional[str]) -> Optional[str]:
    """El nombre legible de un servicio de pago o convenio, o None."""
    if not texto:
        return None
    return PROPUESTAS.get(_normalizar(texto.replace("`", "")).split("(")[0].strip())


def requiere_token(clave: Optional[str]) -> bool:
    """El endpoint es uno conocido que necesita credencial. El compilador no lo
    emite en cliente (SEG-04); se reporta como hueco API-05 → Acción PHP a mano."""
    return nombre_propuesta(clave) is not None
```

En `expediente.py`, el mensaje de `API-05`:

```python
            if _requiere_token(c.endpoint):
                r.huecos.append(Hueco(
                    "falta_dato", "API-05", c.nombre,
                    f"'{c.endpoint}' es {_nombre_propuesta(c.endpoint)}: exige credencial y el "
                    f"compilador no lo emite en el navegador (riesgo SEG-04). Configúralo como "
                    f"una Acción PHP a mano, o usa la vía pública si existe (para CURP: SIPUBEH).",
                ))
                continue
```

y en los imports de `expediente.py`: `from gpmc.nucleo.integraciones import nombre_propuesta as _nombre_propuesta`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS. Ojo: `test_los_catalogos_verificados_estan_registrados` debe seguir dando exactamente las cuatro claves.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/nucleo/integraciones.py src/gpmc/extractores/expediente.py tests/test_integraciones.py tests/test_extractor_expediente.py
git commit -m "feat(integraciones): lo de pago o llave produce API-05 con nombre, no silencio

Tlaloc, ApiMarket (REPUVE), INE, codigos.zip y SAT quedan registrados como
propuesta pendiente de convenio. No se emiten y no salen en la seccion; pero
un Diccionario que escriba REPUVE recibe un hueco que dice que es y por que no
sale solo. Antes, silencio: es la familia de defecto de P-18."
```

---

### Task 4: `GET /api/v1/catalogos`

**Files:**
- Modify: `src/gpmc/web/api.py` (modelo cerca de `ClasificarOut` ~línea 170; ruta dentro de `crear_router`, junto a `@r.post("/clasificar")` ~línea 254)
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `GET /api/v1/catalogos` → `{"catalogos": [CatalogoOut...], "nota": str}` con `CatalogoOut = {clave, proveedor, tipo, url, sinonimos: [str], campos_respuesta: [str]}`. Solo las entradas de `CATALOGOS`; nunca las de `PROPUESTAS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py — al final

def test_get_catalogos_lista_lo_emitible_y_calla_lo_de_pago(tmp_path):
    """La seccion «Catalogos» del asistente pinta esto tal cual. Solo lo que
    el compilador puede emitir; lo de pago o convenio no se lista (se
    configura en la plataforma) y se dice en la nota."""
    r = _cli(tmp_path).get("/api/v1/catalogos")
    assert r.status_code == 200
    d = r.json()
    claves = {c["clave"] for c in d["catalogos"]}
    assert claves == {"mgee", "mgem", "zip_codes", "consultacurpn"}
    assert "repuve" not in claves and "tlaloc" not in claves
    curp = next(c for c in d["catalogos"] if c["clave"] == "consultacurpn")
    assert curp["tipo"] == "consulta"
    assert curp["campos_respuesta"] == ["nombres", "apePat", "apeMat"]
    assert "curp" in curp["sinonimos"]
    assert "credencial" in d["nota"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k "get_catalogos"`
Expected: FAIL con `assert 404 == 200`

- [ ] **Step 3: Write minimal implementation**

Junto a los otros modelos de `api.py`:

```python
class CatalogoOut(BaseModel):
    clave: str
    proveedor: str
    tipo: str                     # catalogo | consulta
    url: str
    sinonimos: List[str] = []     # lo que un Diccionario escribe para activarlo
    campos_respuesta: List[str] = []


class CatalogosOut(BaseModel):
    catalogos: List[CatalogoOut]
    nota: str
```

Dentro de `crear_router`, junto a `/clasificar`:

```python
    @r.get("/catalogos", response_model=CatalogosOut)
    async def listar_catalogos():
        """Lo que el compilador sabe emitir, para la seccion «Catalogos».

        Solo `CATALOGOS`: lo de pago o convenio (`PROPUESTAS`) no se lista
        porque no se emite y se configura en la plataforma. Nada se llama en
        vivo desde aqui: comprobar que un endpoint responde es del simulador.
        """
        from gpmc.nucleo.integraciones import CATALOGOS, SINONIMOS
        salida = []
        for clave, c in CATALOGOS.items():
            sinonimos = sorted(s for s, k in SINONIMOS.items() if k == clave)
            salida.append(CatalogoOut(
                clave=clave, proveedor=c.proveedor, tipo=c.tipo, url=c.url,
                sinonimos=sinonimos, campos_respuesta=list(c.campos_respuesta)))
        return CatalogosOut(
            catalogos=salida,
            nota=("Solo se listan los endpoints que el compilador emite. Los que exigen "
                  "credencial, pago o convenio no salen aquí: se configuran en la "
                  "plataforma como Acción PHP."))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/web/api.py tests/test_api.py
git commit -m "feat(api): GET /api/v1/catalogos, lo que el compilador sabe emitir

Para la seccion «Catalogos» del asistente. Solo CATALOGOS; las propuestas de
pago o convenio no se listan y la nota dice por que. No llama a nada en vivo."
```

---

### Task 5: la vista «Catálogos»

**Files:**
- Modify: `frontend/src/lib/api.ts` (junto a `leerExpediente`, ~línea 184)
- Create: `frontend/src/features/catalogos/Catalogos.tsx`
- Test: `frontend/src/features/catalogos/Catalogos.test.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/catalogos` de la Task 4.
- Produces: `leerCatalogos(): Promise<CatalogosOut>` en `lib/api.ts`; componente `Catalogos` sin props.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/catalogos/Catalogos.test.tsx
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  leerCatalogos: vi.fn().mockResolvedValue({
    catalogos: [
      { clave: "mgee", proveedor: "INEGI", tipo: "catalogo",
        url: "https://gaia.inegi.org.mx/wscatgeo/v2/mgee",
        sinonimos: ["estado", "inegi"], campos_respuesta: [] },
      { clave: "consultacurpn", proveedor: "SIPUBEH", tipo: "consulta",
        url: "https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn?curp=@@{padre}",
        sinonimos: ["curp", "sipubeh"], campos_respuesta: ["nombres", "apePat", "apeMat"] },
    ],
    nota: "Solo se listan los endpoints que el compilador emite. Los que exigen credencial no salen aquí.",
  }),
}));

import Catalogos from "./Catalogos";

it("pinta una fila por catalogo con proveedor, que hace y que lo activa", async () => {
  render(<Catalogos />);
  const fila = (await screen.findByRole("row", { name: /INEGI/ }));
  expect(fila).toHaveTextContent(/lista/i);          // "catalogo" se lee como lista
  expect(fila).toHaveTextContent(/estado/);
  const curp = screen.getByRole("row", { name: /SIPUBEH/ });
  expect(curp).toHaveTextContent(/consulta/i);
  expect(curp).toHaveTextContent(/nombres, apePat, apeMat/);
});

it("dice cuantos conoce y que lo de credencial no se lista", async () => {
  render(<Catalogos />);
  expect(await screen.findByText(/2 endpoints/)).toBeInTheDocument();
  expect(screen.getByText(/exigen credencial/i)).toBeInTheDocument();
});

it("mientras carga no pinta la tabla vacia como si no hubiera nada", () => {
  render(<Catalogos />);
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.getByText(/cargando/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/catalogos/Catalogos.test.tsx`
Expected: FAIL — `Cannot find module './Catalogos'`

- [ ] **Step 3: Write minimal implementation**

En `lib/api.ts`, junto a `leerExpediente`:

```ts
export interface CatalogoOut {
  clave: string;
  proveedor: string;
  tipo: "catalogo" | "consulta";
  url: string;
  sinonimos: string[];
  campos_respuesta: string[];
}
export interface CatalogosOut {
  catalogos: CatalogoOut[];
  nota: string;
}

/** `GET /api/v1/catalogos` — lo que el compilador sabe emitir. Solo lectura. */
export async function leerCatalogos(): Promise<CatalogosOut> {
  return pedirJson(`${BASE}/catalogos`);
}
```

`frontend/src/features/catalogos/Catalogos.tsx`:

```tsx
import { useEffect, useState } from "react";

import { leerCatalogos, type CatalogosOut } from "@/lib/api";

/**
 * Seccion «Catalogos»: que endpoints conoce el compilador y con que palabras
 * del Diccionario se activan. Solo lectura y sin llamar a nada en vivo:
 * comprobar que un endpoint responde es trabajo del simulador.
 *
 * Lo de pago o convenio no aparece a proposito (decision del 2026-09-22): se
 * configura en la plataforma, y listarlo aqui invitaria a esperar que salga
 * solo.
 */
export default function Catalogos() {
  const [datos, setDatos] = useState<CatalogosOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    leerCatalogos().then(setDatos).catch(() => setError("No se pudo leer el registro."));
  }, []);

  if (error) return <p role="alert" className="text-sm text-destructive">{error}</p>;
  if (!datos) return <p className="text-sm text-muted-foreground">Cargando…</p>;

  return (
    <section className="flex flex-col gap-4 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Catálogos</h1>
        <p className="text-sm text-muted-foreground">
          El compilador conoce <strong>{datos.catalogos.length} endpoints</strong>. {datos.nota}
        </p>
      </header>
      <table className="w-full text-sm">
        <thead className="text-left font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
          <tr>
            <th className="py-2 pr-4">Proveedor</th>
            <th className="py-2 pr-4">Qué hace</th>
            <th className="py-2 pr-4">Se activa con</th>
            <th className="py-2 pr-4">Devuelve</th>
            <th className="py-2">URL</th>
          </tr>
        </thead>
        <tbody>
          {datos.catalogos.map((c) => (
            <tr key={c.clave} aria-label={c.proveedor} className="border-t border-border align-top">
              <td className="py-2 pr-4 font-medium">{c.proveedor}</td>
              <td className="py-2 pr-4">
                {c.tipo === "consulta" ? "Consulta: autollena campos" : "Lista para un desplegable"}
              </td>
              <td className="py-2 pr-4">{c.sinonimos.join(", ")}</td>
              <td className="py-2 pr-4">{c.campos_respuesta.join(", ") || "—"}</td>
              <td className="py-2 break-all font-mono text-xs text-muted-foreground">{c.url}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/catalogos/Catalogos.test.tsx`
Expected: PASS (3)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/features/catalogos/
git commit -m "feat(ux): la vista «Catalogos», de solo lectura

Una tabla con proveedor, que hace (lista o consulta), con que palabras del
Diccionario se activa, que devuelve y la URL. Sin llamar a nada en vivo. Lo de
pago o convenio no aparece a proposito."
```

---

### Task 6: el ítem de menú y la ruta `/catalogos`

**Files:**
- Modify: `frontend/src/components/NavegacionLateral.tsx` (bloque inferior, junto a «Historial», ~línea 110)
- Modify: `frontend/src/App.tsx:32-75`
- Test: `frontend/src/components/NavegacionLateral.test.tsx`, `frontend/src/App.test.tsx` (ya existe: se amplía su `vi.mock` y se añade una prueba)

**Interfaces:**
- Consumes: `Catalogos` de la Task 5.
- Produces: la ruta `/catalogos` renderiza `<Catalogos />` con el título «Catálogos» en `AppHeader`; el menú tiene un enlace «Catálogos» siempre disponible, fuera de los pasos.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/components/NavegacionLateral.test.tsx — dentro del describe existente

  test("Catalogos esta siempre disponible y no es un paso del proceso", () => {
    // Es referencia, no un paso: no puede marcar `aria-current="step"` ni
    // depender de que haya expediente. Va junto a Historial.
    render(<NavegacionLateral sid={null} />);
    const enlace = screen.getByRole("link", { name: /catálogos/i });
    expect(enlace).toHaveAttribute("href", "/catalogos");
    expect(within(pasos()).queryByRole("link", { name: /catálogos/i })).toBeNull();
  });
```

```tsx
// frontend/src/App.test.tsx — (1) en el vi.mock existente, añadir una linea:
  leerCatalogos: vi.fn().mockResolvedValue({
    catalogos: [],
    nota: "Solo se listan los endpoints que el compilador emite.",
  }),

// (2) dentro del describe("App (SPA SP1)"), añadir:
  it("en /catalogos pinta la seccion de catalogos y no la carga de insumos", async () => {
    // Otras pruebas de este archivo asumen pathname "/": la ruta se fija
    // aqui y se restaura al final, no en un beforeEach global.
    window.history.replaceState({}, "", "/catalogos");
    try {
      render(<App />);
      // `AppHeader` pinta el titulo en un <span>, asi que el unico heading
      // llamado «Catálogos» es el <h1> de la vista.
      expect(await screen.findByRole("heading", { name: /catálogos/i })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /extraer/i })).toBeNull();
    } finally {
      window.history.replaceState({}, "", "/");
    }
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/NavegacionLateral.test.tsx src/App.test.tsx`
Expected: FAIL — el enlace «Catálogos» no existe; en `/catalogos` se pinta «Carga de insumos».

- [ ] **Step 3: Write minimal implementation**

En `NavegacionLateral.tsx`: importar `BookOpen` de `lucide-react` y, en el bloque inferior, **antes** del enlace a Historial:

```tsx
        <a href="/catalogos" className={cn(base, "text-white/70 hover:bg-white/10 hover:text-white")}>
          <BookOpen aria-hidden className="size-5 shrink-0" />
          <span className="max-lg:sr-only">Catálogos</span>
        </a>
```

En `App.tsx`: importar `Catalogos from "@/features/catalogos/Catalogos"`, y

```tsx
  // Referencia, no un paso: se sirve sin expediente. El servidor entrega
  // index.html para cualquier ruta que no sea de un handler real.
  const enCatalogos = window.location.pathname === "/catalogos";
```

antes del `return`, y en el `return`:

```tsx
        <AppHeader titulo={enCatalogos ? "Catálogos" : est ? "Revisión del expediente" : "Carga de insumos"} />
        <main className="flex-1 px-6 py-8">
          {aviso ? (
            <p role="alert" className="pb-4 text-sm text-destructive">
              {aviso}
            </p>
          ) : null}
          {enCatalogos ? (
            <Catalogos />
          ) : est ? (
            <WizardHuecos estado={est} onEstado={setEst} />
          ) : (
            <CargaInsumos onListo={setEst} />
          )}
        </main>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && bash ../scripts/check-frontend.sh`
Expected: tipos limpios, vitest en verde, build OK.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/NavegacionLateral.tsx frontend/src/components/NavegacionLateral.test.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(ux): «Catalogos» en el menu lateral, alcanzable sin expediente

Es referencia, no un paso del proceso: va junto a Historial y no marca
aria-current. La SPA enruta /catalogos; el servidor ya sirve index.html para
rutas que no son de un handler."
```

---

### Task 7: verificación de punta a punta y despliegue en desarrollo

**Files:** ninguno nuevo.

- [ ] **Step 1: Suites completas**

Run: `.venv/bin/python -m pytest -q && bash scripts/check-frontend.sh`
Expected: todo en verde; anotar los totales (partían de 583 servidor / 243 interfaz).

- [ ] **Step 2: El endpoint, contra el servidor de verdad**

Run:
```bash
kill "$(cat /tmp/dev_pid.txt)" 2>/dev/null; lsof -ti:8123 | xargs -r kill -9; sleep 1
nohup .venv/bin/gpmc servir --host 0.0.0.0 --puerto 8123 \
  --almacen "$HOME/Library/Application Support/gpmc/sesiones-dev" \
  --log "$HOME/Library/Logs/gpmc/desarrollo.log" >/dev/null 2>&1 & disown; echo $! > /tmp/dev_pid.txt
curl -fsS --retry 30 --retry-delay 1 --retry-connrefused -o /dev/null http://127.0.0.1:8123/
curl -s http://127.0.0.1:8123/api/v1/catalogos | .venv/bin/python -m json.tool | head -30
```
Expected: cuatro entradas, `consultacurpn` con `tipo: consulta` y sus tres campos.

- [ ] **Step 3: La pantalla, en el navegador**

Abrir `http://127.0.0.1:8123/catalogos`. Comprobar: el menú muestra «Catálogos» junto a Historial; la tabla tiene cuatro filas; SIPUBEH dice «Consulta: autollena campos» y «nombres, apePat, apeMat».

- [ ] **Step 4: Un Diccionario con REPUVE, de punta a punta**

Run:
```bash
D=$(mktemp -d); printf '### Pantalla 1 — CIUDADANO — Datos\n\n| Nombre del Campo | Tipo de Dato | Componente | Obligatorio | Endpoint / API | Descripción |\n| --- | --- | --- | --- | --- | --- |\n| Placa | String | Campo de texto | Sí | REPUVE | [Captura] Campo `@@placa`. |\n' > "$D/Diccionario de Datos.md"
.venv/bin/gpmc extraer "$D" -o "$D/m.yaml" 2>&1 | grep -A1 "API-05"
```
Expected: un `API-05` que nombra «REPUVE via ApiMarket — de pago» y la Acción PHP.

- [ ] **Step 5: Bitácora y push**

Anotar en `planeacion/pendientes.md` que P-21 queda hecha en su mitad automática (A) y con la sección (D); B sigue pendiente. `git push origin main`.
