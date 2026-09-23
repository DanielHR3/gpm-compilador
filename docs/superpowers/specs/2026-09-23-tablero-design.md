# Tablero de Simplificación — diseño

**Fecha:** 2026-09-23
**Estado:** aprobado en conversación, pendiente de revisión escrita
**Depende de:** SPA (SP1), `estimador.py`, `planeacion/registro.clave`

## Propósito

Darle al equipo de Simplificación una vista *entre* trámites que hoy no existe:
qué requisitos se piden una y otra vez, qué datos se capturan en varios
trámites, dónde se atoran los expedientes y qué tan complejo es cada uno.
Todo son agregados; nada del contenido de un expediente sale del servidor.

La primera pregunta que debe contestar, en palabras del usuario: «los
requisitos que se repiten más en los trámites».

## Lo que se decidió y por qué

| Decisión | Alternativa descartada | Motivo |
| --- | --- | --- |
| Registro permanente `tablero.jsonl` en el almacén | Leer el almacén de sesiones y deduplicar | La purga a 7 días haría que el tablero olvidara todo cada semana; el mismo trámite aparece hasta diez veces |
| Se registra **al extraer** (`POST /expedientes`) | Al descargar el `.gpm`; botón «Registrar» | Elegido por el usuario: cuenta todo lo que se sube, resuelto o no |
| Solo agregados por línea | Guardar el manifiesto completo | «Solo agregados, nunca contenido»: los expedientes traen datos de ciudadanos |
| Vista en la SPA con tarjetas y barras CSS | Notebook Jupyter; librería de gráficas | El equipo no instala nada; la SPA no carga nada de CDN; en la SPA no hay tablas |
| Identidad del trámite = `clave(nombre)` de `planeacion/registro.py` | Nueva normalización | Ya existe y ya se usa para lo mismo |

## Parte 1 — Qué se guarda por trámite

Archivo `<almacén>/tablero.jsonl`, una línea JSON por trámite, escrita al
terminar `POST /expedientes`. Misma `clave` → se reemplaza la línea (se
reescribe el archivo entero; es chico y así no quedan duplicados que el lector
tenga que resolver). `_purgar_sesiones` no lo toca: solo borra carpetas cuyo
nombre casa con `_SESION_VALIDA`. Se añade una prueba que lo fije.

| Campo | De dónde sale | Para qué |
| --- | --- | --- |
| `clave` | `registro.clave(m.tramite.nombre)` | identidad |
| `nombre`, `dependencia`, `homoclave` | `m.tramite` | rótulos y filtro |
| `registrado` | fecha de la extracción, ISO 8601 con zona | último registro, actividad por semana |
| `requisitos` | etiquetas de los campos `tipo == "file"`, sin el prefijo «Documento:», con `clave()` para agrupar variantes | requisitos más repetidos |
| `campos` | nombres técnicos de todos los campos, sin `@@` | datos capturados en varios trámites |
| `huecos` | `{codigo: cuenta}` de los huecos **al extraer**, antes de resolver | dónde fallan los expedientes |
| `metricas`, `nivel` | `estimar(m)`: las seis métricas y el nivel sugerido | complejidad |
| `catalogos` | claves de endpoint de `integraciones.CATALOGOS` que usa algún campo | integraciones |
| `actores`, `documentos` | `len(m.actores)`, acciones de tipo `documento` | tamaño |

**No se guarda:** valores de catálogo, textos de plantilla, condiciones,
adjuntos, sesión (`sid`), ni nada leído de un insumo. Una prueba mete un valor
de catálogo y un texto de plantilla en el manifiesto y comprueba que **no**
aparecen en la línea.

Un manifiesto con nombre vacío o «[por confirmar]» no se registra: sin nombre
no hay clave. Se anota en el log a nivel `info`.

Módulo: `src/gpmc/web/tablero.py` con `resumir(m, huecos, estimacion) -> dict`,
`registrar(raiz, linea)` y `leer(raiz) -> list[dict]`. Importa de `nucleo`,
`estimador` y `planeacion.registro`; nada de `nucleo` lo importa a él.

## Parte 2 — Qué contesta el endpoint

`GET /api/v1/tablero?dependencia=` en `web/api.py`. Lee `tablero.jsonl`,
filtra si viene `dependencia`, y devuelve las cuentas hechas:

```
{
  "total_tramites": 6,
  "dependencias": [{"nombre": "SEMARNATH", "tramites": 4}, ...],
  "ultimo_registro": "2026-09-23T18:45:00+00:00" | null,
  "requisitos":        [{"nombre": "Identificación oficial", "tramites": 5, "porcentaje": 83}, ...],
  "campos_compartidos":[{"nombre": "curp", "tramites": 4, "porcentaje": 67}, ...],
  "huecos":            [{"codigo": "DIC-08", "tramites": 5, "total": 23}, ...],
  "complejidad":       [{"clave", "nombre", "dependencia", "nivel", "metricas": {...}}, ...],
  "catalogos":         [{"clave": "mgee", "tramites": 3}, ...],
  "actividad":         [{"semana": "2026-W39", "tramites": 2}, ...]
}
```

