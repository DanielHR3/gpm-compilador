# Fase 2b — Corrector de redacción de etiquetas (diseño)

**Fecha:** 2026-09-17
**Estado:** propuesto, pendiente de revisión
**Antecede a:** `docs/superpowers/plans/2026-09-17-fase2b-corrector-redaccion.md` (por escribir)
**Continúa:** `2026-09-17-agentes-fase2-dic08-design.md` (Fase 2, generador DIC-08)

---

## 1. El problema, y lo que la medición dijo de él

La idea original era «un corrector de lenguaje claro»: ortografía, y además
detectar nombres que un ciudadano no entendería. Antes de diseñar nada se midió
el corpus real —6 expedientes, 270 etiquetas (200 distintas), 448 valores de
catálogo, 42 nombres de pantalla—. La medición cambió el alcance tres veces, y
queda aquí porque es el sustento del diseño.

**Hallazgo 1 — los errores del ejemplo no existen.** Los casos que ilustran la
lámina 6 de la presentación (`Norario`, `Cp sol`, `cpsol`) no aparecen en ningún
expediente: ni en etiquetas, ni en catálogos, ni en nombres de pantalla. La
lámina debe cambiar de ejemplo (ver §12).

**Hallazgo 2 — el prompt ingenuo empeora las etiquetas.** Una primera instrucción
de «solo ortografía y mayúsculas» produjo 5 sugerencias sobre 200, y **3 eran
incorrectas**: le imponía al español la capitalización de títulos del inglés
(`Fecha de expedición de testamento` → `…de Expedición de Testamento`). Peor: no
detectó la única etiqueta verdaderamente mala del corpus.

**Hallazgo 3 — sí hay material, pero es uno solo y es grave.** En Reposición de
Placas existe esta etiqueta, con cinco errores reales:

> `Documento: Documentales Probatorios del Motivo ( colocar como nota : hoja del
> ajustador, facturas de las refacciones, hoja de transito) fotos del vehiculo en
> reparacion) si juicio o litigio ( cargar  caroeta de investigacion u hoja de
> liberaciond el corralon) ( si es juicio uscesorio intestamentario ......hoja del juicio)`

`caroeta`, `liberaciond el`, `uscesorio`, `vehiculo`, `transito`.

**Hallazgo 4 — el prompt detallado sí funciona.** Reescrito para nombrar la regla
del español explícitamente, con lista de intocables y ejemplos negativos tomados
del corpus, sobre las mismas 200 etiquetas:

| | prompt ingenuo | prompt detallado |
|---|---|---|
| Sugerencias | 5 | **2** |
| Falsos positivos | 3 | **0** |
| Detecta la etiqueta de 5 errores | no | **sí** |
| Tokens (200 etiquetas, 1 llamada) | — | 5026 → 502 |

Medido con `gemini-flash-latest` el 2026-09-17.

**Hallazgo 5 — los catálogos son territorio minado.** De los 337 valores
distintos, una parte grande son nombres propios: los municipios de Hidalgo
(Acaxochitlán, Acatlán, Actopan, Ixmiquilpan…), leyes con artículo y fracción,
folios, placas y montos. Es exactamente el material que un corrector destroza.
**Quedan fuera del alcance** (§3).

**Hallazgo 6 — un defecto real, que no es de ortografía.** La celda
`$226.00 (fijo, Ley Estatal de Derechos Art. 40 Fracción V)` se parte por la coma
y produce **dos** opciones de catálogo. Igual con
`PEA-4521 *(ilustrativo, referencia de Pantalla 1)*`. Partimos catálogos por coma
sin respetar paréntesis, y el `.gpm` sale con un catálogo inventado, en silencio.
**No pertenece a esta fase** —no lo arregla un modelo, lo arregla el extractor—
pero queda registrado aquí porque lo destapó esta medición. Ver §12.

---

## 2. La decisión de arquitectura: esto **no** es un hueco

