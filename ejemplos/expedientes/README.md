# Expedientes de ejemplo — conformes a la plantilla

Cada carpeta aquí es un expediente **completo y bien formado**: AS-IS, TO-BE y
Diccionario de Datos escritos contra `ejemplos/PLANTILLA - Diccionario de Datos.md`.
Sirven para dos cosas:

1. **Referencia para el equipo de Simplificación** — copiar la estructura, no
   partir de cero.
2. **Prueba de regresión** — el compilador los procesa sin huecos bloqueantes y,
   cuando el TO-BE lo permite, ramifica el flujo solo.

## `constancia-de-residencia/`

Trámite municipal de 4 pantallas con un ciclo de corrección. Demuestra:

- Encabezados `### Pantalla N — ACTOR — Nombre`.
- Un `@@nombre` ≤ 30 caracteres por campo, en la Descripción.
- Catálogo (`Aprobado · Rechazado`) separado por ` · ` en su columna.
- Condición de visibilidad en forma simple:
  `Visible y obligatorio solo si "Dictamen" = Rechazado`.
- Diagrama TO-BE con carril en todo nodo y `@@dictamen` en la compuerta, con las
  etiquetas de arista (`Aprobado` / `Rechazado`) iguales a los valores del
  catálogo.

Resultado:

```bash
gpmc extraer ejemplos/expedientes/constancia-de-residencia -o /tmp/res.yaml --estricto
# exit 0 — sin huecos bloqueantes; FLU-03 pide confirmar el emparejado nodo↔pantalla

gpmc compilar /tmp/res.yaml -o /tmp/res.gpm
gpmc validar  /tmp/res.gpm          # sin hallazgos
```

El `.gpm` sale con el flujo **ramificado**: `Revisión → Emisión` cuando
`@@dictamen=='aprobado'`, `Revisión → Corrección` cuando `=='rechazado'`, y el
ciclo `Corrección → Revisión`.

> **Pendiente de prueba en plataforma.** Ningún `.gpm` ramificado por este
> compilador se ha importado todavía a `modelador.hidalgo.gob.mx`. Antes de darlo
> por bueno hay que importarlo y recorrer las dos ramas en el portal del
> ciudadano, con acta en `planeacion/actas/` — misma disciplina que PLAT-1…9.
