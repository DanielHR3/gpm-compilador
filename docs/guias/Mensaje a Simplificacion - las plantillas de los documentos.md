# Los documentos que entrega el trámite salen en blanco

**Para:** equipo de Simplificación Administrativa
**De:** Dirección de Gestión Tecnológica
**Fecha:** 2026-09-22

---

Buen día. Les escribimos por algo que encontramos revisando **Reposición de Certificado** y
**Prórroga y/o Ampliación**, y que tiene arreglo fácil de su lado.

## Lo que pasa

Los oficios y formatos que nos mandaron **entran bien** al compilador: se leen completos y el
trámite se importa sin problema. Lo que ocurre es que la plataforma los va a generar **tal cual
están, iguales para todos los ciudadanos**, porque en el texto no hay ninguna marca que le diga
dónde poner los datos que la persona capturó.

Son siete documentos entre los dos trámites y **en los siete pasa lo mismo**. Es decir: el
ciudadano llena su placa, su folio y su marca, y el PDF que se descarga al final no trae nada
de eso.

## Cómo se arregla

Donde va un dato, se escribe el nombre técnico del campo entre llaves dobles. Nada más. Con el
**(3) Oficio de Prórroga**, que está muy bien redactado, el cambio se ve así:

**Como está hoy**

```
Pachuca de Soto, Hgo., 19 de agosto del 2025.
OFICIO SEMARNATH/DGCC/DVV-670/2025.

C. LUIS DAVID OLIVARES PÉREZ
```

**Como lo entendería la plataforma**

```
Pachuca de Soto, Hgo.
OFICIO SEMARNATH/DGCC/DVV-___/2025.

C. {{nombre_propietario}}
```

Y ya. El resto del oficio se queda **exactamente igual**: la redacción, el fundamento legal, el
formato, todo. Solo cambian los pedacitos que hoy traen el dato de una persona real.

(El número de oficio lo dejamos en blanco a propósito: **en el Diccionario de Prórroga no hay
un campo para él**. Si quieren que salga impreso, hace falta agregarlo; si lo va a sellar el
área a mano, se queda así.)

El nombre que va entre llaves es el **nombre técnico del Diccionario**, el que aparece con
`@@` (por ejemplo `@@nombre_solicitante` se escribe `{{nombre_solicitante}}`). Si escriben uno
que no existe, el compilador se los dice con el nombre exacto para corregirlo: no se pierde.

Las plantillas pueden venir en **Word, Markdown o PDF con texto** — como las han estado
mandando. Si además quieren fijar el título y quién firma, se puede poner una cabecera al
principio:

```
---
titulo: Solicitud de Reposición de Certificado
firmador_nombre: Mtra. Mónica Patricia Mixtega Trejo
firmador_cargo: Secretaria de Medio Ambiente y Recursos Naturales
---
```

## Un ejemplo completo, por si ayuda

Así quedaría el **(1) Formato de Solicitud de Reposición** con los campos que ya existen en su
Diccionario. Lo pueden tomar tal cual:

```
---
titulo: Solicitud de Reposición de Certificado
firmador_nombre: Mtra. Mónica Patricia Mixtega Trejo
firmador_cargo: Secretaria de Medio Ambiente y Recursos Naturales
---

SOLICITUD DE REPOSICIÓN DE CERTIFICADO

Pachuca de Soto, Hgo.

MTRA. MÓNICA PATRICIA MIXTEGA TREJO
SECRETARIA DE MEDIO AMBIENTE
Y RECURSOS NATURALES
P R E S E N T E

Por este medio, {{nombre_solicitante}}, con CURP {{curp_solicitante}}, solicito
copia del certificado de verificación vehicular con los siguientes datos:

Tipo de holograma:          {{tipo_holograma}}
Folio del certificado:      {{folio_certificado_previo}}
Marca del vehículo:         {{marca_vehiculo}}
Submarca:                   {{submarca_vehiculo}}
Placas del vehículo:        {{numero_placa}}
Teléfono de contacto:       {{telefono_contacto}}
Correo electrónico:         {{correo_electronico}}

Pago de la reposición: {{monto_reposicion}} UMAS

Lo anterior con fundamento en lo establecido en EL PROGRAMA DE VERIFICACIÓN
VEHICULAR OBLIGATORIO VIGENTE PARA EL ESTADO DE HIDALGO.
```

**Dos detalles que notamos al armarlo**, y que quizá quieran revisar ustedes:

- El formato en papel pide **«Expedido por el Centro No.»** y **«Semestre / Fecha de
  expedición»**, y el Diccionario **no tiene campos para esos dos datos**. O se agregan, o esas
  líneas se quedan fuera del documento.
- La fecha (*«a ___ de 20___»*) la dejamos sin llenar a propósito: todavía no confirmamos si la
  plataforma pone sola la fecha del día. Lo vamos a probar y se los decimos.

## Dos plantillas que conviene mirar aparte

1. **(1) Solicitud de Ampliación y/o Prórroga** — el archivo que llegó contiene **una sola
   línea de guiones bajos**, nada más. Suponemos que se guardó vacío o se exportó mal.

2. **(5) Reposición de Certificado en el formato establecido** — este llegó como un **PDF
   escaneado**, así que al leerlo solo salen columnas de números sueltos, sin frases. Y ahí va
   lo importante: **son los datos de un certificado real ya expedido** —placa y número de serie
   de un vehículo de una persona—. Tal como está, ese documento se le entregaría con esos datos
   **a todos los ciudadanos** que hagan el trámite. Conviene sustituirlo por la plantilla en
   blanco, con sus `{{campos}}`.

## Lo que es nuestro

Para que no parezca que solo mandamos tarea:

- **Todos los documentos se generan hoy al terminar la primera pantalla del ciudadano**, que no
  es donde deberían generarse —un oficio de resolución tendría que salir cuando el funcionario
  resuelve—. Eso lo pone así **nuestro compilador**, no ustedes, y está en nuestra lista.
- **Ya se pueden ver sin importar nada.** En el simulador hay una sección nueva, **«Documentos»**,
  con una tarjeta por cada uno: se ve la plantilla tal como quedó, en qué punto del flujo se
  genera y quién firma. Ahí mismo se puede abrir la vista previa y descargar la hoja. Es la
  forma más rápida de comprobar un cambio: lo mandan, lo subimos y lo ven.

## Nada de esto detiene el trámite

Los dos trámites **se importan y funcionan igual** con las plantillas como están. Lo único que
no funciona es el documento, que sale en blanco. Así que tómenlo con calma; no hay prisa de
hoy para mañana.

---

Gracias, de nuevo. Cada vuelta de estas nos ha dejado el compilador mejor de lo que estaba:
la última vez el que tenía que corregir era el nuestro.