Es la pregunta que bloqueó el diseño desde el principio, y merece respuesta
explícita porque determina todo lo demás.

Un **hueco** es información que falta y que el compilador necesita: se emite
determinísticamente en un extractor, viaja en `huecos.json`, puede bloquear la
entrega del `.gpm`, y se tacha cuando alguien lo resuelve. Un error de ortografía
no es nada de eso: **el manifiesto está completo y el `.gpm` compila bien**. Solo
está mal escrito.

Se consideraron tres caminos:

**(A) Emitir un hueco `DIC-09` que la IA rellena.** Rechazado. Un hueco lo emite
un extractor, y `nucleo/` no puede importar `agentes/` (invariante del repo,
`test_el_nucleo_no_importa_agentes`). Para emitirlo determinísticamente haría
falta un diccionario ortográfico en el núcleo —una dependencia nueva— y si ese
diccionario existiera, el modelo sobraría.

**(B) Una propuesta sin hueco. → ELEGIDA.** `propuestas.json` gana una segunda
lista, `redaccion`, hermana de las de DIC-08. Se genera en la misma tarea de
fondo, pasa por un filtro determinista propio, y la pantalla de revisión la
muestra en su sección. Aceptar dispara una resolución nueva, `tipo: "orto"`, que
escribe `campo.etiqueta`. No toca `huecos.json` porque no hay hueco que tachar.

**(C) Un comando de CLI, aplicado a mano.** Rechazado: la Dirección pidió
explícitamente que apareciera en la pantalla de revisión.

El camino (B) respeta el invariante que ya sostiene la Fase 2 y que no se negocia:

> **El modelo nunca escribe.** Propone; un filtro determinista lo tamiza; una
> persona confirma; el `POST /resolver` escribe. Entre el modelo y el manifiesto
> siempre hay un filtro y un humano.

---

## 3. Alcance

**Dentro:**
- `Campo.etiqueta` de todas las pantallas del expediente. Es `str` de
  presentación (`manifiesto.py:71`); cambiarla no afecta a nada más: el
  emparejamiento usa `Campo.nombre`, y los catálogos usan `OpcionCatalogo.etiqueta`.
- Dos clases de error, y ninguna otra: **ortografía** (acentos, letras
  cambiadas, palabras mal partidas) y **mayúsculas** según la regla del español.

**Fuera, con motivo:**
- **Valores de catálogo** — nombres propios y cifras; riesgo medido (§1, hallazgo 5).
- **Nombres de pantalla** — citizen-facing, pero **no se midieron**. Entrarían
  tras medirlos, no antes.
- **`Campo.nombre`** — identificador técnico (`@@campo`); cambiarlo rompe
  condiciones, flujo y el `.gpm`.
- **«Lenguaje claro»** (proponer un nombre que el ciudadano entienda mejor) —
  es reescritura, no corrección; otro problema y otro diseño.
- **Puntuación, espacios y paréntesis** — incluido el paréntesis descuadrado de
  la etiqueta larga. El modelo tiene prohibido tocarlos; son defectos de forma
  que corresponden al extractor o a la persona.

---

## 4. Componentes

```
src/gpmc/agentes/
  prompt_orto.py      NUEVO  instrucción versionada + esquema de salida
  orto.py             NUEVO  proponer_redaccion(): arma el lote, llama, arma Propuestas
  verificar_orto.py   NUEVO  filtro determinista (el candado)
  bitacora.py         reusa  mismo bitacora-ia.jsonl, distinta VERSION_PROMPT
  proveedor.py        reusa  sin cambios
src/gpmc/web/
  api.py              MODIF  genera y expone redaccion; ResolucionOrto en /resolver
  sesiones.py         reusa  escribir_propuestas ya guarda el dict completo
frontend/src/features/
  redaccion/TarjetaRedaccion.tsx   NUEVO  la tarjeta de sugerencia
  ...pantalla de revisión          MODIF  una sección nueva
```

