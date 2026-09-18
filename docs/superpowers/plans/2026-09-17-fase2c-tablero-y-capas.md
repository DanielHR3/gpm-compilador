# Fase 2c-1 — Tablero de inconsistencias y capas baratas · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La pantalla de revisión pasa de lista recorrible a tablero por código, y resuelve o explica sin gastar llamadas al modelo siempre que se pueda.

**Architecture:** Tres capas delante del proveedor —explicaciones escritas a mano (cero tokens), dos decisiones deterministas, prefiltro léxico y caché por huella— más un tablero de columnas por código que sustituye los modos `lista` y `foco`. El backend gana funciones puras (`anclaje.py`, `cache.py`) que se prueban sin red; el frontend gana componentes chicos con una responsabilidad cada uno. Ningún endpoint se agrega ni se quita.

**Tech Stack:** Python 3.9+, Pydantic v2, FastAPI, pytest · Vite + React 19 + TypeScript + Tailwind v4 + shadcn (base-ui), vitest, oxlint

**Spec:** `docs/superpowers/specs/2026-09-17-fase2c-tablero-y-capas-diseno.md`

## Global Constraints

- **`nucleo/` nunca importa `agentes/`.** Lo verifica `tests/test_agentes.py::test_el_nucleo_no_importa_agentes`. Todo lo que decida si se llama al modelo vive en `agentes/`.
- **El modelo nunca escribe.** Propone; un filtro determinista tamiza; una persona confirma; `POST /resolver` escribe.
- **No se agrega ni se quita ningún endpoint.** El único cambio de contrato es aditivo: el filtro de `GET /expedientes/{sid}/propuestas` deja pasar `aceptable` **y** `sin_anclaje`.
- **Vocabulario de producto:** en la interfaz se dice **inconsistencia**, nunca "hueco". Los títulos de columna son los de `TITULOS` en `lenguaje.ts`.
- **Toda interacción con el modelo se registra** en `bitacora-ia.jsonl` (Licencia AI), incluidos los aciertos de caché.
- **Comentarios y mensajes de commit en castellano, sin acentos en el código fuente Python** (convención del repo).
- Correr siempre con `set -o pipefail` cuando se encadene la salida de pytest o vitest.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `src/gpmc/agentes/anclaje.py` | **NUEVO.** Funciones puras: tokenizar, vocabulario de candidatos, decidir si una frase ancla en algún campo. Sin red, sin estado. |
| `src/gpmc/agentes/cache.py` | **NUEVO.** Huella y lectura/escritura de propuestas cacheadas en el almacén global. Sin red. |
| `src/gpmc/agentes/contexto.py` | **MODIF.** `HuecoDic08` gana `anclado`; prefiltro léxico con red de seguridad. |
| `src/gpmc/agentes/dic08.py` | **MODIF.** Salta los no anclados, consulta la caché, sólo llama por lo que queda. |
| `src/gpmc/web/api.py` | **MODIF.** El filtro de propuestas visibles deja pasar `sin_anclaje`. |
| `frontend/src/features/huecos/lenguaje.ts` | **MODIF.** `EXPLICACIONES` por código y `explicacionDeCodigo()`. |
| `frontend/src/features/huecos/agrupar.ts` | **MODIF.** `agruparPorCodigo()`. |
| `frontend/src/features/huecos/TarjetaChica.tsx` | **NUEVO.** Una inconsistencia como tarjeta de selección. |
| `frontend/src/features/huecos/ColumnaCodigo.tsx` | **NUEVO.** Encabezado con cuenta + lista de tarjetas chicas. |
| `frontend/src/features/huecos/Explicacion.tsx` | **NUEVO.** La capa 0 en pantalla, más el sitio reservado del asistente. |
| `frontend/src/features/huecos/TarjetaAbierta.tsx` | **NUEVO.** Dos mitades: control de resolución \| explicación. |
| `frontend/src/features/huecos/Tablero.tsx` | **NUEVO.** Ensambla columnas y gobierna cuál está abierta. |
| `frontend/src/features/huecos/WizardHuecos.tsx` | **MODIF.** Monta el tablero; se van `modo`, `HUECOS_PARA_FOCO` y el conmutador. |
| `frontend/src/features/huecos/ModoFoco.tsx` | **SE BORRA.** Junto a `ModoFoco.test.tsx` si existe. |

---

## Task 1: `anclaje.py` — decidir sin modelo si una frase ancla en algún campo

**Files:**
- Create: `src/gpmc/agentes/anclaje.py`
- Test: `tests/test_anclaje.py`

**Interfaces:**
- Consumes: `gpmc.agentes.contexto.CampoCandidato` (atributos `nombre`, `etiqueta`, `valores`).
- Produces: `tokens(texto: str) -> set[str]`, `palabras(texto: str) -> set[str]`, `vocabulario(campos: list) -> set[str]`, `sin_anclaje(prosa: str, campos: list) -> bool`, y la constante `MOTIVO_SIN_ANCLAJE: str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_anclaje.py
from gpmc.agentes.anclaje import MOTIVO_SIN_ANCLAJE, palabras, sin_anclaje, tokens, vocabulario
from gpmc.agentes.contexto import CampoCandidato


def _campo(nombre, etiqueta="", valores=()):
    return CampoCandidato(nombre=nombre, etiqueta=etiqueta or nombre, tipo="text",
                          valores=list(valores), pantalla="p1")


def test_tokens_quita_acentos_y_palabras_cortas():
    assert tokens("Solo si la validación de formato") == {"solo", "validacion", "formato"}


def test_palabras_descarta_las_vacias():
    # "solo" es vacia; "validacion" no.
    assert palabras("Solo si la validación") == {"validacion"}


def test_vocabulario_junta_nombre_etiqueta_y_valores():
    v = vocabulario([_campo("forma_pago", "Forma de pago", ["linea", "ventanilla"])])
    assert {"forma", "pago", "linea", "ventanilla"} <= v


def test_la_frase_medida_no_ancla_en_ningun_campo():
    # Caso real: 2 de los 3 DIC-08 sin anclaje del corpus, y el que trabo la revision.
    campos = [_campo("procedencia", "Procedencia", ["fisica", "moral"]),
              _campo("rfc", "RFC")]
    assert sin_anclaje("Solo si la validación de formato detecta errores al enviar", campos)


def test_un_campo_de_una_pantalla_posterior_no_es_anclaje():
    """Caso real de Reposicion de Certificado: la prosa nombra un campo, pero
    de la Pantalla 2, y el hueco vive en la 1. Una condicion no puede mirar al
    futuro, asi que ese campo NO llega como candidato: lo que se recibe aqui es
    la lista sin el, y entonces no hay anclaje."""
    campos = [_campo("observaciones", "Observaciones")]
    assert sin_anclaje(
        'Visible solo cuando el ciudadano reingresa tras un resultado '
        '"¿Documentación conforme?" = No en la Pantalla 2', campos)


def test_una_frase_que_nombra_un_campo_si_ancla():
    campos = [_campo("procedencia", "Procedencia", ["fisica", "moral"])]
    assert not sin_anclaje("Visible solo si Procedencia es moral", campos)


def test_ancla_tambien_por_un_valor_del_catalogo():
    campos = [_campo("forma_pago", "Forma de pago", ["ventanilla", "linea"])]
    assert not sin_anclaje("Se muestra cuando el pago es en ventanilla", campos)


def test_las_palabras_vacias_no_cuentan_como_anclaje():
    # "campo" y "valor" aparecen en los dos lados y no significan nada.
    campos = [_campo("campo_valor", "Campo valor")]
    assert sin_anclaje("Solo si el campo tiene valor", campos)


def test_sin_campos_no_hay_anclaje_posible():
    assert sin_anclaje("Visible solo si Procedencia es moral", [])


def test_el_motivo_es_una_frase_para_una_persona():
    assert "campo" in MOTIVO_SIN_ANCLAJE.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_anclaje.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'gpmc.agentes.anclaje'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/gpmc/agentes/anclaje.py
"""Decide, SIN llamar al modelo, si una condicion en prosa puede llegar a ser
una regla entre campos.

Medido el 2026-09-17 sobre los seis expedientes reales: 2 de 23 condiciones
DIC-08 no mencionan ningun campo del tramite, y son la MISMA frase —«Solo si la
validacion de formato detecta errores al enviar»—. Preguntarle al modelo por
ellas cuesta una llamada para que declive (o peor, para que invente). Esto las
resuelve gratis y con mas acierto.
"""
import re
import unicodedata

# Palabras que aparecen en las dos orillas y no significan nada: si el unico
# "anclaje" es una de estas, no hay anclaje.
VACIAS = frozenset({
    "solo", "cuando", "campo", "campos", "valor", "valores", "pantalla",
    "usuario", "este", "esta", "esto", "para", "desde", "como", "siempre",
    "visible", "muestra", "mostrar", "debe", "sera", "tiene", "hace",
})

MOTIVO_SIN_ANCLAJE = (
    "la frase no menciona ningun campo del tramite: no es una comparacion "
    "entre campos, asi que el compilador no puede armar una regla"
)

_PALABRA = re.compile(r"[a-z]{4,}")


def tokens(texto: str) -> set:
    """Palabras de 4+ letras, en minusculas y sin acentos. Sin filtrar vacias:
    el vocabulario de los campos las necesita todas."""
    plano = "".join(c for c in unicodedata.normalize("NFD", texto or "")
                    if unicodedata.category(c) != "Mn")
    return set(_PALABRA.findall(plano.lower()))


def palabras(texto: str) -> set:
    """Como `tokens`, pero sin las vacias. Es lo que se usa del lado de la prosa."""
    return tokens(texto) - VACIAS


def vocabulario(campos) -> set:
    """Todo lo que nombra a los campos candidatos: nombre interno, etiqueta y
    valores del catalogo."""
    v = set()
    for c in campos:
        v |= tokens(c.nombre) | tokens(c.etiqueta) | tokens(" ".join(c.valores))
    return v


def sin_anclaje(prosa: str, campos) -> bool:
    """True si la prosa no comparte ninguna palabra con ningun candidato."""
    return not (palabras(prosa) & vocabulario(campos))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_anclaje.py -v`
