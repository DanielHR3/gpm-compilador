# Catálogos de APIs, simulador, historial y consulta — diseño

**Fecha:** 2026-09-22
**Estado:** aprobado en conversación el 2026-09-22; se implementa por piezas, en el orden de abajo
**Origen:** el usuario pidió seis cosas en un mismo mensaje. Se descompusieron porque son piezas
independientes con costes muy distintos, y una de ellas (F) es de otra naturaleza.

## Las seis piezas y su orden

| | Pieza | Tamaño | Orden |
| --- | --- | --- | --- |
| **A** | Catálogo de APIs **automático**: ampliar el registro y los sinónimos | Pequeño, backend | 1 |
| **D** | **Sección «Catálogos»** en el asistente: qué endpoints conoce el compilador | Pequeño | 1 (con A) |
| **C** | **Probar la API desde el simulador**: hoy conecta catálogos; falta el autollenado y enseñar la respuesta | Mediano | 2 |
| **E** | **Historial con los `.gpm`** guardados para redescargar | Pequeño, con una decisión de almacenamiento | 3 |
| **B** | Catálogo **seleccionable**: control en pantalla cuando el extractor no puede decidir | Mediano | 4 |
| **F** | **Consulta**: leyes de simplificación + tarjetas informativas, solo lectura | Grande, otra naturaleza | 5, con su propio diseño |

A y D se hacen juntas porque D es lo que permite comprobar A de un vistazo.

## Restricciones que atraviesan todo

1. **El repositorio es público** (`github.com/DanielHR3`, cuenta personal, P-22). Nada reservado
   entra en él. Las **tarjetas informativas son de uso exclusivo de la DGT** hasta que un mando
   superior las solicite: si F se construye, se leen del disco de la máquina, fuera del repo, como
   las sesiones y el registro. Esa regla se mantiene incluso después de migrar a Bitbucket.
2. **Una URL observada en un export auténtico gana** sobre la de cualquier documento. Lo nuevo
   entra solo cuando no hay forma observada. Las cuatro entradas de hoy salen del export
   `acceso-informacion-publica.gpm`.
3. **Solo se emiten endpoints públicos y gratuitos.** Los que exigen token, pago o convenio no se
   emiten (`SEG-04`: la llave quedaría a la vista en el navegador). Un Diccionario que los nombre
   produce `API-05`, nunca silencio.
4. **El núcleo no toca la red.** Comprobar que una API responde es trabajo del simulador (C), que
   corre en el navegador, igual que la plataforma.

---

## A — el registro de endpoints

### El hueco del modelo

El catálogo de la Dirección mezcla dos cosas que el registro actual no distingue:

- **Catálogo**: devuelve una lista para poblar un `select` (estados, municipios, colonias). Es lo
  que `Catalogo` modela hoy: `nodo`, `etiqueta`, `valor`.
- **Consulta**: recibe un dato y devuelve otros para autollenar (CURP → nombre y apellidos). Es un
  `api_ajax`. Necesita `campos_respuesta` y no necesita `etiqueta`/`valor` de lista.

Se añade `tipo: Literal["catalogo", "consulta"]` a `Catalogo`. Las cuatro entradas actuales quedan
como `catalogo` salvo SIPUBEH, que pasa a `consulta`.

### Qué entra — y lo que la autorrevisión descartó

Del «Catálogo Maestro de APIs» (bóveda, 2026-08-11), solo lo que es **oficial, gratuito y sin
token**, y solo si no hay ya una forma observada para lo mismo. Al revisar el documento entrada
por entrada, **ninguna candidata nueva cumple las tres condiciones con lo que hay escrito**:

| Candidata | Por qué NO entra como emitible |
| --- | --- |
| `codigos.zip` (códigos postales) | «1 000 req/hora **con API Key**»: pide llave. Va a `APIS_CON_TOKEN` |
| Padrón de notarías (`datos.gob.mx`) | El endpoint documentado lleva `resource_id=notarias-indaabin`, un **marcador**, no un identificador real (son UUID). Sin forma de respuesta |
| CCT de escuelas (`datos.gob.mx`) | `resource_id=cct_sep_resource_id`, literalmente un marcador |

