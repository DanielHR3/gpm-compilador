# Fase 3 compacta: catálogo de campos aprobados y respuesta en JSON

Fecha: 2026-11-11 · Pidió: Daniel («reducelo lo más que se pueda») · Estado: aprobado el enfoque, en implementación.

## Problema

La licencia de norte70 del Compilador (500 mil tokens) iba en 70 % antes de producción. Una corrida
de la Fase 3 costaba ~40 mil tokens (≈ 22 mil tras `85ffcf9`), porque el modelo **redacta los dos
documentos completos en Markdown** en cada expediente:

- Un Diccionario aprobado mide ~15 mil tokens; casi todo son filas de tabla.
- Cada llamada lleva instrucciones de formato, plantilla y ejemplo (~4,500 tokens) solo para que el
  modelo aprenda a escribir esas tablas.
- En los 26 Diccionarios aprobados de la wiki, **46 % de los campos de cada trámite ya existe en otro**
  (CURP + SIPUBEH en 16, folio en 15, nombres y apellidos en 14, pago en 12…).

## Idea

El modelo **decide**; el Compilador **escribe**.

1. **Catálogo de campos aprobados** (`src/gpmc/agentes/catalogo/campos.yaml`, versionado en el repo):
   cada campo con su `@@id`, etiqueta, tipo, componente, límites, catálogo de valores y la **fila
   Markdown tal como el equipo la aprobó**. Se construye con `gpmc catalogo construir --wiki …`
   desde los Diccionarios de la wiki; solo entran campos que aparecen en 2 o más trámites (lo de un
   solo trámite es particular y no se reusa). Sin datos de casos reales: la columna «Ejemplo Real
   del Campo» no se copia.
2. **Una sola llamada** que devuelve JSON compacto:
   ```json
   {"pantallas": [{"actor": "CIUDADANO", "nombre": "Solicitud",
                   "campos": ["@@curp", "@@nombres", {"etiqueta": "Folio del permiso anterior",
                              "tipo": "Texto", "obligatorio": true, "id": "folio_permiso"}]}],
    "flujo": [{"de": "Solicitud", "a": "Revisión"},
              {"de": "Revisión", "a": "Corrección", "si": "@@dictamen == 'Rechazado'"}],
    "eliminaciones": [{"elemento": "Copia de INE", "se_elimina": true, "fundamento": "…"}],
    "problema": "…", "impacto": ["…"], "riesgos": ["…"], "pendientes": ["…"]}
   ```
   Un campo del catálogo es solo su `@@id` (3–5 tokens en vez de ~60 de una fila).
3. **El Compilador arma el Markdown** del Diccionario (filas del catálogo + filas nuevas en el mismo
   formato) y de la Propuesta TO-BE (secciones fijas + diagrama Mermaid compilable generado del
   `flujo`). Lo que sigue después no cambia: `extraer_borradores`, verificación, huecos, decisión
   por documento, extracción y `.gpm`.
4. **Requisitos sin IA**: cada requisito que `requisitos_del_as_is` lee del AS-IS ya es un campo
   Archivo; se le pasa al modelo como hecho, no como tarea.
5. **Caché por huella del AS-IS** (`sha256` del texto recortado + versión del prompt + versión del
   catálogo): subir el mismo AS-IS otra vez no llama al modelo.
6. **El catálogo crece**: lo que el equipo acepta o corrige alimenta la siguiente construcción del
   catálogo (paso manual `gpmc catalogo construir`, revisado por PR; nada se aprende solo en producción).

## Lo que viaja al modelo

| Bloque | Hoy | Compacta |
|---|---|---|
| Instrucciones | ~1,700 ×2 | ~700 ×1 (reglas de decisión, no de formato) |
| Plantilla + ejemplo | ~2,800 ×2 | 0 |
| Catálogo | — | ~600 (`@@id · etiqueta · tipo`, solo los recurrentes) |
| AS-IS recortado | ~4,500 ×2 | ~4,500 ×1 |
| Diccionario generado (entrada del TO-BE) | ~3,000 | 0 (misma llamada) |
| Salida | ~4,000–6,000 | ~1,200–2,000 (JSON con referencias) |
| **Total estimado** | **~22 mil** | **~7–8 mil** |

## Reglas

- **Nada inventado por el Compilador:** si el modelo cita un `@@id` que no está en el catálogo, se
  rechaza esa referencia y queda como hueco (`GEN-04`, nuevo, `falta_dato`), no se adivina.
- El catálogo **no** reemplaza la decisión del equipo: el Diccionario armado se revisa y se acepta,
  corrige o declina igual que hoy.
- El esquema JSON se valida con Pydantic; un JSON inválido es `RespuestaInvalida` (no se reintenta).
- La ronda de mejora bajo pedido sigue existiendo y usa el mismo formato JSON (solo manda los huecos
  y las referencias, no los documentos).
- `VERSION_PROMPT_COMPACTA = "compacta-v1"`; la bitácora mide `tokens_total` y `saldo` por llamada.
- El camino actual (`dicc-v3` / `tobe-v3`) queda detrás de `GPMC_FASE3_MODO=documentos` como
  respaldo durante la transición; por omisión, `compacta`.

## Pasos

1. Catálogo: constructor, `campos.yaml`, medición de cobertura sobre los 26 Diccionarios.
2. Esquema JSON y armado del Markdown (Diccionario y TO-BE) — pruebas: el Markdown armado lo lee
   `extraer_borradores` sin huecos de formato y compila a `.gpm`.
3. Prompt compacto y `generar()` en una llamada; caché por huella.
4. Mejora bajo pedido en formato compacto.
5. Medición en producción con `saldo`: una corrida real antes/después.