Expected: PASS, 9 pruebas.

- [ ] **Step 5: Verificar contra el corpus real que el numero medido se sostiene**

Run:
```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python - <<'PY'
from pathlib import Path
from gpmc.extractores.expediente import extraer_expediente
from gpmc.agentes.contexto import contexto_dic08
from gpmc.agentes.anclaje import sin_anclaje
BASE = Path("/Users/danielhernandezrubio/Downloads/EXPEDIENTES DE TRAMITES CON REINGENIERIA")
n = s = 0
for d in sorted(p for p in BASE.iterdir() if p.is_dir()):
    if not any(d.glob("*iccionario*")): continue
    r = extraer_expediente(d)
    if not r.manifiesto: continue
    hs = [h for h in r.huecos if h.codigo == "DIC-08"]
    if not hs: continue
    ctx = contexto_dic08(r.manifiesto, hs)
    for h in ctx.huecos:
        n += 1
        propios = [c for c in ctx.campos if c.nombre in h.candidatos]
        if sin_anclaje(h.prosa, propios): s += 1
print(f"sin anclaje: {s}/{n}")
PY
```
Expected: `sin anclaje: 3/23`. Si sale otro número, **parar y avisar**: la medición del spec dejó de ser cierta y hay que entender por qué antes de seguir.

Los tres casos esperados son: la misma frase «Solo si la validación de formato detecta errores al enviar» en Alta de Avisos de Testamento y en Constancia de No Infracción, y en Reposición de Certificado la de `p1::observaciones`, que nombra un campo de la **Pantalla 2** desde la Pantalla 1 — una condición no puede mirar al futuro, así que ese campo no es candidato.

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/agentes/anclaje.py tests/test_anclaje.py
git commit -m "feat(agentes): decidir sin modelo si una condicion ancla en algun campo"
```

---

## Task 2: Prefiltro léxico de candidatos, con red de seguridad

**Files:**
- Modify: `src/gpmc/agentes/contexto.py`
- Test: `tests/test_contexto_prefiltro.py`

**Interfaces:**
- Consumes: `gpmc.agentes.anclaje.palabras`, `tokens`, `sin_anclaje` (Task 1).
- Produces: `HuecoDic08` gana el campo `anclado: bool = True`. `contexto_dic08(m, huecos)` devuelve el contexto **ya prefiltrado y ya marcado**. La firma no cambia.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contexto_prefiltro.py
from gpmc.agentes.contexto import contexto_dic08
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Campo, Manifiesto, OpcionCatalogo, Pantalla


def _m():
    return Manifiesto(
        nombre="Tramite de prueba",
        pantallas=[
            Pantalla(id="p1", nombre="Captura", campos=[
                Campo(nombre="procedencia", etiqueta="Procedencia",
                      catalogo=[OpcionCatalogo(valor="moral", etiqueta="Moral")]),
                Campo(nombre="domicilio_fiscal", etiqueta="Domicilio fiscal"),
                Campo(nombre="telefono_contacto", etiqueta="Teléfono de contacto"),
                Campo(nombre="rfc", etiqueta="RFC"),
            ]),
        ],
    )


def _hueco(campo, prosa):
    return Hueco(nivel="falta_dato", codigo="DIC-08", ubicacion=f"p1::{campo}",
                 mensaje=f"la condición de visibilidad de '{campo}' ({campo}) "
                         f"no se pudo interpretar: «{prosa}»")


def test_manda_solo_los_candidatos_que_la_prosa_menciona():
    ctx = contexto_dic08(_m(), [_hueco("rfc", "Visible solo si Procedencia es moral")])
    assert [c.nombre for c in ctx.campos] == ["procedencia"]
    assert ctx.huecos[0].candidatos == ["procedencia"]


def test_el_prefiltro_reduce_el_tamano_del_contexto():
    from gpmc.agentes.contexto import estimar_tokens
    h = [_hueco("rfc", "Visible solo si Procedencia es moral")]
    ctx = contexto_dic08(_m(), h)
    # Cuatro campos declarados, uno solo mencionado: el contexto encoge.
    assert estimar_tokens(ctx) < 200


def test_red_de_seguridad_si_el_prefiltro_deja_cero_candidatos():
    # La prosa ancla (menciona "domicilio") pero escrito de forma que, si el
    # prefiltro fallara, no debe quedarse sin candidatos que ofrecer.
    ctx = contexto_dic08(_m(), [_hueco("rfc", "Visible solo si Domicilio fiscal existe")])
    assert ctx.huecos[0].candidatos, "un hueco anclado nunca sale sin candidatos"


def test_marca_como_no_anclado_lo_que_no_menciona_ningun_campo():
    ctx = contexto_dic08(
        _m(), [_hueco("rfc", "Solo si la validación de formato detecta errores al enviar")])
    assert ctx.huecos[0].anclado is False


def test_un_hueco_no_anclado_conserva_sus_candidatos_completos():
    # No se recorta lo que no se va a mandar: quien decida mostrarlo los necesita.
    ctx = contexto_dic08(
        _m(), [_hueco("rfc", "Solo si la validación de formato detecta errores al enviar")])
    assert len(ctx.huecos[0].candidatos) == 3


def test_lo_anclado_sigue_marcado_como_anclado():
    ctx = contexto_dic08(_m(), [_hueco("rfc", "Visible solo si Procedencia es moral")])
    assert ctx.huecos[0].anclado is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_contexto_prefiltro.py -v`
Expected: FAIL — `HuecoDic08` no tiene `anclado`, y `ctx.campos` trae los cuatro campos.

- [ ] **Step 3: Write minimal implementation**

En `src/gpmc/agentes/contexto.py`, agregar el import y el campo:

```python
from gpmc.agentes.anclaje import palabras, sin_anclaje, tokens
```

```python
class HuecoDic08(BaseModel):
    ubicacion: str
    campo: str
    etiqueta: str
    pantalla: str
    prosa: str
    candidatos: list[str]
    # False -> la prosa no menciona ningun campo: no se manda al modelo.
    anclado: bool = True
```

Agregar la función de prefiltro, justo antes de `contexto_dic08`:

```python
def _prefiltrar(ctx: ContextoLote) -> ContextoLote:
    """Recorta candidatos a los que la prosa menciona, y marca los no anclados.

    Medido el 2026-09-17: 15804 -> 7838 tokens sobre los seis expedientes
    reales (50%). Y con 5 candidatos en vez de 45 hay muchas menos formas de
    elegir el campo equivocado, asi que tambien sube la precision.
    """
    por_nombre = {c.nombre: c for c in ctx.campos}
    for h in ctx.huecos:
        propios = [por_nombre[n] for n in h.candidatos if n in por_nombre]
        if sin_anclaje(h.prosa, propios):
            # No se manda al modelo: se deja entero para quien lo muestre.
            h.anclado = False
            continue
        del_texto = palabras(h.prosa)
        utiles = [c.nombre for c in propios
                  if (tokens(c.nombre) | tokens(c.etiqueta)
                      | tokens(" ".join(c.valores))) & del_texto]
        # Red de seguridad: ahorrar nunca puede dejar a un hueco anclado sin
        # nada que ofrecer. Si el recorte queda vacio, se manda la lista entera.
        h.candidatos = utiles or h.candidatos
    usados = {n for h in ctx.huecos if h.anclado for n in h.candidatos}
    usados |= {n for h in ctx.huecos if not h.anclado for n in h.candidatos}
    ctx.campos = [c for c in ctx.campos if c.nombre in usados]
    return ctx
```

Y en `contexto_dic08`, sustituir el `return ctx` final por:

```python
    return _prefiltrar(ctx)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_contexto_prefiltro.py tests/test_agentes.py -v`
Expected: PASS.

- [ ] **Step 5: Confirmar el 50 % sobre el corpus real**

Run:
```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python - <<'PY'
from pathlib import Path
from gpmc.extractores.expediente import extraer_expediente
from gpmc.agentes.contexto import contexto_dic08, estimar_tokens
BASE = Path("/Users/danielhernandezrubio/Downloads/EXPEDIENTES DE TRAMITES CON REINGENIERIA")
t = 0
for d in sorted(p for p in BASE.iterdir() if p.is_dir()):
    if not any(d.glob("*iccionario*")): continue
    r = extraer_expediente(d)
    if not r.manifiesto: continue
    hs = [h for h in r.huecos if h.codigo == "DIC-08"]
    if hs: t += estimar_tokens(contexto_dic08(r.manifiesto, hs))
print(f"tokens totales con prefiltro: {t}  (antes: 15804)")
PY
```
Expected: **7 838** (un 50 % menos que los 15 804 de antes). Los huecos sin anclaje conservan su lista completa a proposito —no se mandan al modelo, pero quien los muestre los necesita—, y por eso no baja hasta 7 665. Si sale muy distinto, **parar y avisar**.

- [ ] **Step 6: Commit**

```bash
git add src/gpmc/agentes/contexto.py tests/test_contexto_prefiltro.py
git commit -m "perf(agentes): prefiltro lexico de candidatos, 50% menos tokens medido"
```

---

## Task 3: `cache.py` — no volver a pagar la misma pregunta

**Files:**
- Create: `src/gpmc/agentes/cache.py`
- Test: `tests/test_cache_ia.py`

