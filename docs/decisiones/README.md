# Decisiones de arquitectura

Una nota por decisión, con la forma de [MADR](https://adr.github.io/madr/): contexto, opciones,
decisión y consecuencias. La evidencia es siempre un acta de `planeacion/actas/`; una decisión
sin acta es una creencia.

| # | Decisión | Estado |
| --- | --- | --- |
| [0001](0001-sintaxis-de-transicion-con-igualdad-simple.md) | Reglas de transición con `@@campo=='valor'` (`SINTAXIS_ESTRICTA = False`) | aceptada |
| [0002](0002-folio-llaveado-por-variable-sin-proceso-id.md) | Folio llaveado por el nombre de la variable, sin `proceso_id` | aceptada |
| [0003](0003-api-ajax-solo-contra-endpoints-publicos.md) | `api_ajax` se emite, solo contra endpoints públicos | aceptada |

Nueva decisión: copiar `plantilla.md` con el siguiente número. `CLAUDE.md` mantiene por ahora sus
secciones «Cuestión resuelta»; reducirlas a un enlace aquí requiere aprobación humana.
