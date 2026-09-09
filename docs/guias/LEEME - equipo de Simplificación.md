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

1. **Sube los tres archivos** del expediente. El Diccionario de Datos es obligatorio; sin él no
   hay pantallas que compilar.
2. **Revisa lo que extrajo.** Verás las pantallas, los campos, la complejidad estimada y —lo más
   importante— **los huecos**.
3. **Resuelve los huecos.** Son las cosas que la herramienta no pudo deducir de sus documentos y
   que decidió *no inventar*. Por ejemplo: un campo sin nombre técnico `@@` en su descripción, o
   un catálogo que el Diccionario marca como pendiente.
4. **Recorre el trámite** en el simulador, para ver el flujo como lo vería el ciudadano.
5. **Descarga el `.gpm`** y pásalo a la DGT para que lo importe.

## Dos cosas que conviene tener claras

**El flujo que propone es lineal**, una tarea por pantalla en orden. Las compuertas de su
diagrama TO-BE se cuentan y se reportan, pero **no se reproducen**: hay que ramificarlas a mano.
Traducir automáticamente una etiqueta como *"si procede"* a una condición sería justo el tipo de
error que nadie nota hasta que el trámite ya está en producción.

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