**Interfaces:**
- Consumes: nada del proyecto; sólo `hashlib`, `json`, `pathlib`.
- Produces: `RUTA_CACHE: str`, `huella(version_prompt: str, instruccion_hash: str, codigo: str, prosa: str, candidatos: list[str]) -> str`, `leer(raiz: Path, h: str) -> Optional[dict]`, `escribir(raiz: Path, h: str, dato: dict) -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cache_ia.py
import json

from gpmc.agentes import cache


ARGS = dict(version_prompt="dic08-v2", instruccion_hash="abc123", codigo="DIC-08",
            prosa="Visible solo si Procedencia es moral",
            candidatos=["procedencia", "rfc"])


def test_la_misma_pregunta_da_la_misma_huella():
    assert cache.huella(**ARGS) == cache.huella(**ARGS)


def test_cambiar_la_version_del_prompt_cambia_la_huella():
    otros = dict(ARGS, version_prompt="dic08-v3")
    assert cache.huella(**ARGS) != cache.huella(**otros)


def test_cambiar_la_prosa_cambia_la_huella():
    otros = dict(ARGS, prosa="Visible solo si Procedencia es fisica")
    assert cache.huella(**ARGS) != cache.huella(**otros)


def test_el_orden_de_los_candidatos_no_cambia_la_huella():
    otros = dict(ARGS, candidatos=["rfc", "procedencia"])
    assert cache.huella(**ARGS) == cache.huella(**otros)


def test_lo_escrito_se_lee(tmp_path):
    h = cache.huella(**ARGS)
    cache.escribir(tmp_path, h, {"veredicto": "aceptable"})
    assert cache.leer(tmp_path, h) == {"veredicto": "aceptable"}


def test_lo_no_escrito_devuelve_none(tmp_path):
    assert cache.leer(tmp_path, cache.huella(**ARGS)) is None


def test_una_cache_ilegible_no_rompe_nada(tmp_path):
    h = cache.huella(**ARGS)
    cache.escribir(tmp_path, h, {"veredicto": "aceptable"})
    ruta = next((tmp_path / cache.RUTA_CACHE).rglob("*.json"))
    ruta.write_text("{esto no es json", encoding="utf-8")
    assert cache.leer(tmp_path, h) is None


def test_tambien_se_cachea_un_rechazo(tmp_path):
    # Repetir una llamada para volver a rechazarla cuesta lo mismo que aceptarla.
    h = cache.huella(**ARGS)
    cache.escribir(tmp_path, h, {"veredicto": "campo_inexistente"})
    assert cache.leer(tmp_path, h)["veredicto"] == "campo_inexistente"


def test_la_huella_no_lleva_la_sesion(tmp_path):
    # Dos sesiones distintas con la misma pregunta comparten entrada.
    assert "sid" not in json.dumps(ARGS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_cache_ia.py -v`
Expected: FAIL con `ImportError: cannot import name 'cache'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/gpmc/agentes/cache.py
"""Cache de propuestas por inconsistencia, en el almacen GLOBAL.

Medido el 2026-09-17: 13% de las condiciones DIC-08 del corpus se repiten. Y es
un piso, no un techo: Simplificacion reenvia el mismo expediente corregido
varias veces y hoy cada reenvio se paga entero.

Vive junto a `bitacora-ia.jsonl` y NO en la carpeta de sesion, que se purga por
TTL. La huella no lleva `sid`: dos sesiones con la misma pregunta comparten
entrada. Una cache ilegible se ignora; nunca puede romper la revision.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional

RUTA_CACHE = "cache-ia"


def huella(version_prompt: str, instruccion_hash: str, codigo: str, prosa: str,
           candidatos: list) -> str:
    """Identidad de la pregunta. El prompt entra en la clave, asi que cambiarlo
    invalida la cache sola: no hace falta purgarla a mano."""
    material = json.dumps(
        [version_prompt, instruccion_hash, codigo, prosa.strip(), sorted(candidatos)],
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _ruta(raiz: Path, h: str) -> Path:
    # Dos niveles para no dejar miles de archivos en una sola carpeta.
    return Path(raiz) / RUTA_CACHE / h[:2] / f"{h}.json"


def leer(raiz: Path, h: str) -> Optional[dict]:
    ruta = _ruta(raiz, h)
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def escribir(raiz: Path, h: str, dato: dict) -> None:
    ruta = _ruta(raiz, h)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(dato, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_cache_ia.py -v`
Expected: PASS, 9 pruebas.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/agentes/cache.py tests/test_cache_ia.py
git commit -m "feat(agentes): cache de propuestas por huella de (prompt + frase + candidatos)"
```

---

## Task 4: Enganchar anclaje y caché en el generador, y dejarlos ver en la API

**Files:**
- Modify: `src/gpmc/agentes/dic08.py`
- Modify: `src/gpmc/web/api.py` (el filtro de `leer_propuestas`)
- Test: `tests/test_dic08_capas.py`

**Interfaces:**
- Consumes: `anclaje.MOTIVO_SIN_ANCLAJE` (Task 1), `HuecoDic08.anclado` (Task 2), `cache.huella/leer/escribir` (Task 3).
- Produces: `Propuesta.veredicto` admite el valor nuevo `"sin_anclaje"`. `proponer_lote` conserva su firma `(m, huecos, proveedor, raiz, sid, max_tokens=24000) -> list[Propuesta]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dic08_capas.py
from gpmc.agentes import cache
from gpmc.agentes.dic08 import proponer_lote
from gpmc.agentes.prompt import VERSION_PROMPT, hash_instruccion
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Campo, Manifiesto, OpcionCatalogo, Pantalla


class ProveedorContador:
    """Cuenta llamadas y responde siempre lo mismo."""
    nombre = "falso"

    def __init__(self):
        self.llamadas = 0

    def completar(self, instrucciones, contexto, esquema):
        from gpmc.agentes.proveedor import Respuesta
        self.llamadas += 1
        import json
        cuerpo = json.dumps({"propuestas": [{
            "ubicacion": "p1::rfc",
            "condicion": {"campo": "procedencia", "operador": "==", "igual": "moral", "y": []},
            "motivo": None, "confianza": "alta"}]})
        return Respuesta(texto=cuerpo, modelo="falso-1", tokens_entrada=10,
                         tokens_salida=5, duracion_ms=1)


def _m():
    return Manifiesto(nombre="Prueba", pantallas=[Pantalla(id="p1", nombre="Captura", campos=[
        Campo(nombre="procedencia", etiqueta="Procedencia",
              catalogo=[OpcionCatalogo(valor="moral", etiqueta="Moral")]),
        Campo(nombre="rfc", etiqueta="RFC"),
    ])])


def _hueco(prosa):
    return Hueco(nivel="falta_dato", codigo="DIC-08", ubicacion="p1::rfc",
                 mensaje=f"la condición de visibilidad de 'RFC' (rfc) no se "
                         f"pudo interpretar: «{prosa}»")


def test_una_condicion_sin_anclaje_no_llama_al_proveedor(tmp_path):
    prov = ProveedorContador()
    props = proponer_lote(_m(), [_hueco("Solo si la validación de formato detecta errores al enviar")],
                          prov, tmp_path, "s" * 16)
    assert prov.llamadas == 0
    assert len(props) == 1
    assert props[0].veredicto == "sin_anclaje"
    assert props[0].condicion is None
    assert "campo" in (props[0].motivo_modelo or "").lower()


def test_una_condicion_anclada_si_llama_y_propone(tmp_path):
    prov = ProveedorContador()
    props = proponer_lote(_m(), [_hueco("Visible solo si Procedencia es moral")],
                          prov, tmp_path, "s" * 16)
    assert prov.llamadas == 1
    assert props[0].veredicto == "aceptable"


def test_la_segunda_vez_sale_de_cache_y_no_llama(tmp_path):
    prov = ProveedorContador()
    h = [_hueco("Visible solo si Procedencia es moral")]
    proponer_lote(_m(), h, prov, tmp_path, "s" * 16)
    assert prov.llamadas == 1
    props = proponer_lote(_m(), h, prov, tmp_path, "s" * 16)
    assert prov.llamadas == 1, "la segunda vez no debe volver a preguntar"
    assert props[0].veredicto == "aceptable"
    assert props[0].condicion is not None


def test_el_acierto_de_cache_queda_en_la_bitacora(tmp_path):
    from gpmc.agentes.bitacora import leer
    prov = ProveedorContador()
    h = [_hueco("Visible solo si Procedencia es moral")]
    proponer_lote(_m(), h, prov, tmp_path, "s" * 16)
    proponer_lote(_m(), h, prov, tmp_path, "s" * 16)
    entradas = leer(tmp_path)
    assert any("cache" in (e.get("alertas") or []) for e in entradas), \
        "la Licencia AI pide trazabilidad: un acierto de cache es una interaccion"


def test_los_codigos_sin_dato_en_el_origen_nunca_llegan_al_modelo(tmp_path):
    """Spec 6.2(b): en DIC-02 y META-01 la informacion no existe en ninguna
    parte del expediente. Un agente que los rellene inventa derecho
    administrativo. Hoy es cierto por construccion; esto lo deja verificado."""
    prov = ProveedorContador()
    otros = [
        Hueco(nivel="falta_dato", codigo="DIC-02", ubicacion="p1",
              mensaje="el catálogo de 'Tipo de Sanción' está declarado como pendiente"),
        Hueco(nivel="falta_dato", codigo="META-01", ubicacion="metadatos",
              mensaje="no se encontro el tiempo de respuesta declarado"),
    ]
    props = proponer_lote(_m(), otros, prov, tmp_path, "s" * 16)
    assert prov.llamadas == 0
    assert props == []


def test_cambiar_la_version_del_prompt_invalida_la_cache(tmp_path):
    prov = ProveedorContador()
    h = [_hueco("Visible solo si Procedencia es moral")]
    proponer_lote(_m(), h, prov, tmp_path, "s" * 16)
    # Una huella con otra version no existe todavia.
    otra = cache.huella(version_prompt="otra-version", instruccion_hash=hash_instruccion(),
                        codigo="DIC-08", prosa="Visible solo si Procedencia es moral",
                        candidatos=["procedencia"])
    assert cache.leer(tmp_path, otra) is None
    assert VERSION_PROMPT != "otra-version"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python -m pytest tests/test_dic08_capas.py -v`
Expected: FAIL — hoy se llama al proveedor también para la frase sin anclaje, y no hay caché.

- [ ] **Step 3: Write minimal implementation**

En `src/gpmc/agentes/dic08.py`, agregar imports:

```python
from gpmc.agentes import cache
from gpmc.agentes.anclaje import MOTIVO_SIN_ANCLAJE
```

Agregar el helper de huella y el registro de acierto de caché, antes de `proponer_lote`:

```python
def _huella_de(h) -> str:
    return cache.huella(version_prompt=VERSION_PROMPT, instruccion_hash=hash_instruccion(),
                        codigo="DIC-08", prosa=h.prosa, candidatos=list(h.candidatos))


