# Nota propuesta para CLAUDE.md — no aplicada

Para pegar al final de «Mejoras recientes» cuando el usuario lo apruebe.

---

### 10. Historial y tablero en la SPA (2026-09-23)

- **`/historial` ya es de la SPA.** `GET /api/v1/historial` lista las sesiones del
  almacén con fecha de última actividad; `plantillas.historial` queda sin uso, para
  que SP3 lo tire con `portada`/`revision`.
- **Tablero de Simplificación.** `web/tablero.py` mantiene `<almacén>/tablero.jsonl`:
  una línea por trámite con **solo agregados** (requisitos = etiquetas de campos
  `file`, nombres de campo, huecos por código, seis métricas, catálogos). Se escribe
  al extraer (`POST /expedientes`) y, si el expediente no traía nombre, la primera
  vez que lo recibe en `/resolver` (META-04). `_purgar_sesiones` no lo toca.
  `GET /api/v1/tablero?dependencia=` devuelve las cuentas y `features/tablero/`
  las pinta con barras CSS. Spec y plan en `docs/superpowers/`.
- **En la SPA no hay tablas:** una `Card` por elemento. `Catalogos.tsx` sigue en
  tabla desde antes de la regla; se convierte cuando se toque.
