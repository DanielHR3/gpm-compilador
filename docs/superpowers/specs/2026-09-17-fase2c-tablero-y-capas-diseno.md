# Fase 2c-1 — Tablero de inconsistencias y las tres capas baratas (diseño)

**Fecha:** 2026-09-17
**Estado:** propuesto, pendiente de revisión
**Continúa:** `2026-09-17-agentes-fase2-dic08-design.md` (Fase 2)
**Prepara:** Fase 2c-2, el asistente conversacional (fuera de este spec)

---

## 1. Qué cambia

La pantalla de revisión deja de ser una lista que se recorre y pasa a ser un
**tablero** donde se ve el todo y el detalle a la vez. Y el trabajo de resolver
deja de depender de que haya un modelo disponible: tres capas resuelven o
explican antes de gastar una sola llamada.

Hoy conviven dos modos en `WizardHuecos` —`lista` y `foco`, este último con un
riel numerado del 1 al 19—. Ambos desaparecen.

La motivación es concreta y está fechada: con 19 inconsistencias en pantalla, la
persona de Simplificación no sabe cuántas de cada tipo le faltan, ni cuáles puede
cerrar sola, ni cuáles están esperando un dato que no existe. Recorre una lista.

---

## 2. La medición que lo sustenta

Sobre los seis expedientes reales, el 2026-09-17:

**Prefiltro léxico de candidatos — 52 % menos tokens.** Hoy el contexto de DIC-08
manda *todos* los campos de las pantallas anteriores. Mandando sólo los que
comparten alguna palabra con la frase a traducir:

| Expediente | DIC-08 | tokens hoy | con prefiltro | ahorro |
|---|---:|---:|---:|---:|
| Alta de Avisos de Testamento | 2 | 1 148 | 145 | 88 % |
| Constancia de No Infracción | 4 | 1 910 | 600 | 69 % |
| Prórroga de Verificación | 2 | 1 746 | 383 | 79 % |
| Publicación en el Periódico | 2 | 3 782 | 3 245 | 15 % |
| Reposición de Certificado | 8 | 3 176 | 2 021 | 37 % |
| Holograma Exento | 5 | 4 042 | 1 271 | 69 % |
| **Total** | **23** | **15 804** | **7 665** | **52 %** |

No es sólo más barato: con 5 candidatos en vez de 45 hay muchas menos formas de
elegir el campo equivocado.

**Frases repetidas — 13 %.** De 23 condiciones DIC-08, 20 son distintas. Y ese
13 % es un piso, no un techo: Simplificación reenvía el mismo expediente
corregido varias veces y hoy cada reenvío se paga entero.

**Condiciones sin anclaje — 2 de 23 (8 %).** Dos frases no mencionan ningún campo
del trámite, así que no son comparaciones y ningún modelo puede convertirlas en
regla. Son **la misma frase**, y es exactamente la que trabó la revisión del
2026-09-17:

> «Solo si la validación de formato detecta errores al enviar»

Esa se contesta sin modelo, al instante, y con más acierto que preguntando.

---

## 3. Alcance

**Dentro:**
- El tablero, en sustitución de los modos `lista` y `foco`.
- **Capa 0**: explicaciones por código escritas a mano (cero tokens) y las dos
  decisiones deterministas (§6).
- **Capa 1**: prefiltro léxico de candidatos (§7).
- **Capa 2**: caché de propuestas por inconsistencia (§8).
- El sitio donde entrará el asistente, dibujado pero vacío (§9).

**Fuera:**
- **El chat (Fase 2c-2).** Depende de tener proveedor con cuota real; hoy el
  nivel gratuito de AI Studio se agota con una tarde de mediciones.
- **Los agentes de `MMD-04`, `FLU-01` y `FLU-02`.** El contexto se diseña para
  poder llevarlos en el mismo lote, pero construirlos es otro trabajo. Mientras
  no existan, "un solo lote para todos los códigos" no ahorra nada real y **no se
  reclama como beneficio de esta fase**.
- El simulador y la aprobación, que siguen como están.

---

## 4. El tablero

**Columnas por código, con los nombres que ya se leen hoy en la barra lateral**
—Visibilidad de un campo, Tipo de campo, Compuertas del diagrama…—. Reusar ese
vocabulario importa: es el que la Dirección ya reconoce.

Cada columna encabeza con su nombre, cuántas lleva y cuántas faltan. Con muchos
códigos el tablero desplaza en horizontal; las columnas sin inconsistencias no se
dibujan.

**La tarjeta chica** muestra: el campo o la ubicación por su nombre visible, el
estado (`sin resolver` · `falta un dato` · `resuelta`), y si el agente ya propuso
algo. Nada más: es para escoger, no para resolver.

**Al abrirla** se expande a lo ancho del tablero, en su sitio, con dos mitades:
a la izquierda el control de resolución de siempre (`ControlVisibilidad`,
`ControlCompuerta`, …, sin tocarlos), a la derecha la explicación de la capa 0 y
—cuando exista— el asistente. El resto del tablero sigue visible.

