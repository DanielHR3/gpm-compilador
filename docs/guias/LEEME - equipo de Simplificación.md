# Compilador GPM — guía para el equipo de Simplificación

Convierte los insumos que ya producen —Análisis AS-IS, Propuesta TO-BE y Diccionario de Datos—
en el archivo `.gpm` que se importa en la plataforma de modelado.

## Cómo abrirlo

**Doble clic en `Abrir Compilador GPM.command`.**

La primera vez tarda alrededor de un minuto preparando el entorno; después abre en segundos.
Se abre solo en el navegador. Para cerrarlo, `Ctrl+C` en la ventana negra que aparece.

No hay que instalar Python ni nada más: usa el que ya trae la Mac.

> Si macOS dice *"no se puede abrir porque proviene de un desarrollador no identificado"*:
> clic derecho sobre el archivo → **Abrir** → **Abrir**. Solo la primera vez.

## Cómo usarlo

1. **Suelta la carpeta del expediente** completa, o sube los archivos uno por uno. Se reparten
   solos en Diccionario, TO-BE, AS-IS y Vistas; los oficios y formatos que entrega el trámite van
   en **Documentos**. El Diccionario de Datos es obligatorio; sin él no hay pantallas que compilar.
2. **Revisa lo que extrajo.** Verás las pantallas, los campos, la complejidad estimada y —lo más
   importante— **los huecos**.
3. **Resuelve los huecos.** Son las cosas que la herramienta no pudo deducir de sus documentos y
   que decidió *no inventar*. Por ejemplo: un campo sin nombre técnico `@@` en su descripción, o
   un catálogo que el Diccionario marca como pendiente.
4. **Recorre el trámite** en el simulador, para ver el flujo como lo vería el ciudadano. En su
   menú, **Documentos** enseña cada oficio o formato que entrega el trámite con la plantilla tal
   como quedó guardada; se puede descargar como PDF de prueba.
5. **Descarga el `.gpm`**. Cada archivo es una tarjeta con vista previa: mira dentro antes de
   bajarlo. El de **producción** es el que se le pasa a la DGT; el de **pruebas** trae datos de
   ejemplo. Las **Observaciones** se descargan aunque queden inconsistencias pendientes.

## Dos cosas que conviene tener claras

**Las compuertas del TO-BE se reproducen solo cuando el diagrama y el Diccionario casan**: cada
tarea del diagrama tiene que corresponder a una pantalla, y la compuerta tiene que decir sobre
qué campo decide y con qué valor. Si algo no casa, el flujo sale **en línea recta** y se reporta
como inconsistencia de flujo, para que lo ramifiquen ustedes. Traducir automáticamente una
etiqueta como *"si procede"* a una condición sería justo el tipo de error que nadie nota hasta
que el trámite ya está en producción.

**La herramienta propone, no adivina.** Si reporta 50 huecos no está fallando: está diciendo qué
no puede deducir de los documentos. Un extractor que reportara cero huecos sobre material real
estaría inventando.

## Qué le ayuda a la herramienta

Entre más completo el Diccionario de Datos, menos huecos:

- **El nombre técnico en la descripción**, como `` Campo `@@curp_solicitante` ``. Es de donde sale
  el identificador del campo.
- **El catálogo con sus valores separados por `·`**, en vez de "pendiente de confirmar".
- **El encabezado en su formato**: `### Pantalla 3 — NOTARIO — Captura del Aviso`.

## Si algo no sale

Manda el mensaje de error y el nombre del expediente a la DGT. La herramienta no modifica sus
archivos: solo los lee.
