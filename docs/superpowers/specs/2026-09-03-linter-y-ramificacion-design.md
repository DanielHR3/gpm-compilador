# Diseño — Linter de expediente bloqueante y ramificación del flujo

Fecha: 2026-09-03
Estado: propuesta (no implementado)
Contexto: bitácora `2026-09-02 - Lote de reingenieria …` y commits `16dc52c`, `4027b80`.

---

## Motivación

En la semana del 1–3 de septiembre se importaron los seis trámites del lote de
reingeniería a `modelador.hidalgo.gob.mx`. Cada defecto (nombre `@@` de 38
caracteres, `foreach()` en las vistas, `Selector de fecha` mal clasificado) se
descubrió **importando y viendo el error en pantalla**, en tres rondas de
ida y vuelta. El extractor ya reportaba huecos que anticipaban parte de esto,
pero nada impedía descargar el `.gpm` con huecos sin resolver.

Dos cambios reducen ese ciclo:

1. **Linter bloqueante** — el asistente web no entrega el `.gpm` hasta que cada
   hueco esté resuelto o reconocido explícitamente por una persona.
2. **Ramificación del flujo** — cuando el TO-BE da la condición explícita
   (`@@procede == 'si'`), emitir conexiones condicionales en vez de un flujo
   lineal. (Diseño esbozado; requiere su propia fase.)

---

## Parte 1 — Linter de expediente bloqueante

### Estado actual

- `gpmc extraer` escribe el manifiesto y lista los huecos, pero **termina con
  éxito** aunque haya huecos bloqueantes (`cli.py`, rama `extraer`).
- `web/app.py`: la página de revisión muestra los huecos; `GET /descargar/{sid}`
  compila y sirve el `.gpm` **sin comprobar nada**.
- `gpmc compilar` sí se niega, pero solo ante *hallazgos* del validador sobre el
  `.gpm` ya compilado — no ante *huecos* del expediente.

### Niveles de hueco y política

`nucleo/huecos.py` define `NIVELES = ("bloqueante", "falta_dato", "por_confirmar")`.

| Nivel | Códigos típicos | Política del linter |
|---|---|---|
| `bloqueante` | `INS-01`, `INS-03`, `DIC-00`, `DIC-03`, `DIC-04` | No hay `.gpm`. Ya es el comportamiento; el linter solo lo hace visible y explícito. |
| `falta_dato` | `DIC-02`, `DIC-06`, `DIC-07`, `DIC-08`, `META-01`, `MMD-03`, `MMD-04`, `FLU-01`, `FLU-02`, `API-01…04` | **Descarga bloqueada** hasta que cada hueco esté *resuelto* (re-subir el expediente corregido) o *reconocido* ("lo configuro a mano en la plataforma"). |
| `por_confirmar` | `DIC-01`, `DIC-05`, `META-05/06` | No bloquea. Se listan como "revisar de un vistazo". |

El objetivo no es que `falta_dato` sea infranqueable, sino que **nadie mande un
expediente a la DGT sin haber visto y decidido sobre cada hueco**.

### Cambios

**`web/app.py`**

- La página de revisión (`plantillas.revision`) agrupa los huecos `falta_dato` en
  una lista con, por cada uno, dos botones: **"Ya lo corregí, volver a subir"** y
  **"Lo configuro a mano"**.
- El estado de reconocimiento se guarda junto a `huecos.json` en la carpeta de
  sesión: `reconocidos.json` = lista de códigos+ubicación reconocidos.
- `GET /descargar/{sid}/gpm`:
  1. Re-extrae del expediente guardado (no confía en el manifiesto en disco).
  2. Si hay huecos `bloqueante` → 409, mensaje con la lista.
  3. Si hay huecos `falta_dato` no presentes en `reconocidos.json` → 409, "faltan
     N huecos por resolver o reconocer".
  4. Si todo reconocido → compila y sirve, y añade una cabecera/nota en el `.gpm`
     descargado: comentario JSON con la lista de huecos reconocidos, para que la
     DGT sepa qué quedó de configuración manual. *(Alternativa sin tocar bytes del
     `.gpm`: un `<base>.pendientes.txt` en la misma descarga.)*

**`cli.py`**

- `gpmc extraer` gana `--estricto` (por omisión **activado** cuando lo llama el
  asistente web; desactivado para la DGT en terminal). Con `--estricto`:
  - No escribe el manifiesto si hay huecos `bloqueante` o `falta_dato`.
  - Devuelve código de salida 2 y lista lo que falta.
- `gpmc compilar` gana `--desde-expediente <carpeta>` opcional: si se pasa,
  re-extrae y aplica la misma política antes de compilar. Así la puerta también
  existe fuera del navegador.

**`plantillas.py`**