**Lo que se conserva del diseño actual**, porque ya está probado y funciona: la
sección de entrega con la puerta del linter, los enlaces siempre disponibles
(simulador, aprobación, manifiesto), y el comportamiento de cada control.

**Lo que desaparece:** el riel numerado, el «Inconsistencia 5 de 19», el
conmutador lista/foco y el umbral `HUECOS_PARA_FOCO`.

---

## 5. Por qué el tablero antes que el asistente

El tablero no necesita modelo. Si mañana no hay cuota, o el proveedor cambia, o
la Dirección decide otro, la pantalla sigue sirviendo igual. El asistente se
enchufa en un hueco ya dibujado.

Al revés no se puede: un asistente sobre una lista que no deja ver el conjunto
resuelve dudas de una en una sin arreglar el problema de fondo.

---

## 6. Capa 0 — sin modelo, cero tokens

### 6.1 Explicaciones por código

La pregunta más frecuente será *«¿qué significa esto?»*, y **su respuesta no
depende del expediente**: depende del código. `DIC-08` significa lo mismo en
Testamentos que en Reposición de Placas.

Se escriben **una vez, a mano**, junto a los títulos y pistas que ya viven en
`frontend/src/features/huecos/lenguaje.ts`, con tres partes:

- **qué es** — en castellano, sin jerga del compilador;
- **por qué salió** — qué encontró (o no) el extractor;
- **cómo se resuelve** — incluida la salida de configurarlo a mano.

Cero llamadas, respuesta instantánea, y mejor que la de un modelo: el compilador
lo escribimos nosotros. Es texto de presentación, así que vive en el frontend.

### 6.2 Dos decisiones deterministas

**(a) Condición sin anclaje.** Si la frase no menciona ningún campo del trámite
—comparando palabras de ≥ 4 letras, sin acentos, contra nombre, etiqueta y
valores de catálogo de los candidatos— entonces no es una comparación entre
campos y no hay regla que armar. Se marca así **sin llamar al modelo**, y la
tarjeta ofrece directamente «Lo configuro a mano» con el motivo escrito.

Vive en `agentes/` (decide si se llama al modelo), nunca en `nucleo/`.

**(b) Códigos donde el dato no existe.** En `DIC-02` («el catálogo está declarado
como pendiente en el Diccionario») y `META-01` (no se encontró el tiempo de
respuesta) la información **no está en ninguna parte del expediente**. Nunca se
llama al modelo: la tarjeta dice que falta en el origen y ofrece sumarlo a la
lista de lo que hay que pedirle a Simplificación.

Un agente que rellene el catálogo de «Tipo de Sanción» o el tiempo de respuesta
de un trámite no está ayudando: está inventando derecho administrativo.

---

## 7. Capa 1 — prefiltro léxico

En `contexto_dic08`, antes de armar el lote: se toman las palabras de ≥ 4 letras
de las frases de los huecos, se descartan las vacías (`solo`, `cuando`, `campo`,
`valor`, `pantalla`, `siempre`, `visible`, …) y se conservan sólo los candidatos
cuyo nombre, etiqueta o valores de catálogo comparten al menos una.

**Red de seguridad:** si el prefiltro dejara **cero** candidatos para un hueco que
sí tiene anclaje, se manda la lista completa de ese hueco. Ahorrar nunca puede
convertirse en no poder responder.

Los omitidos se registran en `ContextoLote.omitidos`, que ya existe.

El contexto se deja con forma de lote genérico —el hueco lleva su `codigo`— para
que `MMD-04`/`FLU-01`/`FLU-02` puedan viajar en la misma llamada cuando existan.
Hoy eso no ahorra nada y no se cuenta como beneficio.

---

## 8. Capa 2 — caché por inconsistencia

**Clave:** sha256 de (`VERSION_PROMPT` + `hash_instruccion()` + código + frase +
candidatos serializados en orden). El prompt entra en la clave, así que cambiarlo
invalida la caché sola.

**Dónde:** el almacén global, junto a `bitacora-ia.jsonl`, no en la carpeta de
sesión — las sesiones se purgan por TTL y la caché debe sobrevivirlas. Es lo que
hace que el reenvío de un expediente corregido no se vuelva a pagar.

**Qué se guarda:** la respuesta cruda del modelo y su veredicto. **También se
cachean los rechazos y los declinados**: repetir una llamada para volver a
rechazarla cuesta lo mismo que para aceptarla.

**Qué NO se cachea:** nada que dependa de la sesión o de la persona. La clave no
lleva `sid`.

**La bitácora sigue registrando cada uso**, con marca de si vino de caché: la
Licencia AI pide trazabilidad de las interacciones, y un acierto de caché es una
interacción aunque no haya red.

---

## 9. El hueco del asistente

En la mitad derecha de la tarjeta abierta, bajo la explicación de la capa 0, se
reserva el sitio del chat. En esta fase se dibuja **vacío**: sin componente, sin
endpoint, sin llamadas.

Queda escrito aquí para que 2c-2 no tenga que rediseñar la pantalla, y para
recordar el candado que tendrá: el chat podrá **decir** lo que sea, pero sólo
podrá **hacer** dos cosas — proponer una resolución de las que ya existen, que
pasa por el filtro determinista y por el `POST /resolver` de siempre, o
recomendar configurarlo a mano. Nunca escribe sin un clic de la persona.

