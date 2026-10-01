---
estado: aceptada
fecha: 2026-08-31
decidieron: DGT
evidencia: planeacion/actas/2026-08-30-prueba-en-plataforma.md
---

# 0001 — Las reglas de transición se emiten con `@@campo=='valor'`

## Contexto y pregunta

`SINTAXIS_ESTRICTA` (`nucleo/reglas.py`) decide si una regla de transición sale como
`@@campo=='valor'` o como `@@campo->value === 'valor'`. La documentación interna sostenía que la
primera forma fallaba con campos complejos (`select`).

## Opciones consideradas

- `False`: `@@campo=='valor'`.
- `True`: `@@campo->value === 'valor'`.

## Decisión

`SINTAXIS_ESTRICTA = False`. Cuatro exports publicados usan `@@campo == "valor"` sobre `select`, y
en la prueba de runtime un trámite compilado con `False` avanzó por una rama cuya tarea de origen
solo tenía salidas condicionales: solo pudo avanzar porque la regla con `==` evaluó verdadero.

La flecha `->` existe, pero para otra cosa: lee un dato dentro de la respuesta de un webservice
(`@@prefijo->campo`, ver [0003](0003-api-ajax-solo-contra-endpoints-publicos.md)).

## Consecuencias

- La constante no se cambia sin una prueba documentada con acta, y requiere aprobación humana.