Cada pieza tiene un solo trabajo: `prompt_orto.py` solo texto e esquema,
`verificar_orto.py` es una función pura sin red ni estado, `orto.py` orquesta.
`verificar_orto.py` se puede probar entero sin proveedor.

---

## 5. Flujo

1. Se sube el expediente. `POST /expedientes` responde igual que hoy y encola la
   tarea de fondo (`api.py:399`).
2. La tarea de fondo genera **primero** las propuestas DIC-08 (como hoy) y
   **después** las de redacción. Una sola llamada al modelo para todas las
   etiquetas del expediente (~45; medido: 200 caben en 5026 tokens). Si un
   expediente excediera el presupuesto de tokens se reusa `partir_lote` de
   `contexto.py`, igual que DIC-08; con el corpus actual no llega a ocurrir.
3. Cada sugerencia pasa por `verificar_orto`. Las que no pasan se guardan con su
   veredicto —igual que en DIC-08— para poder auditarlas, pero no se muestran.
4. `GET /expedientes/{sid}/propuestas` devuelve también `redaccion`, filtrada a
   `veredicto == "aceptable"` y `decision is None`.
5. La persona ve la etiqueta actual, la corregida, y qué palabras cambian.
   Acepta, corrige a mano, o descarta.
6. Aceptar → `POST …/decision` (registra) **y** `POST …/resolver` con
   `{tipo:"orto", ubicacion:"p1::campo", valor:"…"}` → escribe `campo.etiqueta`
   y guarda `manifiesto.yaml`. Mismo patrón de dos pasos que DIC-08.

Si no hay proveedor, o falla, o la cuota se agota: `redaccion: []` y la pantalla
no muestra la sección. **Nunca bloquea la compilación** — no hay hueco, no hay
puerta 409, el `.gpm` sale igual.

---

## 6. El prompt (`orto-v2`)

La versión se llama `orto-v2` porque `orto-v1` fue la instrucción ingenua que la
medición descartó; conservar la numeración deja rastro de por qué el texto es
como es. Cambiar el texto obliga a subir la versión: la bitácora la registra.

Las tres piezas que lo hacen funcionar, y que **no deben quitarse al editarlo**:

1. **La regla del español, dicha también al revés.** No basta pedir «corrige
   mayúsculas». Hay que afirmar que `Fecha de expedición de testamento` *ya está
   bien*, y que convertirlo a `…de Expedición de Testamento` *es el error, porque
   eso es inglés*. Sin esta frase reaparecen los 3 falsos positivos.
2. **La lista de intocables**, nombrada: siglas (CURP, RFC, UMA, CISE, ARRA),
   municipios de Hidalgo por nombre, leyes con artículo y fracción, cifras,
   folios y placas; y la prohibición de reescribir, reordenar, acortar o tocar
   puntuación.
3. **Permiso explícito de callar:** «si dudas, no lo incluyas: callar vale mucho
   más que corregir algo que ya estaba correcto», más el aviso de que se espera
   que la gran mayoría no tenga error.

Conserva el envoltorio anti-inyección de la Fase 2: los datos viajan entre
`<<DATOS>>` y `<</DATOS>>` y la instrucción dice que nada de ahí dentro son
órdenes.

Salida: `{correcciones: [{indice, corregido, cambios:[{de, a, clase}], confianza}]}`.
Los índices evitan reenviar el texto y permiten emparejar sin ambigüedad.

---

## 7. El filtro determinista (`verificar_orto.py`)

El prompt es una petición; el filtro es el candado. En la medición del 2026-09-17
no tuvo que rechazar nada —el prompt solo ya se comportó— y aun así se construye:
lo que sostiene la congruencia cuando el modelo cambie de versión es el candado,
no la cortesía del prompt.

### 7.1 La regla central: el corregido se reconstruye

El filtro no compara textos a ojo. Exige que **el corregido sea reproducible
aplicando los cambios declarados**:

```
aplicar(original, cambios) == corregido
```

