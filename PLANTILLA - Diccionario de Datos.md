# Plantilla del Diccionario de Datos — equipo de Simplificación

El compilador arma el `.gpm` **entero** a partir de tu Diccionario de Datos y tu
Propuesta TO-BE. Si esos dos vienen consistentes, el trámite sale bien y con poco
trabajo manual después. Si vienen de seis formas distintas, el compilador o los
rechaza o los degrada.

Esta plantilla recoge las reglas de formato que evitan los errores reales de la
semana del 1–3 de septiembre de 2026 (nombres largos que tumbaban el import,
`foreach()` en las vistas, catálogos que salían vacíos).

> **Regla de oro:** antes de mandar el expediente, córrelo en el asistente y
> **resuelve todos los huecos marcados como bloqueantes**. Un hueco no es un
> error de la herramienta: es algo que no pudo deducir y decidió no inventar.

---

## 1. Encabezado de cada pantalla

Exacto, con los tres guiones largos `—`:

```
### Pantalla 3 — NOTARIO — Captura del Aviso
```

- `### ` (tres almohadillas y un espacio). `#### ` solo si va anidada bajo un
  `### Paso N del stepper`.
- `Pantalla N` con número.
- `ACTOR` en mayúsculas: es quien ejecuta esa pantalla (CIUDADANO, NOTARIO,
  ÁREA DE AVISOS, DIRECCIÓN DE VERIFICACIÓN…). De aquí sale el carril de la
  tarea.
- Nombre de la pantalla al final.

**Así no:**
- `### Captura del Aviso` (sin `Pantalla N — ACTOR —`)
- `**Pantalla 3:** Captura` (con negritas o dos puntos)
- Nombre con anotaciones de prueba: `Captura *(Tarea GPM #7920 en un mockup…)*`
  — eso desborda la columna de la plataforma. Quítalo.

---

## 2. Tabla de campos — columnas

En este orden, con esta cabecera:

```
| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real del Campo | Descripción | Elementos Relacionados |
```

Cada fila = un campo. Sin filas duplicadas.

---

## 3. Nombre técnico `@@` — obligatorio y corto

Cada campo lleva su nombre técnico dentro de la **Descripción**, así:

```
[Captura] Campo `@@curp_solicitante`. Dispara la consulta a RENAPO…
```

Reglas:

| Regla | Por qué |
|---|---|
| **Máximo 30 caracteres.** | La columna `campo.nombre` de la plataforma corta ahí. Un nombre de 38 (`@@fecha_vencimiento_certificado_anterior`) **tumba el import entero** con `Data too long`. |
| Solo `a–z`, `0–9` y `_`. Sin acentos, sin mayúsculas, sin espacios. | Es un identificador, no una etiqueta. |
| Único en todo el trámite. | Dos campos con el mismo `@@` colisionan. |
| Si el mismo campo aparece en varias pantallas (vista de solo lectura), usa **el mismo** `@@`. | Es el mismo dato. |

**Así sí:** `` `@@fecha_venc_certificado_ant` `` (28) · `` `@@monto` `` · `` `@@tipo_solicitante` ``
**Así no:** `` `@@fecha_de_vencimiento_del_certificado_anterior` `` (46) · `` `@@Monto a Pagar` `` · sin `@@` en la descripción

Si un `@@` que ya usas en el diagrama TO-BE o en una fórmula tiene más de 30
caracteres, **acórtalo en los dos lados a la vez**.

---

## 4. Catálogo de Valores — un solo formato

Las opciones de un `select` o `radio` van en la columna **Catálogo de Valores**,
separadas por ` · ` (espacio, punto medio `·`, espacio):

```
Doble cero · Cero · Uno · Dos · Exento
```

| Regla | Por qué |
|---|---|
| **Siempre en la columna "Catálogo de Valores"**, nunca en "Límite/Especificaciones". | El compilador lee las opciones de esa columna. |
| **Separador ` · `** siempre. No comas, no `<br>`, no `/`. | Cada separador distinto es una regla más que puede fallar. |
| Sin envoltura: escribe `A · B · C`, no `(catálogo: A, B, C)`. | El prefijo `(catálogo:` se colaba dentro de la primera opción. |
| Un campo `select`/`radio` **sin catálogo revienta la vista** (`Invalid argument supplied for foreach()`). Si no hay valores todavía: escribe `pendiente` (queda reportado como hueco `DIC-02`), o cambia el componente a texto. | Un desplegable vacío no sirve y rompe la pantalla. |
| Para Sí/No: `Tipo de Dato = Boolean` y ya. El compilador pone `Sí · No` solo. | No hace falta repetirlo. |

**Así sí:** `Persona física · Persona moral / institución`
**Así no:**
- `Doble cero, Cero, Uno, Dos` (comas)
- `Soltero <br>Casado <br>Viudo` (`<br>`)
- `(catálogo: Público abierto, Público Cerrado)` (envoltura + comas)
- `Sí / No` puesto en la columna Límite con Catálogo en `N/A`
- `Valores definidos` (no es una lista)

