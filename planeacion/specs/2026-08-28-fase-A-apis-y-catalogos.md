# Fase A — Integración de catálogos remotos y APIs

- **Fecha:** 2026-08-28, revisado 2026-08-29
- **Estado:** aprobado, pendiente de plan de implementación
- **Alcance:** `src/gpmc/nucleo/integraciones.py` (nuevo), `src/gpmc/extractores/diccionario.py`,
  `src/gpmc/compilador/a_gpm.py`, `src/gpmc/simulador/html.py`, pruebas.
- **Fuera de alcance:** el componente `api_ajax` (ver §6, requiere una decisión humana sobre
  un invariante), roles y bandeja del servidor público, `SINTAXIS_ESTRICTA`,
  `nucleo/formato.py`, `validador/`.

## 1. Contexto

El Diccionario de Datos "híbrido" trae dos columnas que hasta la Fase 0 se descartaban
enteras: `Dependencia` y `Endpoint / API`. Ahí vive la diferencia entre un desplegable
inerte y uno que se puebla solo desde INEGI, y entre un campo suelto y una cascada
estado → municipio.

Parte del trabajo ya está hecho: `Campo` tiene `dependencia_tipo`, `dependencia_campo` y
`endpoint`, y el extractor los llena. Lo que falta es que esos valores sean **usables** y
que alguien los traduzca al `.gpm`.

## 2. El bloqueo de la versión anterior está resuelto

La versión anterior de este spec declaraba la traducción al `.gpm` bloqueada:

> *"Necesitamos un export auténtico que contenga un `select` remoto y un select en cascada
> para copiar la estructura. Sin ello, no sabemos si GPM requiere `catalog_url`,
> `object_response`, etc."*

**Ese archivo existe:** `Projects/GPM/Acceso a la Informacion/acceso-informacion-publica.gpm`.
Contiene las tres formas que hacían falta, verbatim:

```jsonc
// catálogo remoto simple
"tipo": "select", "catalogo_id": "1",
"extra": {"tamano": "col-xs-12 col-md-3", "catalog_type": "url",
          "catalog_url": "https://gaia.inegi.org.mx/wscatgeo/v2/mgee",
          "object_response": "datos", "key_object": "nomgeo, cvegeo"}

// catálogo remoto EN CASCADA — la URL interpola el campo padre
"tipo": "select", "catalogo_id": "1",
"extra": {"catalog_type": "url",
          "catalog_url": "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@estado_sol",
          "object_response": "datos", "key_object": "nomgeo, cvegeo",
          "dependent_populated": "1", "populated_by": ["estado_sol"]}

// autollenado por API (fuera del alcance de esta fase, ver §6)
"tipo": "api_ajax", "catalogo_id": null,
"extra": {"url": "https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn",
          "request": "get", "campos": ["curp"], "valores": ["@@curp_solicitante"],
          "prefijo": "data", "get_campos": ["@@curp_solicitante"],
          "get_valores": ["blur"],
          "get_value_campos": ["@@nombres_sol", "@@paterno_sol", "@@materno_sol"],
          "get_value_valores": ["nombres", "apePat", "apeMat"]}
```

`key_object` es `"etiqueta, valor"`: `estado_sol` **muestra** `nomgeo` ("Hidalgo") y
**guarda** `cvegeo` ("13"). Esa distinción es la que hace funcionar la cascada, porque
`mgem/13` devuelve los municipios de Hidalgo. El Diccionario nunca la escribió.

## 3. El registro de endpoints — `nucleo/integraciones.py` (nuevo)

El Diccionario da el endpoint **abreviado** (`` `mgee` (INEGI) ``). La plataforma necesita
cuatro datos más que solo existen en el export. El registro cierra esa brecha.

```python
@dataclass(frozen=True)
class Catalogo:
    clave: str                        # "mgem"
    proveedor: str                    # "INEGI"
    url: str                          # con {padre} si es en cascada
    nodo: str                         # "datos" — donde vive el arreglo
    etiqueta: str                     # "nomgeo" — lo que se ve
    valor: str                        # "cvegeo" — lo que se guarda
    requiere_padre: bool = False
```

**Contenido inicial, verificado contra las APIs vivas el 2026-08-28:**

| clave | proveedor | url | nodo | etiqueta / valor | padre |
|---|---|---|---|---|---|
| `mgee` | INEGI | `https://gaia.inegi.org.mx/wscatgeo/v2/mgee` | `datos` | `nomgeo` / `cvegeo` | no |
| `mgem` | INEGI | `https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@{padre}` | `datos` | `nomgeo` / `cvegeo` | sí |
| `zip_codes` | SEPOMEX | `https://sepomex.kurenn.dev/api/v1/zip_codes?zip_code=@@{padre}` | `zip_codes` | `d_asenta` / `d_asenta` | sí |

