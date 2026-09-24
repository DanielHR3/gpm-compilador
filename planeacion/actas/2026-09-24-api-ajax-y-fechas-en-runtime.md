# Acta — autollenado por CURP (`api_ajax`) en runtime, y por qué se perdían las fechas

- **Fecha:** 2026-09-24
- **Dónde:** `modelador.hidalgo.gob.mx` (procesos **1107** y **1108**, importados el 2026-09-24
  desde `.gpm` del compilador) y `tramites.hidalgo.gob.mx` (portal del ciudadano, trámite
  **48410** iniciado sobre el proceso 1108).
- **Quién:** el usuario hizo los dos logins; el agente operó el navegador. La CURP usada es la
  del propio usuario, con su autorización expresa.
- **Qué NO se hizo:** no se envió el formulario del ciudadano (el trámite 48410 quedó en
  borrador) y no se guardó ningún campo en el diseñador del modelador.

Material: el expediente de prueba (`Análisis AS-IS.md`, `Propuesta TO-BE.md`,
`Diccionario de Datos.md` con columnas Dependencia y Endpoint / API) compilado a
`prueba-api-ajax-curp.gpm` (→ 1107) y `prueba-api-ajax-curp-publico.gpm` (→ 1108, `ruts.publico`).

---

## Resultado 1 — el `api_ajax` que emite el compilador funciona en runtime

En el portal, proceso 1108, pantalla «Datos personales»: se escribió `HERD880823HHGRBN08` en
**CURP** y se salió del campo con Tab. A los pocos segundos:

| Campo | Llenado con | Clave de SIPUBEH |
| --- | --- | --- |
| Nombre(s) | `DANIEL` | `nombres` |
| Apellido Paterno | `HERNANDEZ` | `apePat` |
| Apellido Materno | `RUBIO` | `apeMat` |
| Sexo | `H` | `sexo` |

El portal dibuja además, por su cuenta, un botón de lupa junto al campo CURP para relanzar la
consulta. No lo emite el compilador.

En la misma pantalla se confirmó otra vez la cascada INEGI: al elegir **Hidalgo (13)** en Estado,
Municipio se pobló con los 84 municipios (`Acatlán=13001`, `Acaxochitlán=13002`, …).

Antes, en el modelador, el export del proceso 1108 devolvió el `extra` del `api_ajax`
**idéntico byte a byte** al emitido: el importador no lo toca.

## Resultado 2 — la receta del `api_ajax` (la forma que sí funciona)

Es la forma del `api_curp_trigger` de `acceso-informacion-publica.gpm`, que ahora está probada
en runtime y no solo leída de un export. Un campo `api_ajax` **aparte**, colocado justo después
del campo que lleva el dato. (El que corrió en 1108 traía además `@@fecha_nac_prueba`←`fechaNac`;
se quita aquí porque la fecha no se autollena, ver Resultado 5.)

```json
{
  "attributes": "",
  "url": "https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn",
  "request": "get",
  "campos": ["curp"],
  "valores": ["@@curp_prueba"],
  "tipo": ["si"],
  "prefijo": "data",
  "get_campos": ["@@curp_prueba"],
  "get_tipo": ["input"],
  "get_valores": ["blur"],
  "get_value_campos": ["@@nombres_prueba", "@@paterno_prueba", "@@materno_prueba", "@@sexo_prueba"],
  "get_value_tipo": ["input", "input", "input", "input"],
  "get_value_valores": ["nombres", "apePat", "apeMat", "sexo"]
}
```

Reglas que no se negocian, cada una con su porqué:

1. **`url` sin query.** El parámetro va aparte: `campos` = nombre del parámetro (`curp`),
   `valores` = de dónde sale (`@@campo`), `tipo: "si"` = «variable de la misma vista».
2. **`prefijo` = el nodo de la respuesta** (`data` en SIPUBEH). La plataforma lee
   `respuesta.data.<clave>`; por eso `get_value_valores` lleva la clave **sin** el prefijo.
3. **Disparo:** `get_campos` = el mismo `@@campo` de la CURP, `get_tipo: input`,
   `get_valores: blur` (al salir del campo).
4. **Destino:** `get_value_campos[i]` recibe `get_value_valores[i]`. Las tres listas
   `get_value_*` van del mismo largo y `get_value_tipo` siempre `input`.
5. **Sin `tamano`.** El export auténtico no lo trae en este componente.
6. **Los campos destino son `text` normales** de la misma vista; no se marcan de solo lectura
   por el autollenado. **Nunca una fecha** (ver Resultado 5): el selector del portal no tiene
   nombre y el dato no llega.
7. **Solo endpoints públicos.** La llamada sale del navegador del ciudadano (SIPUBEH responde
   con CORS `*`). Uno que exija token es `API-05` y va a una Acción PHP.
8. **Nombre técnico del campo `api_ajax`:** `api_curp_<pantalla>`, capado a 30.