def _registrar_cache(raiz: Path, sid: str, proveedor, h) -> None:
    """Un acierto de cache es una interaccion: la Licencia AI pide registrarla
    aunque no haya habido red."""
    registrar(raiz, Interaccion(
        sid=sid, proveedor=proveedor.nombre, modelo="(cache)", version_prompt=VERSION_PROMPT,
        solicitud={"huecos": [h.ubicacion], "n_campos": len(h.candidatos), "n_caracteres": 0},
        instruccion_hash=hash_instruccion(), estado="procesada", alertas=["cache"]))
```

Sustituir el cuerpo de `proponer_lote` por:

```python
def proponer_lote(m: Manifiesto, huecos: list, proveedor, raiz: Path, sid: str,
                  max_tokens: int = 24000) -> list:
    ctx = contexto_dic08(m, huecos)
    if not ctx.huecos:
        return []

    # Capa 0: lo que no ancla en ningun campo no se le pregunta a nadie.
    resultado = {}
    pendientes = []
    for h in ctx.huecos:
        if not h.anclado:
            resultado[h.ubicacion] = Propuesta(
                id=uuid.uuid4().hex, ubicacion=h.ubicacion, cita=_cita(m, h),
                creada=_ahora(), veredicto="sin_anclaje", motivo_modelo=MOTIVO_SIN_ANCLAJE)
            continue
        # Capa 2: lo ya preguntado no se vuelve a pagar.
        guardado = cache.leer(raiz, _huella_de(h))
        if guardado is not None:
            try:
                p = Propuesta(**{**guardado, "id": uuid.uuid4().hex, "creada": _ahora()})
            except ValidationError:
                p = None
            if p is not None:
                _registrar_cache(raiz, sid, proveedor, h)
                resultado[h.ubicacion] = p
                continue
        pendientes.append(h)

    if pendientes:
        ctx_pend = _subconjunto(ctx, pendientes)
        partes = partir_lote(ctx_pend, max_tokens)
        alertas = ["lote_partido"] if len(partes) > 1 else []
        for parte in partes:
            if not parte.huecos:
                continue
            parte_alertas = alertas + [f"hueco_omitido:{u}" for (u, _) in parte.omitidos]
            for p in _procesar_parte(m, parte, proveedor, raiz, sid, parte_alertas):
                resultado[p.ubicacion] = p
                h = next(x for x in parte.huecos if x.ubicacion == p.ubicacion)
                cache.escribir(raiz, _huella_de(h),
                               p.model_dump(mode="json", exclude={"id", "creada", "decidida",
                                                                 "decision", "condicion_final"}))

    return [resultado[h.ubicacion] for h in ctx.huecos if h.ubicacion in resultado]
```

Agregar el import de `_subconjunto` en la línea de `contexto`:

```python
from gpmc.agentes.contexto import ContextoLote, _subconjunto, contexto_dic08, partir_lote
```

En `src/gpmc/web/api.py`, en `leer_propuestas`, cambiar el filtro:

```python
        # `sin_anclaje` tambien se muestra: la tarjeta explica por que no hay
        # propuesta, en vez de salir vacia y dejar a la persona trabada.
        visibles = [p for p in d.get("propuestas", [])
                    if p.get("veredicto") in ("aceptable", "sin_anclaje")
                    and p.get("decision") is None]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && set -o pipefail && .venv/bin/python -m pytest tests/ -q`
Expected: PASS, toda la suite. Si algo de `tests/test_web_propuestas*.py` falla por el filtro nuevo, actualizar esa prueba explicando el cambio — nunca ablandarla.

- [ ] **Step 5: Commit**

```bash
git add src/gpmc/agentes/dic08.py src/gpmc/web/api.py tests/test_dic08_capas.py
git commit -m "feat(agentes): capa 0 y cache enchufadas al generador; sin_anclaje visible en la API"
```

---

## Task 5: Explicaciones por código — la capa 0 en pantalla

**Files:**
- Modify: `frontend/src/features/huecos/lenguaje.ts`
- Test: `frontend/src/features/huecos/lenguaje.explicaciones.test.ts`

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `export type Explicacion = { queEs: string; porQueSalio: string; comoSeResuelve: string }` y `export function explicacionDeCodigo(codigo: string): Explicacion | null`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/features/huecos/lenguaje.explicaciones.test.ts
import { describe, expect, it } from "vitest";

import { TITULOS_PARA_PRUEBA, explicacionDeCodigo } from "./lenguaje";

describe("explicaciones por codigo (capa 0: cero tokens)", () => {
  it("DIC-08 explica que es, por que salio y como se resuelve", () => {
    const e = explicacionDeCodigo("DIC-08");
    expect(e).not.toBeNull();
    expect(e!.queEs).toMatch(/condición de visibilidad/i);
    expect(e!.porQueSalio).toMatch(/Diccionario/i);
    expect(e!.comoSeResuelve).toMatch(/a mano|plataforma/i);
  });

  it("DIC-02 dice que el dato falta en el origen, no que haya que inventarlo", () => {
    const e = explicacionDeCodigo("DIC-02");
    expect(e!.comoSeResuelve).toMatch(/Simplificación/i);
  });

  it("META-01 tampoco se inventa", () => {
    expect(explicacionDeCodigo("META-01")!.comoSeResuelve).toMatch(/Simplificación/i);
  });

  it("un codigo desconocido devuelve null y la tarjeta no inventa nada", () => {
    expect(explicacionDeCodigo("XXX-99")).toBeNull();
  });

  it("todo codigo con titulo tiene explicacion: un codigo nuevo no queda mudo", () => {
    const sinExplicacion = Object.keys(TITULOS_PARA_PRUEBA).filter(
      (c) => explicacionDeCodigo(c) === null,
    );
    expect(sinExplicacion).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/lenguaje.explicaciones.test.ts`
Expected: FAIL — `explicacionDeCodigo` y `TITULOS_PARA_PRUEBA` no existen.

- [ ] **Step 3: Write minimal implementation**

En `frontend/src/features/huecos/lenguaje.ts`, exportar el mapa de títulos para la prueba de cobertura y agregar las explicaciones. Añadir al final del archivo:

