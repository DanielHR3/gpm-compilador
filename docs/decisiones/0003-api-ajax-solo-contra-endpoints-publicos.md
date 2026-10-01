---
estado: aceptada
fecha: 2026-09-22
decidieron: DGT
evidencia: planeacion/actas/2026-09-22-componentes-de-script-en-el-modelador.md, planeacion/actas/2026-09-24-api-ajax-y-fechas-en-runtime.md
---

# 0003 — `api_ajax` se emite, solo contra endpoints públicos

## Contexto y pregunta

El invariante prohíbe emitir `Api variable`, `Javascript` y `Redirección`. Durante un mes no se
supo si `api_ajax` era el mismo componente que `Api variable`; no se resolvía leyendo archivos.

## Opciones consideradas

- Tratarlo como prohibido.
- Emitirlo contra cualquier endpoint.
- Emitirlo solo contra endpoints que responden sin credencial.

## Decisión

Con la plataforma abierta (proceso 1103), el panel **Scripts** lista cuatro entradas separadas:
`Javascript`, `Redirección`, `Api ajax` y `Api variable`. `api_ajax` se emite, **solo contra
endpoints públicos** (INEGI, SEPOMEX, SIPUBEH). Uno que exige token se reporta como `API-05` y se
resuelve con una Acción PHP: una llave en una llamada del navegador queda a la vista. El
autollenado por CURP se vio funcionar en el portal el 2026-09-24 (proceso 1108).

## Consecuencias

- El catálogo vive en `nucleo/integraciones.py`; lo de pago o convenio va en `PROPUESTAS` y nunca
  se emite.
- Los destinos del autollenado son solo campos de texto (el selector de fecha no tiene `name`).