En código: `extractores/diccionario._armar_autollenado` decide qué campos se conectan (API-06
`por_confirmar` cuando se arma, API-04 cuando falta la CURP o una clave no tiene mapeo) y
`compilador/a_gpm._campo_gpm` emite el `extra`. Las pruebas que lo fijan:
`test_el_api_ajax_sale_igual_que_en_el_export_autentico` y
`test_un_api_ajax_sin_curp_o_sin_endpoint_conocido_no_se_emite_roto`.

## Resultado 3 — las fechas: la plataforma ya no reconoce el tipo `date` (PLAT-12)

**Síntoma.** Todo campo `date` desaparecía al importar, **sin error**: el proceso 1068
(reingeniería del 2026-09-02) perdió sus tres fechas y 1107/1108 perdieron `fecha_nac_prueba`.

**Causa, vista en la plataforma.** El diseñador de vistas agrega campos con
`agregarCampo(<formulario>, <tipo>)`, que carga `backend/formularios/ajax_agregar_campo/<f>/<tipo>`.
Pedido directamente (un GET, no guarda nada):

| Tipo pedido | Respuesta |
| --- | --- |
| `date` | **500** — `Exception: Tipo de campo no reconocido: date` (`/app/application/models/Campo.php:301`) |
| `fecha`, `time`, `calendar`, `datepicker`, `date_picker` | 500, mismo mensaje |
| `date_time`, `datetime` | 200 — formulario **«Edición de fecha / hora»** con `tipo` oculto = `date_time` |

El propio botón **Texto → Fecha** del diseñador llama a `agregarCampo(…,'date')` y abre un
modal vacío: la plataforma tiene roto su propio botón. El importador tropieza con la misma
excepción y descarta el campo.

Los 16 campos `date` de los exports de referencia (p. ej. `pago-de-bases-licitaciones.gpm`,
`busqueda-de-testamento-v2.0.gpm`) son de la versión anterior de la plataforma: esquema de 18
claves por campo, contra las 25 de hoy. En ningún archivo disponible hay un `date_time`.

**El formulario «Edición de fecha / hora»** publica en `extra`, en este orden:
`destacar` (solo si se marca), `tamano`, `attributes`, `subtype` (radio `date` | `time`,
**`date` marcado por omisión**), `data_format`, `data_format_unique` (oculto, vacío),
`validateDate` (solo si se marca) y `valid_date` (radio `future_date` | `past_date`, solo si se
elige).

**Arreglo en el compilador.** Un campo `date` o `date_time` del manifiesto sale como:

```json
{"tipo": "date_time",
 "extra": {"tamano": "col-xs-12 col-md-6", "attributes": "", "subtype": "date",
           "data_format": "", "data_format_unique": ""}}
```

El manifiesto sigue diciendo `date` (qué se quiere); solo el compilador traduce al tipo de la
plataforma (cómo se escribe). No existe subtipo de fecha **y** hora, así que `date_time` del
manifiesto toma el valor por omisión del formulario. Red de seguridad: el validador marca
**`EST-08` (bloqueante)** en todo `.gpm` que traiga un campo `date`.

## Resultado 4 — el arreglo importa y la fecha llega al portal (PLAT-12 cerrado)

`prueba-fechas-date-time.gpm` (compilado con el arreglo, validador limpio) se importó como
proceso **1110**. El export devolvió `fecha_nac_prueba:date_time` con el `extra` **idéntico** al
emitido (`tamano`, `attributes`, `subtype: date`, `data_format`, `data_format_unique`), y los
flags `public`/`add_in_menu`/`is_active` en `1`.

En el portal (trámite **48423**, sin enviar) el campo **Fecha de Nacimiento** aparece con su
selector y el marcador `dd-mm-yy`. Es el primer campo de fecha de un `.gpm` del compilador que
llega vivo al ciudadano.

## Resultado 5 — el autollenado NO alcanza un campo de fecha

En el mismo trámite 48423, CURP + Tab llenó otra vez nombres, apellidos y sexo, pero **la fecha
quedó vacía**. El portal dibuja el selector de fecha como un componente propio: su `<input>` no
lleva `name` ni `id`, y no existe en la página ningún elemento `fecha_nac_prueba`. El `api_ajax`
escribe por nombre, así que no tiene dónde dejar `fechaNac`.

**Consecuencia en el compilador.** `diccionario._armar_autollenado` ya no conecta un campo
`date`/`date_time` al autollenado aunque el Diccionario lo marque «autorellenable»: lo deja de
captura manual y lo reporta como `API-04` (`por_confirmar`), diciendo que es un selector de fecha
que el autollenado no alcanza. La regla 9 de la receta: **los destinos del `api_ajax` son solo
campos de texto**.

## Lo que queda

- **Limpieza.** Procesos de prueba **1107, 1108 y 1110**, y los trámites **48410** y **48423** en
  borrador en la cuenta del usuario: se borran cuando el usuario lo decida
  (`/backend/procesos/eliminar/<id>`; los trámites quedan huérfanos, el portal no los borra).
- Si algún día hiciera falta la fecha autollenada, el camino sería una Acción PHP en el servidor,
  no el `api_ajax`. Nadie lo ha pedido.