donde `aplicar` sustituye, para cada `{de, a}` en orden, la primera aparición de
`de` todavía no consumida. Si el modelo declaró sus cambios con honestidad, la
reconstrucción da exacto. Cualquier edición no declarada —una palabra suelta, una
reescritura, un recorte— rompe la igualdad y la sugerencia se rechaza.

Esta regla es la que permite aceptar correcciones que **sí** cambian el número de
palabras (`liberaciond el` → `liberación del`, o al revés) sin abrir la puerta a
que el modelo reescriba: lo que se vigila no es la forma del resultado, sino que
todo cambio esté declarado y sea verificable uno por uno.

### 7.2 Veredictos

`aceptable`, o el motivo del rechazo:

| Veredicto | Se rechaza cuando |
|---|---|
| `no_reconstruye` | `aplicar(original, cambios) != corregido` (§7.1) — cubre reescrituras y cambios no declarados |
| `title_case` | `de` y `a` son la misma palabra salvo la inicial, `a` la sube, y `de` no es la primera palabra del texto |
| `toca_sigla` | `de` está en mayúsculas y mide ≤ 6 caracteres |
| `etiqueta_desconocida` | el índice no corresponde a ninguna etiqueta enviada |
| `cambio_vacio` | `de == a`, o el corregido es igual al original, o la lista de cambios viene vacía |
| `esquema_invalido` | la respuesta no cumple el esquema |
| `sin_respuesta` | el proveedor no devolvió nada |

Las comprobaciones corren **en el orden de la tabla** y la primera que falla da
el veredicto. Una sugerencia puede violar más de una regla —un recorte disfrazado
de mayúscula infringe `title_case` y `no_reconstruye` a la vez— y el veredicto
registrado es el primero, no el más grave. Para la persona da igual, porque en
ambos casos no se le muestra; para auditar la bitácora, importa saberlo.

La regla se validó en seco el 2026-09-17 contra diez casos —los tres falsos
positivos medidos, las tildes y la palabra mal partida de la etiqueta larga, una
sigla, una reescritura encubierta y un recorte—: rechaza los seis que debe
rechazar y acepta los cuatro que debe aceptar.

Los tres falsos positivos de la medición se congelan como **fixtures de
regresión**: `Fecha de expedición de testamento`, `Motor de pago en línea` y
`Autoriza y Firma (digital)` deben ser rechazados por el filtro aunque un modelo
futuro vuelva a proponerlos.

Nota conocida: `toca_sigla` también rechazaría la corrección legítima de una
palabra de ≤ 6 letras escrita toda en mayúsculas. Es un falso negativo aceptado a
cambio de proteger CURP/RFC/UMA; si aparece un caso real, se afina con una lista
de siglas conocidas en vez de la heurística.

---

## 8. Contratos

`GET /expedientes/{sid}/propuestas` — se **agrega** un campo; lo existente no cambia:

```jsonc
{
  "estado": "listo",
  "motivo": null,
  "propuestas": [ /* DIC-08, como hoy */ ],
  "redaccion": [
    {
      "id": "orto-1",
      "ubicacion": "p1::documento_probatorio",
      "actual": "…hoja de transito) fotos del vehiculo…",
      "corregido": "…hoja de tránsito) fotos del vehículo…",
      "cambios": [{"de": "transito", "a": "tránsito", "clase": "ortografia"}],
      "confianza": "alta",
      "veredicto": "aceptable",
      "decision": null
    }
  ]
}
```

`POST /expedientes/{sid}/resolver` — una resolución nueva:

```python
class ResolucionOrto(BaseModel):
    tipo: Literal["orto"]
    ubicacion: str   # "pantalla_id::campo_nombre"
    valor: str       # la etiqueta final (corregida o editada a mano)
```

Valida que la pantalla y el campo existan (422 si no, como `dic08`), fija
`campo.etiqueta = valor`, guarda el manifiesto y **no** toca `huecos.json`.