Comprobado: `mgee` devuelve 32 estados; `mgem/13` devuelve 84 municipios de Hidalgo;
`zip_codes?zip_code=42000` devuelve "Centro", Pachuca. Los tres responden
`Access-Control-Allow-Origin: *`.

**El registro no hace red.** Solo *sabe* URLs; nadie las llama desde Python. El invariante
"sin dependencias de red en el núcleo" queda intacto, y por eso `nucleo/` es su lugar: es un
hecho del dominio, no una decisión de compilación, y lo necesitan tanto el compilador como
el simulador.

**Escape:** un `endpoint` que no esté en el registro se reporta como hueco `API-01` y el
campo se emite como `select` manual vacío. No se inventa una URL.

## 4. Normalización en el extractor

Los valores que hoy guarda el extractor no son usables. Sobre el Diccionario real de
*Acceso a la Información*:

| Campo | Hoy | Debe quedar |
|---|---|---|
| `nombres_sol` | `dependencia_tipo="campo"`, `dependencia_campo="`api_ajax`"` | `dependencia_tipo="api_ajax"`, `dependencia_campo=None` |
| `municipio_sol` | `dependencia_campo="`estado_sol`"` | `dependencia_campo="estado_sol"` |
| `municipio_sol` | `endpoint="`mgem` (INEGI)"` | `endpoint="mgem"` |

Tres reglas:

1. Quitar acentos graves y espacios de ambas celdas.
2. `Dependencia` con valor `api_ajax` → `dependencia_tipo="api_ajax"`. Cualquier otro valor
   no vacío ni `N/A` → `dependencia_tipo="campo"` y ese valor como `dependencia_campo`
   (quitando un `@@` inicial si lo trae).
3. `Endpoint / API` de la forma `` `clave` (PROVEEDOR) `` → quedarse con `clave`. El
   proveedor es informativo; el registro ya lo sabe.

## 5. Emisión al `.gpm`

En `compilador/a_gpm.py`, dentro de `_campo_gpm`, cuando el campo es `select` y trae
`endpoint`:

- Resolver el `endpoint` contra el registro.
- `extra["catalog_type"] = "url"` (en vez de `"manual"`), más `catalog_url`,
  `object_response` y `key_object` del registro. `catalogo_id` sigue en `"1"`.
- Si el catálogo `requiere_padre`, interpolar `@@<dependencia_campo>` en la URL y añadir
  `dependent_populated: "1"` y `populated_by: [<dependencia_campo>]`.
- Si el endpoint no está en el registro, dejar `catalog_type: "manual"` y levantar `API-01`.

**Huecos nuevos** — el extractor propone, no adivina:

| Código | Nivel | Cuándo |
|---|---|---|
| `API-01` | `falta_dato` | el endpoint no está en el registro; se emite catálogo manual vacío |
| `API-02` | `falta_dato` | `dependencia_campo` apunta a un campo que no existe en la pantalla |
| `API-03` | `falta_dato` | el catálogo requiere un padre y no se declaró dependencia |
| `API-04` | `por_confirmar` | el campo declara `api_ajax`; esta fase no lo emite (§6) |

En los cuatro casos **el campo se emite igual** y el trámite compila. Nunca se cae.

## 6. `api_ajax` queda fuera, y por qué

Emitir el componente de autollenado choca con un invariante de `CLAUDE.md`:

> *"No se emiten los componentes `Api variable`, `Javascript` ni `Redirección`."*

Y con un riesgo que la propia guía del equipo documenta:

> `guia_modelado_gpm.md`: *"No insertes tokens de APIs en campos `api_ajax`; toda llamada
> autenticada hazla a través de `Acciones` de tipo PHP."*
> `Proceso y tiempos…`: **SEG-04, riesgo ALTO** — *"Fuga de secretos: API keys de Keycloak y
> RENAPO expuestas en las peticiones AJAX del navegador."*

Hay dos cosas sin resolver que **solo una persona puede decidir**:

1. ¿`Api variable` (el componente prohibido) es lo mismo que `api_ajax` (el tipo de campo
   que el export auténtico sí contiene)? El texto del invariante justifica solo los otros
   dos ("los dos últimos evalúan control de flujo en el navegador"), lo que sugiere que son
   distintos — pero eso es lectura, no confirmación.