```ts
/** Solo para la prueba de cobertura: ningún código debe quedarse sin explicación. */
export const TITULOS_PARA_PRUEBA = TITULOS;

export type Explicacion = {
  /** Qué es, en castellano y sin jerga del compilador. */
  queEs: string;
  /** Qué encontró —o no encontró— el extractor para emitirla. */
  porQueSalio: string;
  /** Qué puede hacer la persona, incluida la salida de configurarlo a mano. */
  comoSeResuelve: string;
};

/**
 * La capa 0 del ahorro de tokens: la respuesta a «¿qué significa esto?» NO
 * depende del expediente, depende del código. DIC-08 significa lo mismo en
 * Testamentos que en Reposición de Placas. Escribirlas a mano una vez cuesta
 * cero llamadas para siempre, responde al instante, y sale mejor que
 * preguntándole a un modelo: el compilador lo escribimos nosotros.
 *
 * Un código sin explicación devuelve null y la tarjeta no inventa una frase
 * generica. La prueba de cobertura impide que un código nuevo quede mudo.
 */
const EXPLICACIONES: Record<string, Explicacion> = {
  "INS-01": {
    queEs: "Falta uno de los documentos de entrada del expediente.",
    porQueSalio: "El compilador buscó el archivo en la carpeta y no lo encontró.",
    comoSeResuelve: "Pídele el documento al área de Simplificación y vuelve a subir la carpeta.",
  },
  "META-01": {
    queEs: "El tiempo que la dependencia tarda en resolver el trámite.",
    porQueSalio: "No aparece declarado en ninguno de los documentos del expediente.",
    comoSeResuelve:
      "Este dato no se puede deducir: es normativo. Hay que pedírselo a Simplificación.",
  },
  "META-02": {
    queEs: "La dependencia responsable del trámite.",
    porQueSalio: "No se encontró declarada en los metadatos del expediente.",
    comoSeResuelve: "Escríbela si la conoces, o pídesela a Simplificación.",
  },
  "META-03": {
    queEs: "El costo del trámite para el ciudadano.",
    porQueSalio: "No se encontró declarado en los metadatos del expediente.",
    comoSeResuelve:
      "Si es gratuito se escribe «Sin costo». Si no lo sabes, pídeselo a Simplificación.",
  },
  "META-04": {
    queEs: "El nombre oficial con el que se publica el trámite.",
    porQueSalio: "No se encontró declarado en los metadatos del expediente.",
    comoSeResuelve: "Escribe el nombre tal como se publica en el catálogo de trámites.",
  },
  "META-05": {
    queEs: "La homoclave del trámite.",
    porQueSalio: "No se encontró declarada en los metadatos del expediente.",
    comoSeResuelve: "Confírmala con Simplificación; no bloquea la descarga del .gpm.",
  },
  "META-06": {
    queEs: "A quién va dirigido el trámite: ciudadano, empresa o servidor público.",
    porQueSalio: "No se encontró declarado en los metadatos del expediente.",
    comoSeResuelve: "Confírmalo con Simplificación; no bloquea la descarga del .gpm.",
  },
  "DIC-01": {
    queEs: "Un campo del Diccionario que no quedó asignado a ninguna pantalla.",
    porQueSalio:
      "El Diccionario declara el campo pero no dice en qué pantalla se captura.",
    comoSeResuelve: "Confirma la pantalla que te propone el compilador, o corrígela.",
  },
  "DIC-02": {
    queEs: "El catálogo de opciones de un campo de lista.",
    porQueSalio:
      "El Diccionario lo declara explícitamente como «pendiente»: las opciones no están escritas en ninguna parte.",
    comoSeResuelve:
      "El dato no existe en el expediente y no se puede inventar. Hay que pedirle el catálogo a Simplificación.",
  },
  "DIC-04": {
    queEs: "Cómo se reparten los campos entre pantallas.",
    porQueSalio: "El Diccionario no divide los campos en pantallas de forma reconocible.",
    comoSeResuelve: "Confirma la división que propone el compilador.",
  },
  "DIC-07": {
    queEs: "Un campo de lista que se quedó sin ninguna opción.",
    porQueSalio:
      "El campo está declarado como lista pero no se extrajo ninguna opción, ni del catálogo ni de las validaciones.",
    comoSeResuelve:
      "Si las opciones no están en el expediente, hay que pedírselas a Simplificación.",
  },
  "DIC-08": {
    queEs:
      "Una condición de visibilidad: cuándo se le muestra este campo al ciudadano y cuándo se le oculta.",
    porQueSalio:
      "El Diccionario escribió la condición en prosa y el compilador no supo convertirla en una regla entre campos.",
    comoSeResuelve:
      "Elige el campo que decide y con qué valor se compara. Si la frase no depende de ningún campo del formulario —por ejemplo, si habla de un estado del sistema— entonces no es una regla: se configura a mano en la plataforma.",
  },
  "API-03": {
    queEs: "El campo del que depende otro para poder consultarse.",
    porQueSalio: "La integración declara una dependencia que no nombra el campo.",
    comoSeResuelve: "Elige el campo que hay que llenar antes.",
  },
  "API-04": {
    queEs: "La conexión con otro sistema que alimenta este campo.",
    porQueSalio: "El expediente menciona la integración pero no su punto de conexión.",
    comoSeResuelve: "Confírmalo con el área técnica, o configúralo a mano en la plataforma.",
  },
  "DOC-02": {
    queEs: "Una variable de una plantilla que no casa con ningún campo del formulario.",
    porQueSalio: "La plantilla usa un marcador que el Diccionario no declara.",
    comoSeResuelve: "Indica con qué campo corresponde, o corrige la plantilla.",
  },
  "DOC-03": {
    queEs: "Una plantilla de documento que no se pudo leer.",
    porQueSalio: "El archivo está en un formato que el compilador no interpreta.",
    comoSeResuelve: "Pide la plantilla en un formato legible, o configúrala en la plataforma.",
  },
  "DOC-04": {
    queEs: "En qué momento del flujo se genera el documento.",
    porQueSalio: "El expediente no dice en qué tarea se produce.",
    comoSeResuelve: "Elige la tarea del flujo en la que se emite.",
  },
  "MMD-02": {
    queEs: "Un nodo del diagrama que el Diccionario no declara.",
    porQueSalio: "El diagrama TO-BE nombra algo que no existe como pantalla ni como campo.",
    comoSeResuelve: "Confirma a qué corresponde, o configúralo a mano.",
  },
  "MMD-03": {
    queEs: "Quién realiza una tarea del flujo.",
    porQueSalio: "El diagrama no asigna responsable a esa tarea.",
    comoSeResuelve: "Elige el área o el rol que la ejecuta.",
  },
  "MMD-04": {
    queEs: "El campo que consulta una decisión del flujo para elegir camino.",
    porQueSalio: "La compuerta del diagrama no nombra ningún campo con @@.",
    comoSeResuelve:
      "Elige el campo del formulario que decide. Si la decisión no depende de un campo, se configura a mano en la plataforma.",
  },
  "FLU-01": {
    queEs: "Compuertas del diagrama que el flujo compilado no reproduce.",
    porQueSalio:
      "Para ramificar hace falta que cada compuerta nombre un campo y que cada salida resuelva a un valor; algo de eso faltó.",
    comoSeResuelve:
      "Completa los campos de las compuertas, o acepta el flujo lineal y ajusta la ramificación en la plataforma.",
  },
  "FLU-02": {
    queEs: "La correspondencia entre las tareas del diagrama y las pantallas del Diccionario.",
    porQueSalio: "El diagrama tiene un número de tareas distinto al de pantallas declaradas.",
    comoSeResuelve: "Confirma la correspondencia; no bloquea la descarga del .gpm.",
  },
  "FLU-03": {
    queEs: "El flujo se construyó ramificado a partir del diagrama.",
    porQueSalio: "Las compuertas cumplieron todas las condiciones para ramificar.",
    comoSeResuelve: "Solo hay que confirmarlo de un vistazo.",
  },
};

export function explicacionDeCodigo(codigo: string): Explicacion | null {
  return EXPLICACIONES[codigo] ?? null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/lenguaje.explicaciones.test.ts src/features/huecos/lenguaje.test.ts`
Expected: PASS. Si la prueba de cobertura señala un código sin explicación, **escribirla** — no quitar el código del mapa.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/lenguaje.ts frontend/src/features/huecos/lenguaje.explicaciones.test.ts
git commit -m "feat(ux): explicaciones por codigo escritas a mano (capa 0, cero tokens)"
```

---

## Task 6: `agruparPorCodigo` — las columnas del tablero

**Files:**
- Modify: `frontend/src/features/huecos/agrupar.ts`
- Test: `frontend/src/features/huecos/agrupar.codigo.test.ts`

**Interfaces:**
- Consumes: `tituloDeCodigo` de `lenguaje.ts`, tipo `Hueco` de `@/lib/types`.
- Produces: `export type ColumnaHuecos = { codigo: string; titulo: string; huecos: Hueco[]; total: number }` y `export function agruparPorCodigo(huecos: Hueco[], resueltas?: Set<string>): ColumnaHuecos[]`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/features/huecos/agrupar.codigo.test.ts
import { describe, expect, it } from "vitest";

import { agruparPorCodigo } from "./agrupar";
import type { Hueco } from "@/lib/types";

const h = (codigo: string, ubicacion: string): Hueco => ({
  nivel: "falta_dato", codigo, ubicacion, mensaje: "x", propuesta: null,
});

describe("agruparPorCodigo", () => {
  it("hace una columna por codigo, con el titulo que ya usa la barra lateral", () => {
    const cols = agruparPorCodigo([h("DIC-08", "p1::a"), h("DIC-08", "p1::b"), h("MMD-04", "D1")]);
    expect(cols.map((c) => [c.codigo, c.titulo, c.total])).toEqual([
      ["DIC-08", "Visibilidad de un campo", 2],
      ["MMD-04", "Decisión del flujo", 1],
    ]);
  });

  it("ordena de mas frecuente a menos, con desempate alfabetico estable", () => {
    const cols = agruparPorCodigo([h("MMD-04", "D1"), h("DIC-02", "p2"), h("DIC-08", "p1::a")]);
    expect(cols.map((c) => c.codigo)).toEqual(["DIC-02", "DIC-08", "MMD-04"]);
  });

  it("un codigo sin inconsistencias no genera columna", () => {
    expect(agruparPorCodigo([]).length).toBe(0);
  });

  it("conserva dentro de cada columna el orden en que llegaron", () => {
    const cols = agruparPorCodigo([h("DIC-08", "p2::z"), h("DIC-08", "p1::a")]);
    expect(cols[0].huecos.map((x) => x.ubicacion)).toEqual(["p2::z", "p1::a"]);
  });

  it("una columna totalmente resuelta sigue existiendo, para poder verla cerrada", () => {
    const cols = agruparPorCodigo([h("DIC-08", "p1::a")], new Set(["DIC-08|p1::a"]));
    expect(cols).toHaveLength(1);
    expect(cols[0].total).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/agrupar.codigo.test.ts`
Expected: FAIL — `agruparPorCodigo` no existe.

- [ ] **Step 3: Write minimal implementation**

En `frontend/src/features/huecos/agrupar.ts`, agregar el import y la función:

```ts
import { tituloDeCodigo } from "./lenguaje";

export type ColumnaHuecos = {
  codigo: string;
  titulo: string;
  huecos: Hueco[];
  total: number;
};

/**
 * Una columna por codigo de validacion, de mas frecuente a menos.
 *
 * El tablero sustituye al riel numerado del 1 al 19: con una lista la persona
 * no sabe cuantas de cada tipo le faltan. Los titulos son los mismos que ya se
 * leen en la barra lateral —reusar ese vocabulario importa: es el que la
 * Direccion ya reconoce—.
 *
 * `resueltas` (claves `codigo|ubicacion`) NO quita columnas: una columna
 * terminada se sigue dibujando, cerrada, para que se vea el avance.
 */
export function agruparPorCodigo(
  huecos: Hueco[],
  _resueltas: Set<string> = new Set(),
): ColumnaHuecos[] {
  const porCodigo = new Map<string, Hueco[]>();
  for (const h of huecos) {
    const previos = porCodigo.get(h.codigo);
    if (previos) previos.push(h);
    else porCodigo.set(h.codigo, [h]);
  }
  return [...porCodigo.entries()]
    .map(([codigo, propios]) => ({
      codigo,
      titulo: tituloDeCodigo(codigo),
      huecos: propios,
      total: propios.length,
    }))
    .sort((a, b) => b.total - a.total || a.codigo.localeCompare(b.codigo));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/agrupar.codigo.test.ts src/features/huecos/agrupar.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/agrupar.ts frontend/src/features/huecos/agrupar.codigo.test.ts
git commit -m "feat(ux): agrupar inconsistencias por codigo para las columnas del tablero"
```

---

## Task 7: `TarjetaChica` y `ColumnaCodigo` — la superficie de selección

**Files:**
- Create: `frontend/src/features/huecos/TarjetaChica.tsx`
- Create: `frontend/src/features/huecos/ColumnaCodigo.tsx`
- Test: `frontend/src/features/huecos/ColumnaCodigo.test.tsx`

**Interfaces:**
- Consumes: `ColumnaHuecos` (Task 6), `Hueco` y `Propuesta` de `@/lib/types`.
- Produces:
  - `TarjetaChica({ hueco, propuesta, resuelta, abierta, onAbrir })` donde `onAbrir: () => void`.
  - `ColumnaCodigo({ columna, resueltas, propuestas, abiertaClave, onAbrir })` con `resueltas: Set<string>`, `propuestas: Map<string, Propuesta>`, `abiertaClave: string | null`, `onAbrir: (clave: string) => void`.
  - Ambos usan la clave `` `${hueco.codigo}|${hueco.ubicacion}` ``.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/huecos/ColumnaCodigo.test.tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import ColumnaCodigo from "./ColumnaCodigo";