- `requisitos` y `campos_compartidos` van de más a menos repetido;
  `campos_compartidos` solo incluye los que salen en **dos o más** trámites.
- `huecos` se ordena por `tramites` y no por `total`, para que un expediente
  con cuarenta `DIC-06` no tape a un código que sale en todos.
- `complejidad` se ordena por nivel (Alto → Bajo) y luego por nombre.
- `actividad` cubre las últimas doce semanas ISO, con ceros donde no hubo nada.
- Sin archivo o vacío: `200` con `total_tramites: 0`, listas vacías y
  `ultimo_registro: null`. Nunca `404`.
- Una línea que no parsea se salta y se registra en el log con su número de
  línea; las demás salen.

## Parte 3 — Qué se ve en pantalla

Ruta `/tablero` en la SPA (igual que `/historial` y `/catalogos`), con entrada
«Tablero» en la barra lateral junto a ellas. Módulo
`frontend/src/features/tablero/`. **Solo tarjetas** (`Card` de shadcn): una por
sección y, dentro, una por elemento cuando la lista lo pide. Ninguna `<table>`.
Barras horizontales en CSS con los tokens del sistema; sin librería de gráficas.

De arriba abajo:

1. **Cabecera con filtro.** Título, «N trámites de M dependencias, último
   registrado el …» y un `Select` de dependencia que refresca todo.
2. **Requisitos más repetidos.** Tarjeta con una barra por requisito: nombre,
   «en X de N trámites» y porcentaje. Primera sección porque es lo pedido.
3. **Datos que se capturan en varios trámites.** Mismo formato con el nombre
   técnico. Al pie: «Estos datos podrían capturarse una sola vez».
4. **Dónde se atoran los expedientes.** Una barra por código con su nombre
   corto en castellano (`features/tablero/codigos.ts`, un nombre corto por
   código; sin tecnicismos del extractor) y en cuántos trámites sale.
5. **Complejidad por trámite.** Una tarjeta por trámite: nombre, dependencia,
   nivel como etiqueta, y las métricas en una fila de pares «Pasos 7 ·
   Bifurcaciones 2 · Campos 46 · Integraciones 1». Al pie, en una línea, la
   advertencia del estimador de que la escala no está calibrada.
6. **Integraciones y actividad.** Dos tarjetas chicas: trámites por endpoint,
   y trámites registrados por semana (doce barras).

Estados: «Cargando…» mientras llega; sin registros, un texto que explica que
el tablero se llena solo al extraer expedientes; error de red, aviso con
`role="alert"`. Todo cabe a ancho de teléfono: las tarjetas se apilan.

## Parte 4 — Pruebas y cierre

Backend (`tests/test_tablero.py`, ampliación de `tests/test_api.py`):

- `resumir` produce solo agregados; un valor de catálogo y un texto de
  plantilla del manifiesto no aparecen en la salida.
- Registrar dos veces la misma `clave` deja una sola línea, la última.
- Un manifiesto «[por confirmar]» no se registra.
- `POST /expedientes` escribe la línea; con huecos bloqueantes también.
- `GET /api/v1/tablero`: vacío → `200` y listas vacías; con tres trámites de
  dos dependencias → requisitos ordenados con porcentaje, huecos ordenados
  por trámites y no por total, `campos_compartidos` sin los de un solo
  trámite, y `?dependencia=` recorta todo.
- Una línea corrupta se salta y las demás salen.
- `_purgar_sesiones` no borra `tablero.jsonl`.

Frontend (`features/tablero/*.test.tsx`, `App.test.tsx`,
`NavegacionLateral.test.tsx`):

- La vista pinta las seis secciones con datos mockeados, sin ninguna `table`,
  y cambia al elegir dependencia.
- Estados vacío, cargando y error.
- `/tablero` pinta el tablero y no la carga de insumos; la barra lateral
  tiene el enlace.

Cierre: `pytest` completo, `scripts/check-frontend.sh`, rebuild del `dist/`,
`launchctl kickstart` del servicio, y `curl` al endpoint en vivo. El tablero
arranca vacío en el servidor porque solo se llena al extraer; se re-extraen
los expedientes de `ejemplos/expedientes/` para que tenga datos el primer día.
Los seis expedientes reales los registra el equipo con una extracción normal.

Documentación: sección en `despliegue/LEEME.md` sobre `tablero.jsonl` (qué
guarda, que no se purga, cómo vaciarlo) y una nota propuesta para CLAUDE.md
que se entrega redactada sin aplicar.

## Fuera de alcance

- Leer la línea «Requisitos:» del AS-IS (prosa): la fuente determinista son
  los campos `file` del manifiesto.
- Tiempos de ciclo de `planeacion/registro.py`: se integran cuando el equipo
  los esté registrando de verdad.
- Convertir `Catalogos.tsx` a tarjetas: sigue en tabla desde antes de la
  regla; se hace cuando se toque esa vista.
