# Observaciones al Diccionario de Datos

**Trámite:** Reposición de Certificado de Verificación Vehicular para Expediente Digital
**Revisado:** 18 de septiembre de 2026 · **Para:** equipo de Simplificación Administrativa

El compilador leyó el expediente completo: **8 pantallas, 41 campos, 2 actores y 9 tareas**. El
documento está bien armado; lo que sigue son **dos cosas que impiden que cuatro campos se
compilen solos**, y las dos se arreglan escribiendo una línea distinta.

Ninguna requiere rehacer nada.

---

## Observación 1 — Los campos de «solo lectura» se están quedando con el nombre de otro campo

### Qué está pasando

Un campo que muestra información de otra pantalla —por ejemplo *«Vista de solo lectura
(Dirección → Ciudadano)»*— **es un campo distinto** del que muestra. Necesita su **propio**
nombre técnico `@@`.

Hoy su descripción empieza así:

> `[Solo lectura] Muestra @@observaciones capturadas por la Dirección en la Pantalla 2…`

Ese `@@observaciones` está puesto como *referencia*, para decir qué se muestra. Pero el compilador
toma **el primer `@@` que encuentra en la descripción** y lo usa como nombre del campo. Resultado:
la vista de la Pantalla 1 y el campo real de la Pantalla 2 **acaban llamándose igual**.

En este expediente ocurre **ocho veces**:

| Nombre que se duplicó | Lo tienen a la vez | |
| --- | --- | --- |
| `@@observaciones` | P1 · Vista de solo lectura (Dirección → Ciudadano) | P2 · **Observaciones** |
| `@@motivo_no_localizado` | P3 · Vista de solo lectura (Dirección → Ciudadano) | P2 · **Motivo de No Localización** |
| `@@doc_preplantilla` | P3 · Visualizar Plantilla | P2 · **Documento: Preplantilla** |
| `@@estatus_tramite` | P3 · Motor de pago en línea · y P8 · Estatus del Trámite | P3 · **Estatus del Trámite** |
| `@@monto_reposicion` | P4 · Vista de solo lectura (Sistema → Funcionario) | P3 · **Monto a Pagar por Reposición** |
| `@@folio_formato_f7` | P5 · Vista de solo lectura (Dirección → Ciudadano) | P4 · **Folio del Formato F7** |
| `@@doc_comprobante_pago` | P6 · Vista de solo lectura (Ciudadano → Funcionario) | P5 · **Documento: Comprobante de Pago** |
| `@@doc_certificado_final` | P8 · Documento: Reposición de Certificado (PDF) | P7 · **Documento: Copia del Certificado** |

### Por qué importa

No es un detalle de forma. **Dos campos con el mismo nombre se estorban**: al armar el trámite, el
compilador no sabe a cuál se refiere una condición que lo cite, y el campo que gana puede ser el
equivocado.

De hecho, **es lo que está rompiendo dos de los cuatro bloqueos de este expediente**. Las
condiciones de las Pantallas 7 y 8 citan «Estatus del Trámite» con los valores *Pago validado* y
*Concluido — reposición disponible*, que **sí existen** en el catálogo de la Pantalla 3. Fallan
porque hay tres campos llamados `@@estatus_tramite` y el que el compilador encuentra no trae el
catálogo. La condición está bien escrita; el nombre duplicado es lo que la tumba.

### Cómo se escribe

**El `@@` propio va primero en la descripción.** Después, todas las referencias que hagan falta:

> `[Solo lectura] Campo @@vista_observaciones_direccion. Muestra el contenido de @@observaciones`
> `(Pantalla 2), para que el ciudadano sepa exactamente qué corregir antes de reenviar.`

Un nombre sugerido por cada caso, para que no haya que inventarlos:

| Pantalla | Campo | Nombre propio sugerido |
| --- | --- | --- |
| P1 | Vista de solo lectura (Dirección → Ciudadano) | `@@vista_observaciones_direccion` |
| P2 | Vista de solo lectura (Ciudadano → Funcionario) | `@@vista_expediente_ciudadano` |
| P3 | Vista de solo lectura (Dirección → Ciudadano) | `@@vista_motivo_no_localizado` |
| P3 | Visualizar Plantilla | `@@visualizar_plantilla` |
| P3 | Motor de pago en línea | `@@motor_pago_en_linea` |
| P4 | Vista de solo lectura (Sistema → Funcionario) | `@@vista_monto_reposicion` |
| P5 | Vista de solo lectura (Dirección → Ciudadano) | `@@vista_folio_formato_f7` |
| P6 | Vista de solo lectura (Ciudadano → Funcionario) | `@@vista_comprobante_pago` |
| P8 | Documento: Reposición de Certificado (PDF) | `@@vista_certificado_final` |

> El de la Pantalla 2 no está duplicado: sencillamente **no declara ningún `@@`**, y el compilador
> tuvo que proponerle uno. Aprovechen y pónganle el suyo.