- Plantilla nueva para el bloque de huecos con los botones de reconocer/re-subir.

### Pruebas

- `test_web.py`: `/descargar` devuelve 409 con un expediente que tiene `DIC-07`
  sin reconocer; 200 tras marcarlo reconocido.
- `test_cli.py`: `gpmc extraer --estricto` sale con código 2 y no escribe el
  `.yaml` cuando hay `falta_dato`.
- `test_cli.py`: sin `--estricto`, comportamiento actual intacto.

### Fuera de alcance

- Corregir el expediente automáticamente. El linter reporta y bloquea; la
  corrección la hace una persona contra `PLANTILLA - Diccionario de Datos.md`.

---

## Parte 2 — Ramificación del flujo (esbozo)

> Esto **no** es bounded. Reabre una decisión deliberada del proyecto
> (`FLU-01`: "traducir 'si procede' a una condición sería justo el tipo de error
> que nadie nota"). Necesita su propio spec y prueba en plataforma. Aquí queda
> el boceto para no perderlo.

### El problema

Hoy `extractores/expediente.py` linealiza: una tarea por pantalla en orden
(`t_<pantalla.id>`), más una terminal, y conexiones `t_i → t_{i+1}` sin
condición. El diagrama Mermaid del TO-BE **solo se usa para contar** compuertas y
avisar (`FLU-01`, `MMD-04`). El extractor nunca correlaciona los nodos del
diagrama con las pantallas del Diccionario.

### Condición para ramificar con seguridad

Emitir una conexión condicional **solo** cuando las tres cosas se cumplen:

1. La compuerta del Mermaid nombra **exactamente un** `@@campo` (`n.campos == [x]`),
   y `x` es un campo real del manifiesto.
2. Cada arista que sale de la compuerta tiene una **etiqueta** que resuelve a un
   valor del catálogo de `x` (o `Sí`/`No`).
3. Los nodos destino de esas aristas se pueden emparejar 1:1 con pantallas del
   Diccionario (por nombre normalizado) o con la tarea terminal.

Si algo de eso falla → se mantiene la linealización actual y el hueco `FLU-01`,
igual que hoy. Nada se degrada respecto al estado presente.

### Mecánica propuesta

- **Emparejado nodo↔pantalla** (`extractores/mermaid.py` + `expediente.py`):
  función `emparejar(nodos_mermaid, pantallas)` que casa por
  `_clave(nombre)` y devuelve `{id_nodo: id_pantalla}` más la lista de no
  emparejados. Umbral: si empareja < 60% de las tareas del diagrama, se aborta la
  ramificación entera (probablemente el Diccionario está incompleto — `FLU-02`).
- **Construcción de conexiones**: recorrer el grafo del Mermaid desde el inicio;
  para cada arista `a→b` donde `a` es tarea y `b` tarea, emitir `Conexion(de,
  a)` usando los ids de tarea del manifiesto (vía el emparejado). Para una arista
  que sale de una compuerta, emitir `Conexion(..., cuando=Condicion(campo=x,
  igual=<valor de la etiqueta>, operador=...))`.
- **Reglas**: se emiten con `nucleo/reglas.emitir()` — ya soporta `==` y `!=`.
- **Validación**: `manifiesto.py` ya valida que la condición de una conexión use
  un campo declarado; reutilizar.

### Riesgos

- Emparejado por nombre es frágil: nombres de pantalla y de nodo divergen
  ("Revisar documentación" vs "Área revisa docs"). Mitigación: umbral + reporte
  de cada emparejado en un hueco `FLU-03` "confirma que estas parejas son
  correctas".
- Compuertas anidadas / bucles (reingreso tras rechazo) — la linealización no los
  modela y la ramificación tampoco debería intentarlo en la primera versión:
  detectar ciclo → abortar ramificación de ese tramo.
- Debe probarse importando a la plataforma un `.gpm` ramificado y recorriéndolo
  en el portal del ciudadano, con acta en `planeacion/actas/`, antes de darlo por
  bueno (misma disciplina que PLAT-1…9).

### Precondición de datos

Depende de que el equipo de Simplificación escriba el TO-BE según la sección 7 de
`PLANTILLA - Diccionario de Datos.md` (carril en todo nodo, `@@campo` en toda
compuerta, etiquetas de arista = valores). Sin eso, la condición de seguridad
casi nunca se cumple y todo sigue saliendo lineal.

---

## Orden de trabajo sugerido

1. Parte 1 (linter) — bounded, alto retorno, sin riesgo de plataforma.
2. `PLANTILLA - Diccionario de Datos.md` en manos del equipo de Simplificación;
   un par de expedientes reescritos contra ella.
3. Parte 2 (ramificación) — spec propio + implementación + prueba en plataforma,
   una vez que haya expedientes que cumplan la precondición.