---

## 5. Componente Sugerido (GPM) — vocabulario

El compilador mapea el texto de esta columna a un tipo de campo. Usa estas
palabras:

| Escribe | Sale como |
|---|---|
| `Lista desplegable (select)` · `Desplegable` | `select` |
| `Botones segmentados` · `Radio Sí-No` · `Opción única` | `radio` |
| `Campo de texto (input)` · `Input` | texto |
| `Área de texto (textarea)` | textarea |
| `Selector de fecha (calendario)` | fecha |
| `Carga de archivo (uploader)` | archivo |
| `Párrafo` · `Nota informativa` · `Badge` | párrafo (solo lectura) |

**Ojo:** `Selector de fecha` es una fecha, no un desplegable. No escribas
`Cita (calendario de agendamiento)` esperando el componente de citas: ese hay
que configurarlo a mano en la plataforma; el compilador solo puede dejar una
fecha.

---

## 6. Condición de Visibilidad — forma simple

Si un campo solo se muestra bajo condición, escríbela **exactamente** así:

```
Visible solo si "Etiqueta del campo que gobierna" = Valor
Visible y obligatorio solo si "¿Es Persona Moral?" = No
Visible solo cuando `@@procedencia` = Municipio
Obligatorio solo si "¿Tiene Sanción?" = Sí
```

- `Visible` / `Obligatorio` / `Visible y obligatorio` + `solo si` / `solo cuando`
  / `cuando`.
- La referencia entre comillas (la **etiqueta** de otro campo) o como `` `@@campo` ``.
- `= Valor` — un solo valor, tal cual aparece en el catálogo de ese campo, o
  `Sí` / `No`. Se admite `≠` para "distinto de".
- El campo que gobierna debe estar **antes** en el Diccionario.

**Lo que el compilador NO interpreta** (lo reporta como hueco `DIC-08`, y hay que
configurarlo a mano):

- Conjuntos: `∈ {Acuerdo, Decreto, Ley}`
- Condiciones compuestas: `X = A y "Otro campo" = B`
- Rangos o prosa: `el estatus es "Publicado" o posterior`
- Referencias a la visibilidad de otro elemento: `cuando "X" está visible`

Si necesitas una de esas, sepárala en campos/pasos más simples o déjala para
configuración manual — no la escribas a medias.

---

## 7. Propuesta TO-BE — el diagrama Mermaid

```mermaid
flowchart TD
    A[Ciudadano: Captura la solicitud]:::ciudadano --> B{¿@@procede == 'si'?}:::area
    B -->|Sí| C[Área: Cotiza]:::area
    B -->|No| D[Área: Oficio de improcedencia]:::area
```

| Regla | Por qué |
|---|---|
| **Todo nodo con carril `:::actor`** (`:::ciudadano`, `:::area`, `:::notario`…). | Sin carril el compilador no sabe quién ejecuta esa tarea (hueco `MMD-03`). En Publicación quedaron 36 nodos sin carril. |
| **Cada compuerta `{…}` nombra el campo** que decide, con su `@@`: `{¿@@procede == 'si'?}`. | Si dice solo `{¿Procede?}`, la condición hay que capturarla a mano (`MMD-04`), y el flujo sale lineal. |
| Las etiquetas de las flechas que salen de una compuerta = los **valores** del campo: `-->|Sí|`, `-->|No|`, `-->|Renovación|`. | De ahí sale la regla de transición. |
| El diagrama debe traer un bloque ```` ```mermaid ```` de verdad. | Sin él no se cuenta el flujo (`MMD-01`). |
| Que el número de tareas del diagrama sea coherente con el número de pantallas del Diccionario. | Diferencias grandes (23 tareas vs 4 pantallas) suelen ser un Diccionario incompleto (`FLU-02`). |

> Con el `@@` en cada compuerta y los carriles completos, una versión futura del
> compilador podrá **ramificar el flujo solo**. Sin eso, siempre sale lineal.

---

## 8. Antes de mandar el expediente — lista de verificación

- [ ] Cada pantalla con encabezado `### Pantalla N — ACTOR — Nombre`.
- [ ] Cada campo con `` `@@nombre` `` en su Descripción, ≤ 30 caracteres, sin repetir.
- [ ] Cada `select`/`radio` con su catálogo en la columna correcta, separado por ` · `, o marcado `pendiente`.
- [ ] Componentes escritos con el vocabulario de la sección 5.
- [ ] Condiciones de visibilidad en la forma simple de la sección 6.
- [ ] Diagrama TO-BE con carril en todo nodo y `@@campo` en toda compuerta.
- [ ] Corrido en el asistente: **cero huecos bloqueantes**.