import type { Hueco, Propuesta } from "@/lib/types";

const h = (ubicacion: string): Hueco => ({
  nivel: "falta_dato", codigo: "DIC-08", ubicacion,
  mensaje: `la condición de visibilidad de 'RFC' (rfc) no se pudo interpretar: «x»`,
  propuesta: null,
});

const columna = {
  codigo: "DIC-08",
  titulo: "Visibilidad de un campo",
  huecos: [h("p1::rfc"), h("p2::curp")],
  total: 2,
};

function pintar(extra = {}) {
  return render(
    <ColumnaCodigo
      columna={columna}
      resueltas={new Set<string>()}
      propuestas={new Map<string, Propuesta>()}
      abiertaClave={null}
      onAbrir={vi.fn()}
      {...extra}
    />,
  );
}

it("encabeza con el titulo y cuantas faltan de cuantas", () => {
  pintar();
  const cab = screen.getByRole("heading", { name: /Visibilidad de un campo/i });
  expect(cab).toBeInTheDocument();
  expect(screen.getByText(/0 de 2/)).toBeInTheDocument();
});

it("dibuja una tarjeta por inconsistencia, nombrada por su campo", () => {
  pintar();
  expect(screen.getAllByRole("button")).toHaveLength(2);
  expect(screen.getByRole("button", { name: /rfc/i })).toBeInTheDocument();
});

it("al hacer clic avisa cual se abrio, con su clave", async () => {
  const onAbrir = vi.fn();
  pintar({ onAbrir });
  await userEvent.click(screen.getByRole("button", { name: /rfc/i }));
  expect(onAbrir).toHaveBeenCalledWith("DIC-08|p1::rfc");
});

it("una resuelta se marca y la cuenta lo refleja", () => {
  pintar({ resueltas: new Set(["DIC-08|p1::rfc"]) });
  expect(screen.getByText(/1 de 2/)).toBeInTheDocument();
  expect(within(screen.getByRole("button", { name: /rfc/i })).getByText(/resuelta/i))
    .toBeInTheDocument();
});

it("marca las que ya tienen propuesta del agente", () => {
  const p = { id: "x", ubicacion: "p1::rfc", veredicto: "aceptable" } as unknown as Propuesta;
  pintar({ propuestas: new Map([["DIC-08|p1::rfc", p]]) });
  expect(within(screen.getByRole("button", { name: /rfc/i })).getByText(/propuesta/i))
    .toBeInTheDocument();
});

it("la abierta se anuncia como tal para lectores de pantalla", () => {
  pintar({ abiertaClave: "DIC-08|p1::rfc" });
  expect(screen.getByRole("button", { name: /rfc/i })).toHaveAttribute("aria-expanded", "true");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/ColumnaCodigo.test.tsx`
Expected: FAIL — los componentes no existen.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/features/huecos/TarjetaChica.tsx
import { Check, Sparkles } from "lucide-react";

import { cn } from "cn";
import type { Hueco, Propuesta } from "@/lib/types";

import { leerMensajeVisibilidad } from "./lenguaje";

/**
 * Una inconsistencia como tarjeta de SELECCION: sirve para escoger, no para
 * resolver. Por eso trae solo el nombre visible, el estado y si el agente ya
 * propuso algo; todo lo demas vive en la tarjeta abierta.
 */
export default function TarjetaChica({
  hueco,
  propuesta = null,
  resuelta = false,
  abierta = false,
  onAbrir,
}: {
  hueco: Hueco;
  propuesta?: Propuesta | null;
  resuelta?: boolean;
  abierta?: boolean;
  onAbrir: () => void;
}) {
  const leido = leerMensajeVisibilidad(hueco.mensaje);
  // El nombre visible: la etiqueta del campo si el mensaje la trae; si no, la
  // ubicacion, que siempre existe.
  const nombre = leido?.etiqueta ?? hueco.ubicacion;
  return (
    <button
      type="button"
      onClick={onAbrir}
      aria-expanded={abierta}
      className={cn(
        "flex w-full flex-col items-start gap-1 rounded-lg border p-3 text-left text-sm transition-colors",
        abierta ? "border-primary bg-primary/5" : "border-border bg-card hover:bg-muted/50",
        resuelta && "opacity-70",
      )}
    >
      <span className="font-medium text-foreground">{nombre}</span>
      <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        {resuelta ? (
          <span className="flex items-center gap-1 text-primary">
            <Check aria-hidden className="size-3" />
            resuelta
          </span>
        ) : (
          <span>{hueco.nivel === "por_confirmar" ? "solo confirmar" : "falta un dato"}</span>
        )}
        {propuesta && !resuelta ? (
          <span className="flex items-center gap-1 text-secondary">
            <Sparkles aria-hidden className="size-3" />
            propuesta
          </span>
        ) : null}
      </span>
    </button>
  );
}
```

```tsx
// frontend/src/features/huecos/ColumnaCodigo.tsx
import type { Propuesta } from "@/lib/types";

import type { ColumnaHuecos } from "./agrupar";
import TarjetaChica from "./TarjetaChica";

/** Clave estable de una inconsistencia: `codigo|ubicacion`. */
export const claveDe = (codigo: string, ubicacion: string): string => `${codigo}|${ubicacion}`;

/**
 * Una columna del tablero: su titulo, cuantas van de cuantas, y sus tarjetas.
 *
 * La cuenta es lo que el riel numerado no daba: saber cuanto falta DE ESTE
 * TIPO. Una columna terminada se sigue dibujando para que se vea el avance.
 */
export default function ColumnaCodigo({
  columna,
  resueltas,
  propuestas,
  abiertaClave,
  onAbrir,
}: {
  columna: ColumnaHuecos;
  resueltas: Set<string>;
  propuestas: Map<string, Propuesta>;
  abiertaClave: string | null;
  onAbrir: (clave: string) => void;
}) {
  const cerradas = columna.huecos.filter((h) =>
    resueltas.has(claveDe(h.codigo, h.ubicacion)),
  ).length;
  return (
    <section className="flex w-72 shrink-0 flex-col gap-2 rounded-xl bg-muted/40 p-3">
      <header className="flex flex-col gap-0.5">
        <h3 className="text-sm font-semibold tracking-tight text-foreground">
          {columna.titulo}
        </h3>
        <p className="text-xs text-muted-foreground">
          {cerradas} de {columna.total}
        </p>
      </header>
      <div className="flex flex-col gap-2">
        {columna.huecos.map((h) => {
          const clave = claveDe(h.codigo, h.ubicacion);
          return (
            <TarjetaChica
              key={clave}
              hueco={h}
              propuesta={propuestas.get(clave) ?? null}
              resuelta={resueltas.has(clave)}
              abierta={abiertaClave === clave}
              onAbrir={() => onAbrir(clave)}
            />
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/ColumnaCodigo.test.tsx`
Expected: PASS, 6 pruebas.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/TarjetaChica.tsx frontend/src/features/huecos/ColumnaCodigo.tsx frontend/src/features/huecos/ColumnaCodigo.test.tsx
git commit -m "feat(ux): tarjeta chica y columna por codigo del tablero"
```

---

## Task 8: `Explicacion` y `TarjetaAbierta` — resolver con la explicación al lado

**Files:**
- Create: `frontend/src/features/huecos/Explicacion.tsx`
- Create: `frontend/src/features/huecos/TarjetaAbierta.tsx`
- Test: `frontend/src/features/huecos/TarjetaAbierta.test.tsx`

**Interfaces:**
- Consumes: `explicacionDeCodigo` (Task 5), `TarjetaHueco` (existente, sin tocar), `Propuesta`/`Hueco` de `@/lib/types`.
- Produces:
  - `Explicacion({ codigo, motivoSinAnclaje })` con `motivoSinAnclaje?: string | null`.
  - `TarjetaAbierta({ hueco, sid, manifiesto, propuesta, ultimoActor, onResuelto, onCerrar })`, que envuelve a `TarjetaHueco` sin modificarlo.
  - **Ojo con la firma real:** `TarjetaHueco.onResuelto` es `(nuevo: RespuestaResuelto, hueco: Hueco, valor?: string) => void` —tres argumentos, no uno— y acepta `ultimoActor?: string`, que el control de `MMD-03` usa para preseleccionar el actor anterior. Hay que reenviar ambos o se pierde ese comportamiento.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/huecos/TarjetaAbierta.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  reconocer: vi.fn().mockResolvedValue({ huecos: [], reconocidos: [] }),
  resolver: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  decidirPropuesta: vi.fn().mockResolvedValue(undefined),
  camposDelManifiesto: () => [{ nombre: "estado", etiqueta: "Estado", catalogo: [] }],
}));

import TarjetaAbierta from "./TarjetaAbierta";
import type { Hueco, Propuesta } from "@/lib/types";

const HUECO: Hueco = {
  nivel: "falta_dato", codigo: "DIC-08", ubicacion: "p1::rfc",
  mensaje: "la condición de visibilidad de 'RFC' (rfc) no se pudo interpretar: «Solo si es moral»",
  propuesta: null,
};

function pintar(extra = {}) {
  return render(
    <TarjetaAbierta
      hueco={HUECO}
      sid={"a".repeat(16)}
      manifiesto={{}}
      propuesta={null}
      onResuelto={vi.fn()}
      onCerrar={vi.fn()}
      {...extra}
    />,
  );
}

it("muestra la explicacion del codigo sin gastar ninguna llamada", () => {
  pintar();
  expect(screen.getByText(/condición de visibilidad/i)).toBeInTheDocument();
  expect(screen.getByText(/Diccionario escribió la condición en prosa/i)).toBeInTheDocument();
});

it("sigue mostrando el control de resolucion de siempre", () => {
  pintar();
  expect(screen.getByText(/¿Cuándo debe verse/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/campo de la condición 1/i)).toBeInTheDocument();
});

it("cuando el agente no pudo, dice por que en vez de dejar la tarjeta muda", () => {
  const p = {
    id: "x", ubicacion: "p1::rfc", condicion: null,
    motivo_modelo: "la frase no menciona ningun campo del tramite",
    veredicto: "sin_anclaje", confianza: "baja", decision: null,
    cita: { fuente: "Diccionario de Datos", pantalla: "p1", pantalla_nombre: "Captura", campo: "rfc", texto: "x" },
    condicion_final: null, creada: "", decidida: null,
  } as unknown as Propuesta;
  pintar({ propuesta: p });
  expect(screen.getByText(/no menciona ningun campo/i)).toBeInTheDocument();
});

it("reserva el sitio del asistente sin construirlo todavia", () => {
  pintar();
  expect(screen.getByTestId("sitio-asistente")).toBeInTheDocument();
});

it("se puede cerrar", async () => {
  const onCerrar = vi.fn();
  pintar({ onCerrar });
  await userEvent.click(screen.getByRole("button", { name: /cerrar/i }));
  expect(onCerrar).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/TarjetaAbierta.test.tsx`
Expected: FAIL — los componentes no existen.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/features/huecos/Explicacion.tsx
import { BookOpen } from "lucide-react";

import { explicacionDeCodigo } from "./lenguaje";

/**
 * La capa 0 en pantalla: que es, por que salio y como se resuelve.
 *
 * No cuesta ninguna llamada al modelo porque la respuesta depende del codigo y
 * no del expediente. Un codigo sin explicacion no dibuja nada, en vez de
 * inventar una frase generica.
 *
 * `motivoSinAnclaje` es lo que el agente concluyo SIN preguntarle al modelo:
 * que la frase no depende de ningun campo. Decirlo evita que la persona se
 * quede mirando una tarjeta muda.
 */
export default function Explicacion({
  codigo,
  motivoSinAnclaje = null,
}: {
  codigo: string;
  motivoSinAnclaje?: string | null;
}) {
  const e = explicacionDeCodigo(codigo);
  if (!e && !motivoSinAnclaje) return null;
  return (
    <div className="flex flex-col gap-3 text-sm">
      {e ? (
        <>
          <p className="flex items-start gap-2">
            <BookOpen aria-hidden className="mt-0.5 size-4 shrink-0 text-secondary" />
            <span className="text-foreground">{e.queEs}</span>
          </p>
          <div className="flex flex-col gap-1 text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">Por qué salió: </span>
              {e.porQueSalio}
            </p>
            <p>
              <span className="font-medium text-foreground">Cómo se resuelve: </span>
              {e.comoSeResuelve}
            </p>
          </div>
        </>
      ) : null}
      {motivoSinAnclaje ? (
        <p className="rounded-lg border border-border bg-muted/40 p-3 text-muted-foreground">
          <span className="font-medium text-foreground">El agente lo revisó: </span>
          {motivoSinAnclaje}
        </p>
      ) : null}
    </div>
  );
}
```

```tsx
// frontend/src/features/huecos/TarjetaAbierta.tsx
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Hueco, Propuesta } from "@/lib/types";

import Explicacion from "./Explicacion";
import TarjetaHueco, { type RespuestaResuelto } from "./TarjetaHueco";
// `Hueco` y `Propuesta` vienen de @/lib/types, arriba.

/**
 * La inconsistencia abierta, a lo ancho del tablero y en dos mitades: a la
 * izquierda el control de resolucion de siempre —`TarjetaHueco` no se toca—, a
 * la derecha la explicacion de la capa 0 y el sitio reservado del asistente.
 *
 * El sitio del asistente se dibuja vacio a proposito (Fase 2c-2): tenerlo ya
 * maquetado evita rediseñar la pantalla cuando el chat exista.
 */
export default function TarjetaAbierta({
  hueco,
  sid,
  manifiesto,
  propuesta,
  ultimoActor = "",
  onResuelto,
  onCerrar,
}: {
  hueco: Hueco;
  sid: string;
  manifiesto: Record<string, unknown>;
  propuesta: Propuesta | null;
  /** Actor elegido en el MMD-03 anterior; se reenvia tal cual. */
  ultimoActor?: string;
  onResuelto: (nuevo: RespuestaResuelto, hueco: Hueco, valor?: string) => void;
  onCerrar: () => void;
}) {
  // Una propuesta `sin_anclaje` no es una propuesta: es la conclusion de que no
  // la puede haber. No se le pasa al control, que la interpretaria como regla.
  const esSinAnclaje = propuesta?.veredicto === "sin_anclaje";
  const paraControl = esSinAnclaje ? null : propuesta;

  return (
    <article className="flex flex-col gap-4 rounded-xl border border-primary/30 bg-card p-4 lg:flex-row">
      <div className="min-w-0 flex-1">
        <TarjetaHueco
          hueco={hueco}
          sid={sid}
          manifiesto={manifiesto}
          propuesta={paraControl}
          ultimoActor={ultimoActor}
          onResuelto={onResuelto}
        />
      </div>
      <aside className="flex w-full shrink-0 flex-col gap-4 border-t border-border pt-4 lg:w-80 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-semibold tracking-tight text-foreground">
            Qué significa esto
          </h4>
          <Button type="button" variant="ghost" size="sm" onClick={onCerrar} aria-label="Cerrar">
            <X aria-hidden className="size-4" />
          </Button>
        </div>
        <Explicacion
          codigo={hueco.codigo}
          motivoSinAnclaje={esSinAnclaje ? propuesta?.motivo_modelo ?? null : null}
        />
        {/* Fase 2c-2: aqui va el chat. Vacio hasta que haya cuota real. */}
        <div data-testid="sitio-asistente" />
      </aside>
    </article>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/TarjetaAbierta.test.tsx`
Expected: PASS, 5 pruebas. Si `TarjetaHueco` exige props que no se le pasan, **pasárselas** — no modificar `TarjetaHueco`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/Explicacion.tsx frontend/src/features/huecos/TarjetaAbierta.tsx frontend/src/features/huecos/TarjetaAbierta.test.tsx
git commit -m "feat(ux): tarjeta abierta con la explicacion al lado y el sitio del asistente"
```

---

## Task 9: `Tablero` — ensamblar las columnas

**Files:**
- Create: `frontend/src/features/huecos/Tablero.tsx`
- Test: `frontend/src/features/huecos/Tablero.test.tsx`

**Interfaces:**
- Consumes: `agruparPorCodigo` (Task 6), `ColumnaCodigo` y `claveDe` (Task 7), `TarjetaAbierta` (Task 8).
- Produces: `Tablero({ huecos, sid, manifiesto, resueltas, propuestas, ultimoActor, onResuelto })`, con `onResuelto: (nuevo: RespuestaResuelto, hueco: Hueco, valor?: string) => void` — la misma firma de tres argumentos que ya tiene `TarjetaHueco`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/huecos/Tablero.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  reconocer: vi.fn().mockResolvedValue({ huecos: [], reconocidos: [] }),
  resolver: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  decidirPropuesta: vi.fn().mockResolvedValue(undefined),
  camposDelManifiesto: () => [{ nombre: "estado", etiqueta: "Estado", catalogo: [] }],
}));

