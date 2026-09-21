# Para probar los dos trámites corregidos

**Para:** equipo de Simplificación Administrativa
**De:** Dirección de Gestión Tecnológica
**Fecha:** 2026-09-21

---

## La liga

```
http://192.168.1.220:8123
```

> **Ojo: esta no es la de siempre.** La que ya conocen —la del puerto **8000**— sigue
> funcionando igual y con ella no pasa nada. Esta otra es una **versión de pruebas**, con los
> cambios que hicimos hoy a partir de sus observaciones. Úsenla solo para esta revisión.

**Tres cosas prácticas:**

- Hay que estar **en la red de la oficina**. Desde casa o con datos móviles no abre.
- **Pruébenla el mismo día que la reciban.** La dirección se mueve sola cuando nuestra máquina
  se reconecta a la red —hoy cambió dos veces en una hora—, así que si mañana no abre **no está
  caída**: pídannos la del día. Ya está pedido a Infraestructura un nombre fijo para que esto
  deje de pasar.
- No hace falta instalar nada ni tener contraseña.

## Qué nos gustaría que miren

### 1. Sus dos trámites corregidos

Metan **Reposición de Certificado** y **Prórroga y/o Ampliación**, los que nos mandaron hoy.
Los pasamos por el compilador y salen **sin un solo nombre técnico repetido**, cuando la versión
anterior traía nueve y tres. Prórroga además queda **sin ninguna inconsistencia que bloquee**.

Lo que queremos confirmar con ustedes es que **la herramienta está de acuerdo con su corrección**,
no solo nosotros.

### 2. La tarjeta nueva: «Nombre técnico repetido»

Cuando dos campos se llaman igual, la pantalla ahora lo dice así:

> el nombre técnico `@@estatus_tramite` lo declaran dos campos; **parece el mismo dato mostrado
> de nuevo**: «Estatus del Trámite» en *Estatus, Resultado y Cotización* y «Estatus del Trámite»
> en *Descarga de la Reposición* son iguales. Déjalo en una sola fila y di en el TO-BE dónde se
> vuelve a mostrar

Y cuando **no** son el mismo dato, cambia el consejo:

> **son dos datos distintos con el mismo nombre**: «Documento: Copia del Certificado» (archivo)
> en *Cargar Copia del Certificado* y «Documento: Reposición de Certificado (PDF)» (texto) en
> *Descarga de la Reposición*. Renombra uno de los dos en el Diccionario

**La pregunta para ustedes:** ¿se entiende sin que nadie se lo traduzca? ¿Dice lo suficiente
para corregirlo, o falta algo?

### 3. El documento de observaciones

El botón **«Descargar observaciones»**, arriba a la derecha. Es el documento que les mandamos,
y ahora incluye estos hallazgos en el apartado del Diccionario. Si algo ahí se lee como un
reproche y no como una indicación, dígannoslo: esa parte la escribimos para que la puedan
integrar tal cual.

## Lo que seguimos debiendo nosotros

Dos cosas de su mensaje, para que no parezca que las dejamos pasar:

1. **Las vistas de solo lectura todavía no se construyen como Paso de visualización.** El
   compilador sigue emitiendo el flujo en línea recta. Es trabajo nuestro y está en cola.
2. **Sigue abierta la pregunta de si dos campos con el mismo `@@` comparten valor** en la
   plataforma. Ningún trámite auténtico lo demuestra, así que lo vamos a probar importando un
   trámite de prueba, y se lo diremos con acta. De eso depende la recomendación del caso 2 —el
   mismo dato mostrado de nuevo—, y si sale que sí comparten valor, se lo diremos con la misma
   claridad aunque nos deje mal.

## Si algo falla

Mándennos el **mensaje de error completo** y el **nombre del expediente**. Con eso basta: la
herramienta va dejando registro de lo que pasa y podemos verlo del lado nuestro.

---

Gracias por la corrección de los dos expedientes, y por la respuesta del otro día. Nos ahorró
trabajo: estábamos por pedirles que cambiaran el Diccionario y lo que había que cambiar era
nuestro compilador.
