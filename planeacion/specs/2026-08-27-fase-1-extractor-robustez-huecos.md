# Fase 1 — Robustez del extractor y clasificación de huecos

- **Fecha:** 2026-08-27
- **Estado:** aprobado, pendiente de plan de implementación
- **Alcance:** `src/gpmc/extractores/`, `src/gpmc/nucleo/`, `src/gpmc/cli.py`,
  `src/gpmc/web/` (solo lectura), pruebas, limpieza de repo.
- **Fuera de alcance:** formulario editable en el navegador (Fase 2), login,
  hospedaje, persistencia de sesión (Fase 3), autoría por formulario (Fase 4),
  `SINTAXIS_ESTRICTA`, cualquier cambio a `nucleo/formato.py`,
  `compilador/` o `validador/`.

## 1. Contexto y problema

Correr `gpmc extraer` sobre un expediente real (trámite "Alta de Avisos de
Testamento") produce 9 pantallas, 47 campos, 10 tareas y **49 "huecos"**. Al
revisarlos:

| # | Hueco | Qué es en realidad |
|---|---|---|
| 1 | `no se encontro 'Propuesta TO-BE.md': sin el no hay flujo` | **Bug del buscador.** El archivo se llama `3.-Propuesta TO-BE 1.md`. El buscador compara la palabra clave *incluyendo* `.md`, así que cualquier texto entre la palabra y la extensión (` 1.md`, ` final.md`) rompe la coincidencia. El insumo más importante se pierde en silencio y el flujo sale vacío. |
| 2 | `no se encontro el tiempo de respuesta declarado` | Gap real: falta un dato. |
| 3–49 | `el campo 'X' no declara nombre tecnico @@ ...; se propuso 'x'` (×47) | Ruido: el extractor **ya propuso** un nombre técnico razonable y solo pide confirmación. |

Para el equipo de Simplificación esto se lee como "49 errores, la herramienta
está rota". En realidad son ~2 datos faltantes + 47 confirmaciones triviales, y
un bug que tira el flujo.

El diccionario (`5.-Diccionario de Datos.md`) se salvó por casualidad: no tiene
sufijo entre la palabra clave y `.md`.

## 2. Objetivo

Que la salida del extractor distinga **señal de ruido** y que ningún insumo se
pierda por variaciones de nombre. Métrica: el trámite de Testamento pasa de
"49 huecos" a "1 bloqueante, ~4 faltan datos, ~44 por confirmar", y el TO-BE se
encuentra pese al sufijo ` 1`.

## 3. Diseño

### 3.1 Buscador de archivos — `_leer` en `extractores/expediente.py`

**Normalización** de nombre antes de comparar (función nueva `_normalizar`):

1. `unicodedata.normalize("NFKD", ...)` y descartar los diacríticos (`Mn`).
2. Minúsculas.
3. Colapsar `[\s._\-]+` a un solo espacio; `strip()`.
4. Quitar prefijo de orden al inicio: `^\d+\s*[.)\-]+\s*` (cubre `1.-`, `3) `, `2. `).
5. Quitar sufijos de versión/copia al final, repetidamente:
   ` v?\d+$`, ` final$`, ` copia$`, ` \(\d+\)$`.

La comparación se hace contra el **stem** (`Path.stem`, sin `.md`), no contra
`name`. Esa es la corrección de la causa raíz.

**Solo archivos `.md`.** Los `.pdf` y demás ni se consideran como candidatos.

Cada insumo tiene un conjunto de palabras clave ya normalizadas:

- `as_is`: `{"analisis as is", "as is"}`
- `to_be`: `{"propuesta to be", "to be"}`
- `dicc`: `{"diccionario de datos", "diccionario"}`

Un archivo es candidato si su stem normalizado **contiene** alguna palabra clave
del insumo.

**Resolución:**

- **0 candidatos:**
  - `dicc` ausente → como hoy: hueco `INS-03` bloqueante y `return r` (sin
    diccionario no hay pantallas).
  - `to_be` ausente → hueco `INS-01` **bloqueante**; se continúa con flujo
    lineal (comportamiento actual).
  - `as_is` ausente → sin hueco (es opcional; comportamiento actual).
- **1 candidato:** se usa.
- **2+ candidatos:** no se adivina. Hueco `INS-02` **falta_dato**
  (`"N candidatos para <insumo>: a.md, b.md — confirma cuál"`) y ese insumo se
  trata como no encontrado (cae en la rama de "0 candidatos" para efectos de
  bloqueo, pero el hueco reportado es `INS-02`, no `INS-01`).

`SinPermiso` (bloqueo de TCC de macOS al leer `~/Documents`, `~/Desktop`,
`~/Downloads`) se conserva sin cambios.

`_leer` deja de devolver solo `str`: devuelve `Tuple[str, List[Hueco]]` (texto y
los huecos de resolución), o se refactoriza a una función `_resolver_insumo` que
`extraer_expediente` orquesta. El detalle exacto lo fija el plan; el contrato es
que los huecos `INS-01`/`INS-02` nacen aquí.

### 3.2 Tipo `Hueco` — nuevo módulo `nucleo/huecos.py`

```python
from dataclasses import dataclass
from typing import Optional

NIVELES = ("bloqueante", "falta_dato", "por_confirmar")

@dataclass
class Hueco:
    nivel: str            # uno de NIVELES
    codigo: str           # estable: INS-01, DIC-01, META-01, FLU-01, ...
    ubicacion: str        # "p1", "flujo", "metadatos", "" (vacío = general)
    mensaje: str          # texto para una persona
    propuesta: Optional[str] = None   # valor sugerido por el extractor (DIC-01)

    def __str__(self) -> str:
        pre = f"[{self.codigo}] " if self.codigo else ""
        loc = f"{self.ubicacion}: " if self.ubicacion else ""
        return f"{pre}{loc}{self.mensaje}"
```

`nucleo/huecos.py` no importa nada de `gpmc` (respeta la dependencia en un solo
sentido). Es hermano conceptual de `validador.reglas.Hallazgo` pero distinto:
`Hallazgo` describe defectos estructurales de un `.gpm` ya compilado; `Hueco`
describe lo que no se pudo derivar de los insumos.

### 3.3 Los tres sub-extractores devuelven `List[Hueco]`

`extractores/diccionario.py`, `extractores/metadatos.py` y
`extractores/mermaid.py` cambian el campo `huecos: list[str]` de su `Resultado`
por `huecos: list[Hueco]`. `expediente.py` deja de prefijar strings
(`f"[diccionario] {h}"`) y solo concatena listas de `Hueco`.

Tabla de códigos y nivel:

| Código | Origen | Nivel | Nota |
|---|---|---|---|
| `INS-01` | expediente | bloqueante | TO-BE no encontrado |
| `INS-02` | expediente | falta_dato | insumo con varios candidatos |
| `INS-03` | expediente | bloqueante | Diccionario de Datos no encontrado |
| `DIC-00` | expediente | bloqueante | sin tabla de campos legible / ninguna pantalla |
| `DIC-01` | diccionario | **por_confirmar** | nombre técnico `@@` propuesto; `propuesta` = el nombre sugerido, `ubicacion` = pantalla |
| `DIC-04` | diccionario | falta_dato | no se encontró ninguna cabecera `### Pantalla N`; se agrupó todo en una pantalla |
| `META-01` | metadatos | falta_dato | tiempo de respuesta no declarado |
| `META-02` | metadatos | falta_dato | dependencia no encontrada en el frontmatter |
| `META-03` | metadatos | por_confirmar | costo no declarado; se asume sin costo (el extractor ya asume un valor) |
| `META-04` | metadatos | falta_dato | nombre del trámite no determinado |
| `META-05` | metadatos | por_confirmar | homoclave no encontrada (normal en trámites nuevos) |
| `META-06` | metadatos | por_confirmar | "A quién va dirigido" no encontrado; type_of_person queda en 'ambas' |
| `FLU-01` | expediente | falta_dato | el TO-BE tiene N compuertas que el manifiesto lineal no ramifica |
| `FLU-02` | expediente | falta_dato | nº de tareas del diagrama ≠ nº de pantallas del diccionario |
| `MMD-01` | mermaid | falta_dato | la Propuesta TO-BE no trae bloque ```mermaid``` |
| `MMD-02` | mermaid | falta_dato | arista referencia un nodo no declarado / diagrama mal formado |

El plan mapea cada `r.huecos.append(...)` existente a uno de estos códigos. Si
aparece un caso no listado, su nivel por defecto es `falta_dato` y se registra
en el plan (no se inventa un nivel más permisivo en silencio).

**El nombre técnico propuesto se sigue escribiendo en el YAML** (comportamiento
actual de `diccionario.py`): el manifiesto compila sin intervención. `DIC-01` es
puramente informativo — le dice al analista "revisa que `@@curp` sea correcto".

### 3.4 Salida de `gpmc extraer`

Agrupada por nivel, con conteo y un carácter guía por nivel:

```
Generado: tramite.yaml
  9 pantallas, 47 campos, 2 actores, 10 tareas

■ 1 BLOQUEANTE — resolver antes de compilar
  [INS-01] no se encontró la Propuesta TO-BE: el flujo sale lineal

▲ 4 FALTAN DATOS — un humano debe escribirlos
  [META-01] tiempo de respuesta no declarado
  [FLU-01] flujo: el TO-BE tiene 3 compuertas que este manifiesto no ramifica
  ...

· 44 POR CONFIRMAR — el extractor propuso un valor, revísalos de un vistazo
  [DIC-01] p1: 'CURP' → @@curp
  … y 41 más   (usa --huecos para verlos todos)
```

- Orden de bloques: bloqueante, falta_dato, por_confirmar.
- El bloque `por_confirmar` se trunca a 3 líneas por defecto.
- Nueva bandera `--huecos` (o `-H`): imprime todos los huecos sin truncar.
- **Código de salida: 0** siempre que se haya escrito el YAML. Los huecos nunca
  han fijado el código de salida y eso no cambia. Solo se devuelve `1` si no se
  pudo producir manifiesto alguno (comportamiento actual).
- Sin `.venv`/TTY no cambia nada: es texto plano; los caracteres guía son
  `U+25A0`, `U+25B2`, `U+00B7`, todos ASCII-safe en UTF-8.

### 3.5 Página `/revisar` — solo lectura

`web/plantillas.py :: revision(m, huecos, problemas, estimacion, sid)` recibe
`huecos: list[Hueco]`. Se renderiza en **3 secciones plegables**
(`<details>`), cada una con su conteo y color:

- bloqueante → rojo (`--alerta`)
- falta_dato → ámbar
- por_confirmar → gris

Cada ítem muestra `codigo`, `ubicacion`, `mensaje` y, si hay, `→ propuesta`.
**Sin campos editables.** El formulario de corrección es la Fase 2.

`web/app.py`:

- La ruta `POST /extraer` guarda `huecos.json` (lista de dicts de `Hueco`) en
  vez de `huecos.txt`.
- La ruta `GET /revisar/{sid}` carga `huecos.json` y reconstruye `list[Hueco]`.
- Se elimina el `.splitlines()` sobre `huecos.txt`.
- El resto del flujo (`/simulador`, `/aprobacion`, `/descargar`) no cambia.

### 3.6 Limpieza de repositorio (incluida en esta fase)

- Borrar del árbol: `patch.py`, `patch_dic.py`, `test_acceso.yaml`,
  `test_tol.yaml`, `scratch/`.
- Añadir `scratch/` a `.gitignore`.
- Revertir el cambio sin commitear de `extractores/expediente.py` (agrega
  variantes `AS_IS.md` / `TO_BE.md` / `Diccionario_Datos.md`): queda subsumido
  por §3.1, que cubre esos casos vía normalización.

## 4. Plan de pruebas (TDD: primero la prueba que falla)

### 4.1 Buscador — `tests/test_extractor_expediente.py`

Con `tmp_path` y archivos markdown mínimos que ya compilen:

- `3.-Propuesta TO-BE 1.md` → se encuentra como TO-BE (no aparece `INS-01`).
- `Propuesta TO-BE final.md`, `propuesta_to_be_v2.md`, `TO BE.md`,
  `Análisis AS-IS.md` con acento → se encuentran.
- Carpeta con `Propuesta TO-BE.md` **y** `TO-BE borrador.md` → hueco `INS-02`,
  nivel `falta_dato`, y el flujo se comporta como si faltara el TO-BE.
- Carpeta sin ningún TO-BE → hueco `INS-01`, nivel `bloqueante`, manifiesto
  igual se produce (flujo lineal).
- `_normalizar` como unidad: casos de prefijo `1.-`, sufijo ` 1`, ` (2)`,
  acentos, mayúsculas.

### 4.2 Clasificación — `tests/test_huecos.py` (nuevo) o extensión

- Todos los elementos de `r.huecos` son `Hueco` con `nivel in NIVELES`.
- Sobre el diccionario de un expediente real (vía `GPMC_WIKI`, se salta si no
  está): todo `DIC-01` tiene `nivel == "por_confirmar"` y `propuesta` no vacía;
  su conteo iguala el nº de campos sin `@@` explícito.
- Sin TO-BE: existe exactamente un `INS-01` bloqueante.
- `str(hueco)` produce el formato `[CODIGO] ubicacion: mensaje`.

### 4.3 Regresión

- `tests/test_extractor_diccionario.py`, `test_extractor_mermaid.py`,
  `test_web.py` adaptados al tipo `Hueco`.
- La prueba "siempre reporta huecos sobre material real" sigue pasando con el
  tipo nuevo.
- **Suite completa verde**, incluida la prueba de ida y vuelta byte-exacta de
  `nucleo/formato.py` (esta fase no la toca): `.venv/bin/pytest -v`.

## 5. Riesgos

- **Normalización demasiado agresiva** podría emparejar un archivo equivocado.
  Mitigación: solo `.md`, y el caso 2+ candidatos nunca adivina (`INS-02`).
- **Cambio de tipo `list[str]` → `list[Hueco]`** toca varios módulos y sus
  pruebas. Mitigación: `Hueco.__str__` mantiene compatibilidad en los puntos
  que hacen `"\n".join(...)`; el plan actualiza call sites uno por uno.
- **`huecos.txt` → `huecos.json`**: sesiones viejas en disco quedarían sin
  `huecos.json`. Aceptable — las sesiones del asistente son efímeras y esta
  fase no promete persistencia.

## 6. Criterios de aceptación

1. `gpmc extraer <expediente de Testamento> -o t.yaml` encuentra el TO-BE pese
   al sufijo ` 1` y reporta `INS-01` **solo** si el TO-BE de verdad no está.
2. La salida muestra 3 bloques con conteos; `por_confirmar` truncado salvo con
   `--huecos`.
3. `r.huecos` es `list[Hueco]`; cada uno con nivel válido; los `DIC-01` llevan
   `propuesta`.
4. `/revisar/{sid}` muestra los 3 bloques plegables con color, sin edición.
5. `patch.py`, `patch_dic.py`, `test_acceso.yaml`, `test_tol.yaml`, `scratch/`
   fuera del árbol; `scratch/` en `.gitignore`.
6. `.venv/bin/pytest -v` en verde.
