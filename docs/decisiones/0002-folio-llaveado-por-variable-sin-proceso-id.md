---
estado: aceptada
fecha: 2026-08-31
decidieron: DGT
evidencia: planeacion/actas/2026-08-30-prueba-en-plataforma.md
---

# 0002 — El folio se llavea por el nombre de la variable, sin `proceso_id`

## Contexto y pregunta

La acción de folio leía su contador de `dato_seguimiento` filtrando por `proceso_id`. Al importar,
la plataforma reasigna ese id y **no reescribe** las referencias dentro del PHP de las acciones:
el contador apuntaba a un proceso inexistente y el folio quedaba roto (PLAT-4).

## Opciones consideradas

- `->count()` o `rand()`: colisionan.
- Contador filtrado por `proceso_id`: roto tras importar.
- Contador llaveado por el nombre de la variable, con `lockForUpdate()`.

## Decisión

`\DB::table('dato_seguimiento')->where('nombre', '<variable>')->lockForUpdate()->value('valor')`,
la forma de dos exports auténticos que corren en runtime (constancia-ambiental, pago-de-bases).

## Consecuencias

- Es invariante de dominio: el validador marca `FOLIO-01`/`FOLIO-02` si se emite otra forma.