---

## 10. Componentes

```
frontend/src/features/huecos/
  Tablero.tsx            NUEVO  columnas, cuentas, desplazamiento
  ColumnaCodigo.tsx      NUEVO  una columna: encabezado + tarjetas chicas
  TarjetaChica.tsx       NUEVO  nombre, estado, marca de propuesta
  TarjetaAbierta.tsx     NUEVO  dos mitades: control | explicacion (+ hueco chat)
  Explicacion.tsx        NUEVO  la capa 0, desde lenguaje.ts
  lenguaje.ts            MODIF  EXPLICACIONES por codigo
  agrupar.ts             MODIF  agruparPorCodigo
  WizardHuecos.tsx       MODIF  monta el tablero; se va lista/foco
  ModoFoco.tsx           SE VA
  RielEntrega.tsx        reusa  la seccion de entrega no cambia
  TarjetaHueco.tsx       reusa  pasa a ser el contenido de TarjetaAbierta
  controles/*            reusa  sin tocar
src/gpmc/agentes/
  anclaje.py             NUEVO  prosa_sin_anclaje(), puro, sin red
  contexto.py            MODIF  prefiltro lexico + red de seguridad
  cache.py               NUEVO  leer/escribir por huella
  dic08.py               MODIF  consulta la cache antes de llamar
```

`Explicacion.tsx` y `anclaje.py` son funciones puras: se prueban sin proveedor y
sin render.

---

## 11. Contratos

**No se agrega ni se quita ningún endpoint.** El tablero se arma con lo que
`/estado` ya devuelve, y resuelve con los mismos `POST /resolver` y
`POST /reconocer`. La única modificación es **aditiva**, en el cuerpo que ya
devuelve `GET /expedientes/{sid}/propuestas`.

Un hueco que la capa 0 decidió sin modelo **sí genera entrada** en
`propuestas.json`, aunque no haya habido llamada: es la forma de que la tarjeta
explique por qué no hay propuesta sin volver a preguntar nada.

```jsonc
{ "ubicacion": "p1::campos_con_error",
  "sin_anclaje": true,
  "motivo": "la frase no menciona ningún campo del trámite",
  "condicion": null,
  "veredicto": "sin_anclaje",
  "decision": null }
```

Los clientes viejos ignoran los campos nuevos; los huecos con propuesta real
mantienen exactamente la forma de la Fase 2.

---

## 12. Errores y estados

- **Sin proveedor, o error, o cuota agotada:** el tablero funciona completo. Las
  tarjetas muestran su explicación de la capa 0 y sus controles. No hay pantalla
  vacía ni traza; es el estado normal, no una falla.
- **Propuesta rechazada por el filtro:** la tarjeta se comporta como si no
  hubiera propuesta. El veredicto queda en `propuestas.json` para auditar.
- **Caché corrupta o ilegible:** se ignora y se llama al modelo. Una caché nunca
  puede romper la revisión.
- **Expediente sin inconsistencias:** el tablero no se dibuja; sólo la entrega.

---

## 13. Pruebas

- **`anclaje.py`**, función pura: la frase medida («Solo si la validación de
  formato detecta errores al enviar») da *sin anclaje*; una que nombra un campo
  real da *con anclaje*; las palabras vacías no cuentan como anclaje.
- **Prefiltro**: recorta candidatos; y con cero candidatos para un hueco anclado
  devuelve la lista completa (la red de seguridad de §7).
- **Caché**: misma huella no llama al proveedor; cambiar `VERSION_PROMPT`
  invalida; un rechazo también se cachea; una caché ilegible no rompe nada.
- **Sin anclaje sin llamada**: un hueco decidido por la capa 0 aparece en
  `propuestas.json` con `veredicto: "sin_anclaje"` y el proveedor **no** se
  invoca ni una vez (se verifica con `ProveedorFalso` contando llamadas).
- **Tablero**: agrupa por código con los títulos de hoy; una columna vacía no se
  dibuja; abrir una tarjeta no cierra el tablero; resolver mueve la tarjeta a
  `resuelta` y actualiza la cuenta de su columna.
- **Explicaciones**: todo código que aparece en `TITULOS` tiene explicación, o la
  prueba falla. Evita que un código nuevo quede mudo.
- **Regresión**: la sección de entrega y la puerta del linter siguen igual.

---

## 14. Puntos abiertos

1. **Cuota y proveedor definitivo.** Bloquea 2c-2, no esta fase. La Dirección ya
   dijo que Gemini es sólo para pruebas.
2. **Cuánto ahorra la capa 0** depende de qué pregunte la gente, y no hay
   usuarios todavía. Es una apuesta razonada, no una medición — a diferencia del
   52 % y el 13 %, que sí lo son.
3. **Rotar las dos llaves** pegadas en chat. Sigue pendiente.
4. **El defecto de los catálogos partidos por coma** (spec de la Fase 2b, §12)
   sigue sin arreglar y corrompe datos hoy.