import Tablero from "./Tablero";
import type { Hueco, Propuesta } from "@/lib/types";

const h = (codigo: string, ubicacion: string): Hueco => ({
  nivel: "falta_dato", codigo, ubicacion,
  mensaje: "la condición de visibilidad de 'RFC' (rfc) no se pudo interpretar: «x»",
  propuesta: null,
});

function pintar(extra = {}) {
  return render(
    <Tablero
      huecos={[h("DIC-08", "p1::rfc"), h("DIC-08", "p2::curp"), h("MMD-04", "D1")]}
      sid={"a".repeat(16)}
      manifiesto={{}}
      resueltas={new Set<string>()}
      propuestas={new Map<string, Propuesta>()}
      onResuelto={vi.fn()}
      {...extra}
    />,
  );
}

it("dibuja una columna por codigo", () => {
  pintar();
  expect(screen.getByRole("heading", { name: /Visibilidad de un campo/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Decisión del flujo/i })).toBeInTheDocument();
});

it("de inicio no hay ninguna abierta", () => {
  pintar();
  expect(screen.queryByText(/Qué significa esto/i)).toBeNull();
});

it("abrir una tarjeta no borra el tablero", async () => {
  pintar();
  await userEvent.click(screen.getByRole("button", { name: /rfc/i }));
  expect(screen.getByText(/Qué significa esto/i)).toBeInTheDocument();
  // Las columnas siguen ahi.
  expect(screen.getByRole("heading", { name: /Decisión del flujo/i })).toBeInTheDocument();
});

it("abrir otra cierra la anterior: solo una abierta a la vez", async () => {
  pintar();
  await userEvent.click(screen.getByRole("button", { name: /rfc/i }));
  await userEvent.click(screen.getByRole("button", { name: /curp/i }));
  expect(screen.getAllByText(/Qué significa esto/i)).toHaveLength(1);
});

