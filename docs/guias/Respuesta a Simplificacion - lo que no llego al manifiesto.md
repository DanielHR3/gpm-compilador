# Respuesta: qué no llegó al manifiesto de Prórroga

**Para:** equipo de Simplificación Administrativa
**De:** Dirección de Gestión Tecnológica
**Fecha:** 2026-09-21
**Responde a:** su análisis del compilado de Prórroga y/o Ampliación

---

Comprobamos **uno por uno** sus once puntos contra el código y contra su expediente. El
resultado, sin adornos:

| | |
| --- | --- |
| Puntos que son **defecto o carencia nuestra** | **9** |
| Puntos donde el manifiesto **está bien** y la lectura se prestó a confusión | **2** |
| Cosas que les pedimos cambiar a ustedes | **1** (la que ustedes ya detectaron) |

**Casi todo es nuestro.** Y hay uno que ustedes reportaron como un detalle y para nosotros es lo
más grave de la lista.

---

## Lo más urgente, y no lo habíamos visto

### Las longitudes «máx.» se emiten como longitud EXACTA

Ustedes lo pusieron entre los detalles. Es un defecto que rompe el trámite en producción.

Su Diccionario dice «máx. 150 caracteres» para `razon_social_institucion`. El compilador lee el
número, ignora el «máx.» y emite **longitud exacta = 150**. En la plataforma eso significa que el
campo exige exactamente 150 caracteres: una razón social de 40 **no se puede capturar**.

Comprobado en su expediente: **once campos** salen así, incluidos `numero_placa` (7),
`descripcion_hechos` (1000) y `motivo_rechazo` (500). La causa es una sola línea que busca
`(\d+)\s*caracteres` y no mira si delante decía «máx.».

Y el otro lado del mismo defecto: «exactamente **4 dígitos**» de `modelo` **no se lee**, porque
el patrón exige la palabra «caracteres». Sale sin longitud ninguna.

**No hay nada que cambien ustedes. Es nuestro y lo arreglamos.**

---

## 1. Vistas de solo lectura

**Confirmado, y peor de lo que reportaron.** Las dos filas N/A se convierten en campos, y una de
ellas sale además con el tipo equivocado: `vista_de_solo_lectura_ciudadan` se emite como **campo
de carga de archivo**. Un recuadro para subir un PDF donde ustedes documentaron una vista.

**Su tabla nos sirve tal cual.** Sí podemos leerla. Para que no haya ambigüedad, esta es la forma
exacta que va a reconocer el compilador: una tabla después de la Sección 1, encabezada
`## Vistas de solo lectura`, con esas cuatro columnas y en ese orden.

Es trabajo nuestro y ya está en nuestra lista. Mientras no esté, esas filas seguirán saliendo
como campos: no las den por buenas en el `.gpm`.

## 2. Datos de campos

| Lo que reportaron | Veredicto |
| --- | --- |
| Obligatorio «Condicional» → `false` en 7 campos | **Confirmado. Nuestro.** Ver abajo |
| Longitudes «máx.» y «exactamente 4 dígitos» | **Confirmado. Nuestro, y es lo urgente de arriba** |
| Archivos: formato, tamaño y carga múltiple | **Confirmado.** No leemos esa columna todavía |
| `ayuda` vacía en los 36 campos | **Confirmado. Nuestro** |
| `fecha_vigencia` → texto, `doc_oficio_resolucion` → texto | **Confirmado. Nuestro** |

**Sobre «Condicional»:** tienen razón y además la plataforma sí sabe expresarlo. Lo buscamos en
los doce trámites auténticos que tenemos: un campo condicional se emite como **obligatorio, con su
condición de visibilidad al lado**. Está así en cuatro trámites publicados. O sea que «obligatorio
cuando se muestra» es exactamente lo que la plataforma hace, y nuestro extractor es el que lo
pierde: solo reconoce «Sí» y trata «Condicional» como «No».

**Sobre `ayuda`:** esto nos dolió. El campo existe en nuestro formato y la plataforma lo usa para
el texto de apoyo que ve el ciudadano. Ustedes escriben una Descripción por campo y un Ejemplo
Real, y **no llega ninguno de los dos**. Es ayuda ya redactada, campo por campo, que se está
tirando. No cambien nada: la vamos a aprovechar.