---

## 9. Interfaz

Sección propia en la pantalla de revisión, bajo las inconsistencias, titulada
**«Sugerencias de redacción»**, con una línea que diga qué son: *cambios de
ortografía y mayúsculas propuestos por IA; no afectan la compilación*.

Cada tarjeta muestra la etiqueta actual y la corregida con **las palabras
cambiadas resaltadas** —no un diff de caracteres: la persona debe ver de un
vistazo que solo cambió `transito` por `tránsito`—, y tres acciones con el mismo
lenguaje visual que ya tienen las de DIC-08: **Aceptar**, **Corregir** (abre el
texto editable), **Descartar**.

Si no hay sugerencias, la sección no se dibuja. Nada de estados vacíos que
inviten a buscar problemas donde no los hay.

---

## 10. Bitácora y Licencia AI

Se reusa `bitacora-ia.jsonl` del almacén global y el registro `Interaccion` de la
Fase 2, sin cambios de forma: proveedor, modelo resuelto, versión de prompt
(`orto-v2`), hash de la instrucción, tokens de entrada y salida, duración,
veredicto y decisión. Es el mismo requisito de la Licencia AI de Planeación —
trazabilidad de cada interacción— y la misma respuesta.

Solo viajan al proveedor las **etiquetas**. No van nombres de campo, ni valores
de catálogo, ni metadatos del trámite, ni nada de los PDFs del expediente.

---

## 11. Pruebas

- **`verificar_orto` sin proveedor**, una prueba por veredicto, más los tres
  fixtures de regresión de §7. Es el grueso, y no necesita red.
- **`proponer_redaccion` con `ProveedorFalso`**: lote bien armado, respuesta
  bien mapeada, veredictos aplicados, bitácora escrita.
- **Fallo del proveedor** (`ErrorDeRed`, cuota agotada): `redaccion: []`, sin
  traza, la compilación sigue. Se aprendió en la Fase 2 que `medir-ia` escupía un
  traceback aquí; no repetirlo.
- **`POST /resolver` con `tipo:"orto"`**: cambia la etiqueta, guarda el
  manifiesto, deja `huecos.json` intacto; 422 con campo inexistente.
- **El invariante**: `test_el_nucleo_no_importa_agentes` debe seguir pasando.
- **Frontend**: la sección no aparece con `redaccion: []`; Aceptar dispara las
  dos peticiones; Corregir manda el texto editado.
- **Pendiente de la medición**, a correr cuando reinicie la cuota diaria: que en
  la etiqueta larga el corregido conserve el número de palabras y cuántos de los
  5 errores arregla. El arnés ya lo mide. **No se da por buena esa parte hasta
  verla**, y la regla de reconstrucción de §7.1 existe precisamente por esa duda.

---

## 12. Fuera de esta fase, pero destapado por ella

1. **Partir catálogos respetando paréntesis** (§1, hallazgo 6). Defecto real,
   silencioso, corrompe datos; determinista y con prueba fácil. Recomendado como
   trabajo inmediato siguiente, **antes** que esta fase si hay que elegir.
2. **`_parece_condicion` en `diccionario.py`** descarta en silencio condiciones
   en prosa sin «solo si/cuando» ni símbolo de comparación. Limita cuánto puede
   llegar a resolver el generador DIC-08.
3. **La lámina 6 de la presentación** ilustra con errores inexistentes. Debe usar
   la etiqueta real de Reposición de Placas, que se defiende sola.

---

## 13. Puntos abiertos

1. **Cuota.** El nivel gratuito de AI Studio se agotó durante la medición
   (`generate_content_free_tier_requests`). Para uso real hace falta decidir
   plan de pago o proveedor definitivo — la Dirección ya señaló que Gemini es
   solo para pruebas.
2. **Rotar las dos llaves** que se pegaron en chat. Sigue pendiente.
3. **¿Entran los nombres de pantalla?** Solo tras medirlos.