it("sin inconsistencias no dibuja tablero", () => {
  pintar({ huecos: [] });
  expect(screen.queryByRole("heading", { name: /Visibilidad/i })).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/Tablero.test.tsx`
Expected: FAIL — `Tablero` no existe.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/features/huecos/Tablero.tsx
import { useState } from "react";

import type { Hueco, Propuesta } from "@/lib/types";

import { agruparPorCodigo } from "./agrupar";
import ColumnaCodigo, { claveDe } from "./ColumnaCodigo";
import TarjetaAbierta from "./TarjetaAbierta";
import type { RespuestaResuelto } from "./TarjetaHueco";

/**
 * El tablero de inconsistencias: una columna por codigo, y la que se abre se
 * expande a lo ancho, debajo, sin tapar el resto.
 *
 * Sustituye a los modos `lista` y `foco`. Con una lista —y con un riel del 1 al
 * 19— la persona de Simplificacion no sabe cuantas de cada tipo le faltan, ni
 * cuales puede cerrar sola. Con columnas eso se ve sin leer.
 *
 * Una sola abierta a la vez: dos tarjetas anchas abiertas devuelven el problema
 * de la lista.
 */
export default function Tablero({
  huecos,
  sid,
  manifiesto,
  resueltas,
  propuestas,
  ultimoActor = "",
  onResuelto,
}: {
  huecos: Hueco[];
  sid: string;
  manifiesto: Record<string, unknown>;
  resueltas: Set<string>;
  propuestas: Map<string, Propuesta>;
  ultimoActor?: string;
  onResuelto: (nuevo: RespuestaResuelto, hueco: Hueco, valor?: string) => void;
}) {
  const [abierta, setAbierta] = useState<string | null>(null);
  const columnas = agruparPorCodigo(huecos, resueltas);
  if (columnas.length === 0) return null;

  const huecoAbierto =
    abierta === null
      ? null
      : huecos.find((h) => claveDe(h.codigo, h.ubicacion) === abierta) ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-3 overflow-x-auto pb-2">
        {columnas.map((c) => (
          <ColumnaCodigo
            key={c.codigo}
            columna={c}
            resueltas={resueltas}
            propuestas={propuestas}
            abiertaClave={abierta}
            onAbrir={(clave) => setAbierta((prev) => (prev === clave ? null : clave))}
          />
        ))}
      </div>
      {huecoAbierto ? (
        <TarjetaAbierta
          // `key`: al cambiar de inconsistencia el control debe remontarse
          // limpio, sin arrastrar lo que se escribio en la anterior.
          key={abierta}
          hueco={huecoAbierto}
          sid={sid}
          manifiesto={manifiesto}
          propuesta={propuestas.get(abierta!) ?? null}
          ultimoActor={ultimoActor}
          onResuelto={onResuelto}
          onCerrar={() => setAbierta(null)}
        />
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/Tablero.test.tsx`
Expected: PASS, 5 pruebas.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/huecos/Tablero.tsx frontend/src/features/huecos/Tablero.test.tsx
git commit -m "feat(ux): tablero de inconsistencias por codigo"
```

---

## Task 10: Montar el tablero y retirar los modos `lista` y `foco`

**Files:**
- Modify: `frontend/src/features/huecos/WizardHuecos.tsx`
- Delete: `frontend/src/features/huecos/ModoFoco.tsx`
- Modify: `frontend/src/features/huecos/WizardHuecos.test.tsx`
- Test: la suite completa.

**Interfaces:**
- Consumes: `Tablero` (Task 9).
- Produces: `WizardHuecos` sin `modo`, sin `HUECOS_PARA_FOCO` y sin el conmutador. `RielEntrega` y la sección de entrega quedan exactamente como están.

- [ ] **Step 1: Ver qué pruebas dependen de los modos que se van**

Run:
```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && \
  grep -rn "ModoFoco\|Uno a la vez\|modo\b\|useFoco\|HUECOS_PARA_FOCO" src/features/huecos/*.test.tsx src/features/huecos/*.tsx | grep -v node_modules
```
Anotar la lista: cada una de esas pruebas describe un comportamiento que **desaparece a propósito**. Se borran o se reescriben contra el tablero; ninguna se ablanda.

- [ ] **Step 2: Write the failing test**

Agregar al final de `frontend/src/features/huecos/WizardHuecos.test.tsx`:

```tsx
it("la revisión es un tablero por tipo, sin riel ni conmutador de modo", async () => {
  // Estado minimo con dos inconsistencias de codigos distintos.
  const estado = {
    sid: "a".repeat(16),
    manifiesto: {},
    huecos: [
      { nivel: "falta_dato", codigo: "DIC-08", ubicacion: "p1::rfc",
        mensaje: "la condición de visibilidad de 'RFC' (rfc) no se pudo interpretar: «x»",
        propuesta: null },
      { nivel: "falta_dato", codigo: "META-01", ubicacion: "metadatos",
        mensaje: "no se encontro el tiempo de respuesta declarado", propuesta: null },
    ],
    reconocidos: [],
  } as unknown as Parameters<typeof WizardHuecos>[0]["estado"];

  render(<WizardHuecos estado={estado} onEstado={vi.fn()} />);

  expect(screen.getByRole("heading", { name: /Visibilidad de un campo/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Tiempo de respuesta/i })).toBeInTheDocument();
  // Lo que se va:
  expect(screen.queryByRole("radiogroup", { name: /Cómo ver las inconsistencias/i })).toBeNull();
  expect(screen.queryByText(/Inconsistencia \d+ de \d+/)).toBeNull();
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npx vitest run src/features/huecos/WizardHuecos.test.tsx`
Expected: FAIL — hoy existe el conmutador y no hay encabezados de columna.

- [ ] **Step 4: Write minimal implementation**

En `WizardHuecos.tsx`:

1. Borrar la constante `HUECOS_PARA_FOCO` y su comentario.
2. Borrar el estado `const [modo, setModo] = useState<"lista" | "foco">(...)`.
3. Borrar los imports de `ModoFoco`, `useFoco`, `useListaConSalida` y `cn` **si dejan de usarse** (comprobarlo con oxlint en el paso 5).
4. Borrar el bloque `role="radiogroup"` completo (el conmutador Lista / Uno a la vez).
5. Sustituir todo el bloque `{modo === "foco" && foco.actual ? (...) : (...)}` —el render de las dos formas— por:

```tsx
        <Tablero
          huecos={huecosOriginales}
          sid={estado.sid}
          manifiesto={manifiesto}
          resueltas={cerradas}
          propuestas={propuestasPorClave}
          ultimoActor={ultimoActor}
          onResuelto={reportar}
        />
```

6. Agregar, junto a los demás `useMemo`/derivados del componente, el índice de propuestas por clave:

```tsx
  // `propuestas` YA es un Map<ubicacion, Propuesta> (linea 68). El tablero las
  // busca por `codigo|ubicacion`, que es la clave estable de una
  // inconsistencia, asi que hay que reindexarlo — no recorrerlo como arreglo.
  const propuestasPorClave = new Map(
    [...propuestas.values()].map((p) => [`DIC-08|${p.ubicacion}`, p] as const),
  );
```

**Dos cosas que NO se pueden cambiar sin romper el tablero:**

- `Tablero` recibe **`huecosOriginales`**, no `huecos`. `huecos` encoge conforme
  se resuelven, asi que las tarjetas desaparecerian en vez de marcarse
  «resuelta», y las cuentas por columna («1 de 2») saldrian mal. `cerradas` ya
  se calcula sobre `huecosOriginales` (linea 123); el tablero tiene que mirar la
  misma lista.
- `propuestas` es un `Map`, no un arreglo: recorrerlo con `.map(...)` directo
  falla en tiempo de ejecucion.

7. Agregar el import: `import Tablero from "./Tablero";`

Borrar el archivo del modo foco:

```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && \
  git rm frontend/src/features/huecos/ModoFoco.tsx && \
  git rm --ignore-unmatch frontend/src/features/huecos/ModoFoco.test.tsx
```

- [ ] **Step 5: Run the whole suite, the linter and the build**

Run:
```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && set -o pipefail && \
  npx vitest run && npx oxlint src/ && npm run build
```
Expected: todo en verde. Las pruebas que se apoyaban en `lista`/`foco` se borran o se reescriben contra el tablero, **explicando el cambio en el mensaje del commit**. Si `useFoco.ts` o `useListaConSalida.ts` quedan sin usar, borrarlos también con sus pruebas.

- [ ] **Step 6: Run the Python suite (no debe haberse tocado)**

Run: `cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && set -o pipefail && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A frontend/src
git commit -m "feat(ux): la revision es un tablero por tipo; se van los modos lista y foco"
```

---

## Task 11: Verificación de punta a punta con el expediente real

**Files:** ninguno. Es una comprobación, y su resultado se reporta.

- [ ] **Step 1: Reconstruir el frontend en el repo principal y comprobar que el servidor lo sirve**

Run:
```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador/frontend && npm run build && \
  cd .. && curl -s --max-time 8 http://192.168.0.143:8000/ | grep -o 'index-[A-Za-z0-9_-]*\.js'
```
Expected: el hash servido coincide con el recién construido. Si la IP cambió, obtenerla con `ipconfig getifaddr en0`.

- [ ] **Step 2: Subir el expediente y comprobar las tres capas**

Subir `Constancia de No Infracción Vehicular Ambiental` por la interfaz y verificar:
1. La revisión es un tablero, con columnas nombradas como la barra lateral.
2. La inconsistencia de `Campos con Error` muestra la explicación de DIC-08 **y** el motivo del agente sin haber llamado al modelo.
3. Con la cuota agotada, el tablero funciona completo y no hay pantalla vacía ni traza.

- [ ] **Step 3: Comprobar en la bitácora que se llamó menos**

Run:
```bash
cd /Users/danielhernandezrubio/Desktop/Projects/gpm-compilador && .venv/bin/python - <<'PY'
from pathlib import Path
from gpmc.agentes.bitacora import leer
raiz = Path.home() / "Library/Application Support/gpmc"
e = leer(raiz)[-10:]
for x in e:
    print(x["timestamp"][:19], x["modelo"], x.get("tokens_entrada"), x.get("alertas"))
PY
```
Expected: las entradas nuevas traen `tokens_entrada` claramente menores que las de la Fase 2, y los aciertos de caché aparecen con `modelo: "(cache)"` y `alertas: ["cache"]`.

- [ ] **Step 4: Reportar**

Decir qué se verificó y qué no. **Si algo de la capa 0 no se pudo comprobar porque la cuota impidió generar propuestas, decirlo explícitamente** en vez de darlo por bueno.

---

## Cierre

- [ ] **Usar `superpowers:finishing-a-development-branch`** para fusionar, limpiar el worktree y decidir el destino de la rama.
- [ ] **Antes de borrar ningún worktree**, comprobar desde dónde corre el servidor: `lsof -p $(lsof -ti tcp:8000) | awk '$4=="cwd"'`. En este proyecto ya se borraron worktrees con servidores dentro dos veces.
- [ ] **Actualizar el vault**: entrada en `Bitacora/` y fila en `Bitacora/README.md`, con el estilo narrativo de las anteriores.