## 3. Flujo y acciones

**Las ramificaciones: confirmado, y es deliberado por ahora.** El flujo sale lineal a propósito.
Traducir solas una etiqueta como «si procede» a una condición es justo donde un error no se nota
hasta producción. Las compuertas se cuentan y se reportan para configurarlas a mano. El editor
visual de flujo que quitaría ese trabajo está en nuestra lista, sin diseño todavía.

**Los dos roles de la Dirección: confirmado.** Salen dos actores (ciudadano y Dirección), sin
distinguir quien elabora de quien autoriza y firma.

> ### Aquí sí hay una lectura equivocada
>
> **«sin acciones ni integraciones (0 y 0)»: el manifiesto trae cinco acciones**, y entre ellas
> **las cuatro variantes del oficio** que dan por perdidas:
>
> - (1) Solicitud de Ampliación y/o Prórroga
> - (3) Oficio de Prórroga con término establecido
> - (4) Oficio de Rechazo de Prórroga
> - (5) Oficio de ampliación de Verificación
> - (6) Oficio de Rechazo de Ampliación
>
> Esas sí se generan. Lo que no se emite es la **consulta a RENAPO**, y eso también es
> deliberado: una llamada autenticada desde el navegador dejaría la credencial a la vista de
> cualquiera. Se reporta como hueco para resolverlo por otra vía dentro de la plataforma.
>
> El cálculo de la fecha de vigencia, la clasificación automática y la firma digital sí están
> fuera: no los emitimos.

## 4. Avisos, notificaciones y documentos

**Confirmado, y con un matiz que les conviene saber.**

- **Notificaciones: no las leemos, y tampoco avisamos de que no las leemos.** Su Sección 3 trae
  disparador, destinatario, medio y contenido: justo lo que necesita el compilador para
  construirlas. Se pierden enteras y en silencio. Es de los primeros de nuestra lista, porque son
  notificaciones ya redactadas trámite por trámite.
- **Textos y Avisos: confirmado**, tampoco.
- **Documentos: la Sección del Diccionario no se lee**, pero los oficios **sí llegan** — los
  tomamos de la carpeta `Documentos/` del expediente. Son las cinco acciones del punto anterior.
  Así que ahí no se pierde nada; solo no usamos su tabla.

## 5. Datos generales

| Lo que reportaron | Veredicto |
| --- | --- |
| **Costo vacío** | **El manifiesto está bien.** Ver abajo |
| «A quién va dirigido» vs «Población / usuario objetivo» | **Confirmado. Nuestro** |
| Tiempo de respuesta copia su nota interna | **Confirmado**, y su arreglo es el correcto |

**El costo no es un error.** El compilador leyó «No — gratuito» y lo dejó **vacío a propósito**:
en este formato, vacío significa gratuito. Si escribiéramos «gratuito» como texto, la plataforma
mostraría un costo llamado «gratuito». No cambien nada.

**Sobre la etiqueta:** no la cambien ustedes. Hoy buscamos la forma exacta `**A quién va
dirigido:**` en el AS-IS y ni siquiera miramos la Ficha técnica del Diccionario, que es donde
ustedes lo tienen bien puesto. El que tiene que aprender a leerlo es el compilador.

---

## Resumen de quién hace qué

**Nosotros**, por orden: las longitudes «máx.» (urgente), el obligatorio condicional, los tipos
`date` y `file`, la `ayuda` a partir de la Descripción y el Ejemplo Real, la Ficha técnica para
los metadatos, las notificaciones y avisos, las vistas como Paso de visualización, y los datos de
archivo (formato, tamaño, múltiple).

**Ustedes**, una sola cosa, y ya la tenían vista: los paréntesis con coma en la Descripción de
`folio_rechazo_previo`, que hoy se leen como un catálogo de dos opciones sin sentido. Lo de
«Tiempo de respuesta» también lo tenían visto y su arreglo es el correcto. **Lo de «Población /
usuario objetivo» no lo toquen**: nos toca a nosotros.

Gracias por el ejercicio. Es la primera vez que vemos la lista de lo que tiramos sin enterarnos,
y esa es justo la clase de defecto que no aparece en nuestras pruebas: las once longitudes
llevaban meses saliendo mal y ninguna prueba nuestra lo veía.