Así que el registro emitible **sigue en cuatro**: INEGI estados, INEGI municipios, SEPOMEX y
SIPUBEH, todos con forma observada. Lo que A entrega no es «más endpoints» sino:

1. la distinción `catalogo` / `consulta` en el modelo;
2. `SINONIMOS` ampliado con lo que un Diccionario escribe de verdad;
3. que los de pago, llave o convenio queden **registrados** y produzcan `API-05` con un mensaje que
   diga qué son y por qué no se emiten, en vez de silencio.

Si más adelante alguien verifica el `resource_id` real de notarías o del CCT y su forma de
respuesta, entran con una prueba y el comentario de fuente y fecha, como las de hoy.

### Qué se queda fuera, y dónde

Tláloc (CURP con defunción, RFC), ApiMarket (REPUVE), INE, `codigos.zip`, y todo lo de convenio,
llave o pago. **No aparecen en la sección**; se registran en `APIS_CON_TOKEN` con la nota
«propuesta pendiente de convenio», para que un Diccionario que escriba «REPUVE» produzca `API-05`.

### Sinónimos

`SINONIMOS` crece con lo que un Diccionario escribe de verdad, no con claves técnicas: «curp»,
«código postal», «cp», «colonia», «municipio», «estado», «notaría», «escuela», «cct». Se resuelve
sin acentos ni mayúsculas, como todo lo demás en el extractor.

---

## D — la sección «Catálogos»

- **Menú lateral**: ítem «Catálogos», alcanzable **sin expediente cargado** (como Insumos). No es
  un paso del proceso, es referencia; va separado de los cuatro pasos.
- **API**: `GET /api/v1/catalogos` devuelve el registro emitible: clave, proveedor, tipo, URL,
  sinónimos que lo activan, y para las consultas los campos que devuelven. **No devuelve** los de
  `APIS_CON_TOKEN`.
- **Vista**: una tabla, solo lectura. Columnas: proveedor · qué hace (catálogo / consulta) · URL ·
  palabras del Diccionario que lo activan. Arriba, una línea que dice cuántos conoce el compilador
  y que los que exigen credencial no se listan porque se configuran en la plataforma.
- **Nada se llama en vivo desde aquí.** Eso es C.

---

## Pruebas

**A**: una prueba por entrada nueva (tipo, URL, sinónimo que la resuelve); una que fija que
ninguna clave de `APIS_CON_TOKEN` está en el registro emitible; una que fija que SIPUBEH es
`consulta` y declara sus tres campos.
**D**: `test_api.py` para el endpoint (devuelve las emitibles, no devuelve las de token);
`NavegacionLateral.test.tsx` fija que «Catálogos» se alcanza sin sesión; la vista con su prueba
de render sobre una respuesta fija.

---

## C, E, B, F — lo que ya se sabe, para no perderlo

**C — simulador.** Ya existe `conectarCatalogos` y llama `catalogo_url` en vivo. Falta: (1)
emitir el campo `api_ajax` para las consultas (forma en el acta del 2026-09-22), (2) que el
simulador lo ejecute con el mismo `blur` y enseñe la respuesta cruda al lado, para que el analista
vea si el endpoint contesta antes de importar. Depende de que Simplificación decida si parten
`@@nombre_propietario` en tres.

**E — historial.** Hoy el `.gpm` se genera al descargar y no se guarda. Decisión pendiente:
guardar cada descarga (crece el disco, hay trazabilidad) o solo la última por sesión. Propuesta:
cada descarga, con fecha en el nombre, dentro de la carpeta de la sesión; el historial las lista.

**B — selector.** Cuando `API-01`/`API-03` no resuelven, un control en la tarjeta que ofrece el
registro emitible, como el selector de campo de `DIC-08`.

**F — consulta.** Diseño aparte. Restricción fija: las tarjetas no entran al repo. Las leyes son
públicas y pueden empaquetarse.