2. Si son distintos y se emite `api_ajax`, la regla tiene que ser: **solo endpoints
   públicos**. INEGI, SEPOMEX y SIPUBEH responden sin credencial (verificado). RENAPO y SAT
   no, y un trámite que los pida debe reportarse como hueco y mandarse a una Acción PHP.

Los catálogos remotos de §5 **no tocan nada de esto**: son campos `select` normales con una
URL en su `extra`, sin componente prohibido y sin credencial. Por eso esta fase los entrega
y deja `api_ajax` detrás de una decisión explícita.

## 7. El simulador

`simulador/html.py` ya distingue visualmente los campos con dependencia (insignias "⚡ API
AJAX" y "Depende de: X"). Falta que **ejecute** los catálogos: al abrir la pantalla, poblar
cada `select` remoto llamando su URL; y al cambiar un campo padre, repoblar sus hijos.

Los tres endpoints responden `Access-Control-Allow-Origin: *`, así que la página
autocontenida puede llamarlos **sin proxy** y sin que `web/` deje de ser una cáscara
delgada.

Un `select` cuyo catálogo no se pueda resolver se dibuja como desplegable **vacío y
deshabilitado**, nunca como caja de texto: el simulador no puede mentir sobre lo que hará la
plataforma. Eso cierra de paso el pendiente P-02.

## 8. Plan de pruebas

- **Registro:** resolver `mgee`/`mgem`/`zip_codes` da la URL, nodo y claves esperadas; una
  clave desconocida devuelve `None` sin reventar.
- **Normalización:** sobre el Diccionario híbrido inline, `municipio_sol` sale con
  `endpoint="mgem"` y `dependencia_campo="estado_sol"`, sin acentos graves; `nombres_sol`
  sale con `dependencia_tipo="api_ajax"` y `dependencia_campo=None`.
- **Emisión:** un `select` con `endpoint="mgee"` compila a `catalog_type:"url"` y la URL del
  registro; uno con `endpoint="mgem"` y padre `estado_sol` añade `dependent_populated:"1"`,
  `populated_by:["estado_sol"]` y `@@estado_sol` en la URL. Las claves de `extra` coinciden
  con las del export de referencia.
- **Huecos:** `API-01` con un endpoint inventado; `API-03` con `mgem` sin dependencia.
- **Simulador:** el HTML generado trae la URL del catálogo y el nombre del campo padre; un
  `select` sin catálogo resoluble sale `<select disabled>`, no `<input>`.
- **Regresión:** un `select` con catálogo manual (sin `endpoint`) sigue emitiendo
  `catalog_type:"manual"` — lo que fijó la Fase 0.
- Suite completa verde, incluida la prueba de ida y vuelta byte-exacta.

Todos los fixtures **inline**. Ninguna prueba llama a la red.

## 9. Riesgos

- **El registro envejece.** Si INEGI cambia su URL, los trámites emitidos quedan rotos y
  nada lo detecta. Mitigación: el registro está en un solo archivo, con la fecha de
  verificación anotada. Una prueba opcional marcada para saltarse podría comprobarlo contra
  la red, pero no en la suite normal.
- **`key_object` es una cadena con coma** (`"nomgeo, cvegeo"`), no dos campos. Se copia el
  formato del export tal cual, sin "mejorarlo".
- **Solo un export de referencia** contiene catálogos remotos. Las tres formas de §2 salen
  de ese archivo; si otra plataforma o versión los escribe distinto, no lo sabríamos.
- **La cascada se emite pero no se verifica.** Que la plataforma pueble `municipio_sol` al
  elegir estado solo se comprueba importando. Se anota junto a las otras preguntas abiertas.

## 10. Criterios de aceptación

1. `municipio_sol` del Diccionario de *Acceso a la Información* compila a un `select` con
   `catalog_type:"url"`, la URL de INEGI con `@@estado_sol` interpolado,
   `dependent_populated:"1"` y `populated_by:["estado_sol"]`.
2. Las claves de `extra` de ese campo coinciden exactamente con las del mismo campo en el
   export de referencia.
3. Un endpoint desconocido produce `API-01` y un `select` manual vacío; el trámite compila.
4. `nombres_sol` sale con `dependencia_tipo="api_ajax"` y levanta `API-04`; no se emite
   ningún componente `api_ajax`.
5. En el simulador, `estado_sol` se dibuja como desplegable y trae su URL; un catálogo no
   resoluble sale `<select disabled>`.
6. `.venv/bin/pytest -v` en verde.
