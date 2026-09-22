# Acta — el catálogo de Scripts del modelador, visto en pantalla

- **Fecha:** 2026-09-22
- **Dónde:** `modelador.hidalgo.gob.mx`, proceso **1103** (Prórroga y/o Ampliación, importado el
  2026-09-22 desde un `.gpm` del compilador), formulario **8656** «Nueva Solicitud»
- **Qué se hizo:** se abrió el diseñador de la vista y se desplegó el panel **Scripts**. Se abrió
  la configuración de *Api ajax* para leerla. **No se guardó nada**: se cerró con «Cerrar» y el
  formulario quedó como estaba.

Esta acta existe porque `CLAUDE.md` declaraba la cuestión **abierta** con estas palabras: *«No se
resuelve leyendo archivos. Requiere una respuesta humana… Lo sabe quien tenga la plataforma
abierta y vea cómo se llama cada componente en su catálogo.»*

---

## Resultado 1 — `Api variable` y `api_ajax` son componentes DISTINTOS

El panel **Scripts** lista cuatro entradas separadas:

```
- Javascript
- Redirección
- Api ajax
- Api variable
```

**Consecuencia para el invariante.** `CLAUDE.md` prohíbe emitir «`Api variable`, `Javascript` ni
`Redirección`». Esa lista **no incluye `api_ajax`**, y ahora está confirmado que no es un alias:
son cuatro cosas distintas en el catálogo de la propia plataforma. La cuestión abierta queda
**cerrada**: se puede emitir `api_ajax` sin violar el invariante.

La condición que sí se mantiene es la otra: **solo contra endpoints públicos**. INEGI, SEPOMEX y
SIPUBEH responden sin credencial (verificado el 2026-08-28); SAT y RENAPO directo no, y ahí sigue
valiendo `API-05` y la Acción PHP.

## Resultado 2 — el formulario de configuración, campo por campo

Al elegir *Api ajax* el panel se titula **«Edición de Web service Ajax»**. Bajo las propiedades
normales de un campo (etiqueta, variable, ayuda, validación) trae:

| Sección en pantalla | Campos | Clave en el `extra` del `.gpm` |
| --- | --- | --- |
| **Parámetros de configuración** | URL de afectación/consulta | `url` |
| | Método (GET) | `request` |
| | Nombre del campo · Valor del campo · Variable en la misma vista | `campos` · `valores` · `tipo` |
| | Prefijo de respuesta (opcional) | `prefijo` |
| **Eventos para ejecutar el Ajax** | Nombre del campo · Tipo (`Input`) · Acciones (`onBlur`) | `get_campos` · `get_tipo` · `get_valores` |
| **Cargar datos del ajax** | Nombre del campo · tipo · valor | `get_value_campos` · `get_value_tipo` · `get_value_valores` |

El mapeo es **uno a uno** con el `extra` del `api_curp_trigger` de
`acceso-informacion-publica.gpm`. Ya no hace falta inferir la forma: está confirmada por los dos
lados, el export y la interfaz que lo produce.

También hay un botón **«Previsualizar respuesta de Webservice»**, que permite probar el endpoint
desde la propia plataforma antes de guardar.

## Resultado 3 — el prefijo explica la sintaxis `->`

La nota **IMPORTANTE** del propio formulario dice, textualmente, que el prefijo sirve para
identificar los resultados de esa acción y no pisar valores ya obtenidos, y pone este ejemplo:

> Se consultará el mismo servicio de CURP para padre e hijo en distintas ubicaciones del trámite;
> se debe crear una acción con el prefijo **hijo** y otra con el prefijo **padre**. Así, para
> obtener el nombre del hijo dentro del flujo utilizaríamos `@@hijo->nombres` y para el padre
> `@@padre->nombres`.

> [!note] Reconcilia una discusión vieja
> `guia_modelado_gpm.md` sostenía que la forma correcta de citar un campo era
> `@@campo->value === 'valor'`, y el 2026-08-31 se **refutó con prueba en plataforma** para los
> campos `select`: ahí `@@campo == "valor"` funciona, y `SINTAXIS_ESTRICTA` se quedó en `False`.
>
> Esto explica de dónde salía aquella creencia sin contradecir la prueba: **la flecha es para
> leer un dato dentro de una respuesta de webservice**, no para comparar un `select`. Son dos
> cosas distintas que la guía mezclaba. Ninguna de las dos conclusiones cambia.

## Resultado 4 — de paso: las cuatro vistas están en modo edición

El listado de Vistas del proceso 1103 muestra los cuatro formularios como **(E) Modo edición**.
Ninguno en **(V) Modo visualización**. Es `P-09` visto en la plataforma: el compilador no emite
Pasos de visualización, así que las «vistas de solo lectura» del Diccionario no se construyen.

## Lo que queda para implementar el autollenado por CURP

1. **Corregir la URL registrada.** `integraciones.py` tiene
   `https://sipubeh.hidalgo.gob.mx/api/consultacurpn/@@{padre}`; la auténtica es
   `https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn`, GET con parámetro `curp`.
2. **Emitir el campo `api_ajax`** con el `extra` de la tabla de arriba.
3. **Decisión de Simplificación:** SIPUBEH devuelve `nombres`, `apePat` y `apeMat` por separado y
   el Diccionario de Prórroga declara un solo `@@nombre_propietario`.
4. **Aprobación humana para tocar `CLAUDE.md`**, que es donde vive la cuestión abierta y el
   invariante.