**Queda una decisión que les toca a ustedes:** *«Estatus del Trámite»* aparece en la Pantalla 3 (con
su catálogo de 6 valores) y otra vez en la Pantalla 8 (con la nota «Ver catálogo en Pantalla 3»). Si
es el **mismo** campo mostrado de nuevo, conviene **repetir el catálogo completo** en la Pantalla 8
en vez de remitir a otra pantalla; el compilador no sigue esa remisión. Si es una **vista** del
estado, dele su propio nombre como los demás.

---

## Observación 2 — Una condición de visibilidad no puede mirar hacia el futuro

### El caso

En la Pantalla 1, el campo *«Vista de solo lectura (Dirección → Ciudadano)»* dice:

> **Condición de Visibilidad:** Visible solo si "¿Documentación Conforme?" = No

La intención se entiende perfectamente: *el ciudadano debe ver las observaciones cuando vuelve a
corregir*. El problema es **cuándo** puede saberse eso.

«¿Documentación Conforme?» es un campo de la **Pantalla 2**, que llena **el funcionario**. Cuando el
ciudadano está llenando la Pantalla 1 por primera vez, ese dato **todavía no existe**: nadie ha
revisado nada. Ninguna plataforma puede evaluar una condición contra un dato que aún no se ha
capturado, y GPM tampoco.

### La regla, en una línea

> **Una condición de visibilidad solo puede mirar un campo de la misma pantalla o de una pantalla
> anterior, y el valor tiene que estar en el catálogo de ese campo.**

Si la condición depende de algo que ocurre **después** —una decisión del funcionario, un pago que
aún no se valida, un estado que fija el sistema más adelante— eso no es visibilidad: **es flujo**, y
se modela en el diagrama TO-BE, no en la columna «Condición de Visibilidad».

### Lo bueno: ustedes ya lo modelaron bien

El regreso ya está en su propio diagrama:

```
P2 → ¿@@documentacion_conforme?
       │
       ├── No  →  vuelve a la Pantalla 1
       └── Sí  →  sigue a la Pantalla 3
```

La ida y vuelta **ya está resuelta ahí**. La condición del Diccionario está diciendo lo mismo por
segunda vez, y esa segunda copia es la que no se puede cumplir.

### Qué escribir en su lugar

**Poner «Siempre visible».** Se llega a la Pantalla 1 por la rama «No» de esa decisión; no hay nada
que condicionar. Cuando no hay observaciones, el recuadro simplemente sale vacío.

Ya tienen el precedente en su propio documento: *«Vista de solo lectura (Ciudadano → Funcionario)»*
de la Pantalla 2 está declarada **«Siempre visible»**. Es el mismo tipo de campo, escrito de la
forma que sí funciona.

**Si prefieren que el recuadro no aparezca vacío**, la alternativa es agregar a la Pantalla 1 un
campo de solo lectura —por ejemplo `@@estatus_solicitud`, con catálogo *Nueva · Con observaciones*—
y condicionar contra él. Al vivir en la misma pantalla, la regla sí se puede construir. Cuesta un
campo más y habría que dejar dicho quién lo fija.

**Lo que no recomendamos** es duplicar la Pantalla 1 como una «Pantalla 1-bis — Corrección»: serían
quince campos repetidos que habría que mantener en dos sitios.

---

## Lo que está bien y conviene no tocar

- **El catálogo de «Estatus del Trámite»** está completo y bien partido: los seis valores se leen
  sin problema. Lo que falla es el nombre duplicado, no el catálogo.
- **El diagrama TO-BE nombra sus decisiones con `@@`** (`@@documentacion_conforme`,
  `@@modalidad_pago`), que es justo lo que hace falta para poder ramificar el flujo.
- **Las condiciones condicionales de la Pantalla 1** —CURP solo si no es persona moral, acta
  constitutiva solo si lo es— están perfectas: miran un campo de la **misma** pantalla, capturado
  antes, y con un valor de su catálogo. Son el ejemplo a seguir.

---

## Resumen de cambios

1. **Nueve filas**: mover el `@@` propio al principio de la descripción, con los nombres sugeridos
   arriba. Las referencias a otros campos se quedan donde están, después.
2. **Una fila** (P1, Vista de solo lectura): cambiar la condición de visibilidad por
   **«Siempre visible»**.
3. **Una decisión**: si «Estatus del Trámite» de la Pantalla 8 es el mismo campo, repetir ahí su
   catálogo completo en vez de remitir a la Pantalla 3.

Con eso, de los cuatro bloqueos quedan cero por esta vía. Si quieren comprobarlo antes de
enviarlo, vuelvan a subir el expediente al compilador: las inconsistencias que desaparezcan son
las que quedaron bien escritas.

## Una nota general, más allá de este trámite

Las condiciones escritas contra **«Estatus del Trámite»** aparecen también en otros expedientes.
Como norma: **cuando la condición dependa de un estado que fija el sistema o de una decisión que
toma alguien más adelante, va en la compuerta del diagrama TO-BE**, no en la columna «Condición de
Visibilidad». Es la causa más frecuente de los campos que hay que configurar a mano.
