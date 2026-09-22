# Pendientes — estado verificado

Última verificación: 2026-09-21, suite en **533 passed, 23 skipped** (servidor) y **235
passed** (interfaz).

Este archivo solo registra lo que se comprobó ejecutando código o importando a la
plataforma. Una afirmación sin evidencia aquí vale menos que nada: hace que alguien deje de
buscar.

---

## Resueltos, verificados

| | Hallazgo | Cómo se comprobó |
|---|---|---|
| **P-01** | Los nombres de tarea arrastraban la anotación del TO-BE | El TO-BE de Testamento produce `'Capturar el Formato de Aviso de Testamento directamente en GPM, a distancia'` — sin el `*(Tarea GPM #7920…)*` |
| **P-04** | `i_comp` caía posicionalmente en la columna `Dependencia` y ganaba sobre el tipo declarado | Un híbrido con `Dependencia = fecha_nac` y `Tipo (GPM) = select` ahora emite `select`. Antes emitía `date` |
| **P-05** | `extraer()` tenía dos ramas casi gemelas de ~60 líneas | Extraído `_extraer_campos(filas, pantalla, r)`; el archivo pasó de 330 a 289 líneas y ya no hay dos cuerpos paralelos |
| — | El enlace de Aprobación reintrodujo `target="_blank"` | `test_revision_enlaza_al_simulador_en_la_misma_pestana` pasó de rojo a verde el 2026-08-29 |
| **PLAT-1** | Un `select` manual con solo `catalog_type` reventaba al importar (`CampoSelect.php:468`) | **Importado a la plataforma** (proceso 1046, 2026-08-31): el error desapareció al emitir las cuatro claves. Ver `actas/2026-08-30-prueba-en-plataforma.md` |
| **PLAT-2** | `key_object` con espacio → la plataforma buscaba una clave inexistente | **Importado**: `estado_sol` cargó los 32 estados con `Hidalgo=13` correcto al quitar el espacio |
| **P-02** | El simulador dibujaba `<input>` para un `select` sin opciones | Fase A: un `select` sin catálogo resoluble sale `<select disabled>`. `test_un_select_sin_catalogo_resoluble_sale_deshabilitado` en verde |
| **PLAT-5** | Nombres largos (`formulario.nombre`, `campo.nombre`) tumbaban el import con `Data too long` | **Prueba de punta a punta del expediente REAL de Testamento**: tras capar nombres (60 para forma/tarea, 30 para campo derivado) la plataforma importó sin error y reconstruyó 9 formularios, 10 tareas, 46 campos y 9 conexiones — exactamente lo emitido. Cuarta prueba en `actas/2026-08-30-prueba-en-plataforma.md` |
| — | ¿El compilador sirve para *crear* `.gpm` importables? | **Sí, verificado en la plataforma el 2026-08-31**: expediente real → `.gpm` → import completo → export de vuelta con los mismos conteos |
| **PLAT-3** | La cascada estado→municipio no se había probado en el runtime del ciudadano | **CONFIRMADA en el portal** (`tramites.hidalgo.gob.mx`, expediente real, 2026-08-31): al elegir "Hidalgo" salió `GET .../mgem/13` → 200 y Municipio se pobló con los municipios reales. La plataforma interpola `@@estado_sol`→`13`. Sexta prueba del acta |
| **PLAT-6** | `add_in_menu` hardcodeado en `0`: un trámite `publico:true` no aparecía en el portal | Los 12 exports mueven `public` y `add_in_menu` juntos. Atado `add_in_menu` a `publico`; tras recompilar, el trámite entró al catálogo del portal (132→133). `test_publico_activa_public_y_add_in_menu_juntos` en verde |
| **PLAT-4** | `php_folio` hardcodeaba un `proceso_id` que la plataforma reasigna al importar → folio roto | **Causa raíz:** el esquema `proceso_folio`/`proceso_id` fue inventado. Los dos exports con folio (`constancia-ambiental`, `pago-de-bases`) llavean el contador por el **nombre de la variable** en `dato_seguimiento`.`valor`, con `lockForUpdate` y sin `proceso_id`. `php_folio` emite ahora esa forma; `FOLIO-02` la exige; el invariante de `CLAUDE.md` corregido. Importa y corre en runtime sin el fallo. (Nota: no se reproduce el `// Fixed Race Condition` del export — en una línea comentaría el `return`.) |
| **P-03** | Sin AS-IS el nombre caía al de la carpeta y se filtraba al archivo y al `proceso_id` | La portada del asistente web ya pedía el nombre (`web/app.py`); se añadió `gpmc extraer --nombre` para el mismo camino en la CLI. `test_extraer_nombre_sobrescribe_el_del_expediente` en verde |
| **SINTAXIS_ESTRICTA** | ¿La forma simple `@@campo=='valor'` falla con campos complejos? | **REFUTADO con prueba en la plataforma** (séptima prueba del acta): `@@procede=='si'` sobre un `select` hizo avanzar el flujo en el runtime del ciudadano, y cuatro trámites de producción publicados usan esa forma sobre selects. La constante se queda en `False` |
| — | `cli compilar --proceso-id` fijaba `"900"`, inconsistente con el web | Por omisión ahora deriva del nombre, como el web. La plataforma lo reasigna igual (PLAT-4) |
| — | Ninguna prueba cruzaba Diccionario → extractor → estimador (dejó pasar el bug de `origen`) | `test_de_punta_a_punta_diccionario_extractor_estimador`: un endpoint en el Diccionario llega a `estimador.integraciones` |
| — | `ejemplos/` no traía ningún `select`: la serialización de ese camino no se ejercitaba | `ejemplos/vinculacion-organismos` trae un select con catálogo remoto y su cascada; `test_el_ejemplo_ejercita_la_serializacion_de_un_select_remoto` en verde |

## Lote de reingeniería 2026-09-02 y trabajo posterior (verificado)

| | Hallazgo | Cómo se comprobó |
|---|---|---|
| **PLAT-7** | El nombre `@@` declarado por el analista pasaba entero; `Data too long for column 'nombre'` al importar (Prórroga, 38 chars) | El extractor capa las tres rutas a 30 y reporta `DIC-06`; el validador marca `EST-05` (bloqueante). 6 `.gpm` reimportados (procesos 1068-1073). Commit `16dc52c` |
| **PLAT-8** | `select`/`radio` sin opciones → `Invalid argument supplied for foreach()` en las vistas | Parser de catálogo ampliado (coma, ` / `, `<br>`, envoltura `(catálogo: …)`, Boolean con `Sí-No` en Límite → `{Sí, No}`); piso: sin opciones/endpoint/padre → texto (`DIC-07`, `EST-06`). Commit `16dc52c` |
| **PLAT-9** | `Selector de fecha (calendario)` clasificado como `select` porque «select» es subcadena de «selector» | `selector de fecha`/`calendario` → `date`. Commit `16dc52c` |
| **blindaje** | Los Diccionarios viejos escriben el proveedor (`INEGI`, `SEPOMEX`) en la columna Endpoint; catálogos en cascada sin campo padre | Mapa `SINONIMOS` en `integraciones.py`; el `select` se degrada a texto si el endpoint no resuelve (`API-01`) o es cascada sin padre (`API-03`). `Constancia Vehicular` y `Poda de Árboles` validan sin bloqueantes. Commits del 2026-09-04, `04382c9` |
| **INS-04** | Nada avisaba si se subían insumos de trámites distintos por error | `expediente.py` compara los títulos H1 de AS-IS/TO-BE/Diccionario por intersección de palabras. Commit `b259ffb` |
| **EST-07** | `Estado Civil` de Testamento compiló `('Soltero        casado', 'Divorciado  Viudo', 'Unión Libre')` — 3 opciones basura — **sin un solo hallazgo** | `_despegar` parte una corrida de 2+ espacios/tabs dentro de una opción; el validador marca `EST-07` (aviso). Re-extraer Testamento da 5 opciones y valida limpio; el `.gpm` viejo del lote ahora marca `EST-07` ×2; los otros 5 del lote sin falsos positivos. Commit `038cd90` |
| **FLU-01 (primer corte)** | El flujo salía siempre lineal | `expediente.py` intenta un flujo ramificado desde el Mermaid solo si los nombres de tarea casan exactamente con las pantallas y el conteo coincide; ante cualquier compuerta, degrada a lineal y mantiene `FLU-01`. Commit `b259ffb`. **Ramificación completa: pendiente de spec propio + prueba en plataforma** (ver `docs/superpowers/specs/2026-09-03-linter-y-ramificacion-design.md` Parte 2) |

## Abiertos

- **P-24 — el servidor vive en una laptop y la liga cambia de IP cada vez que se reconecta.**
  Tres cambios en dos dias (`.215` → `.220` → `.215` → `.220`); cada uno obliga a reenviar la
  liga y a regenerar el PDF de la guia. Pedido el 2026-09-22 por el usuario: «empezar a pensar
  en subirlo a algun lugar». Lo que hay hoy: un agente `launchd` en la Mac
  (`despliegue/local.gpmc.servidor.plist`), sin Docker, sin `systemd`, sin nombre DNS.
  Lo que la app necesita del sitio que la reciba —medido, no supuesto—: Python ≥ 3.9 con
  `pydantic` y `pyyaml` (el resto es opcional: FastAPI/uvicorn para servir, el SDK de Gemini
  solo si hay llave); **ninguna base de datos**: el estado son carpetas de sesion en disco con
  purga a 7 dias; un solo proceso; el frontend va compilado (Node solo en el build, no en
  runtime; `GPMC_FRONTEND_DIST` apunta al `dist/`); logs con rotacion ya resueltos
  (`GPMC_LOG_*`); salida a internet **desde el servidor** unicamente hacia Gemini (si se
  activa la Fase 2); los catalogos publicos (INEGI, SEPOMEX, SIPUBEH) los pide **el navegador
  del analista**, asi que su maquina tambien necesita salida. **No hay login**: hoy lo abre
  cualquiera en la red. Restriccion que no se negocia: los expedientes llevan datos de
  ciudadanos —el 22-sep aparecio un certificado escaneado con placa y serie de un vehiculo
  real dentro de una plantilla— asi que **tiene que quedar dentro de la red de gobierno**,
  no en una nube publica ni detras de un tunel. Depende de P-22 (el codigo se desplegaria
  desde Bitbucket, no desde la cuenta personal). Opciones, de menor a mayor esfuerzo:
  (a) nombre DNS interno o IP fija para esta Mac —ya pedido a Infraestructura; no arregla que
  la Mac se apague—; (b) una VM Linux de la DGT con `systemd` + `nginx` + nombre interno, que es
  el destino para el que se diseno la SPA; (c) imagen Docker como forma de entrega para (b).
  **Sin decidir. Primer paso concreto cuando se decida:** escribir la ficha de despliegue para
  Infraestructura con esta lista y el `systemd`/`Dockerfile` equivalentes al `plist`.

- **P-23 — ninguna plantilla de documento de los expedientes reales trae `{{variables}}`.**
  Medido el 2026-09-22 sobre los dos expedientes del lote (`Archivo (1)`), las siete acciones
  de tipo `documento` tienen **cero** marcas `{{...}}` y `variables: []`:

      62 palabras   1004 chars  (1) Formato de Solicitud de Reposicion
       1 palabras    128 chars  (5) Repocision de Certificado en el formato establecido
       0 palabras     28 chars  (1) Solicitud de Ampliacion y o Prorroga
     140 palabras   1708 chars  (3) Oficio de Prorroga con termino establecido
     181 palabras   2163 chars  (4) Oficio de Rechazo de Prorroga
     136 palabras   1668 chars  (5) Oficio de ampliacion de Verificacion
     181 palabras   2163 chars  (6) Oficio de Rechazo de Ampliacion

  Consecuencias: (a) el documento que emite la plataforma sale **igual para todos los
  ciudadanos**, sin un solo dato del tramite; (b) por eso el simulador **no puede** ensenar un
  PDF relleno con lo que el analista capturo: no hay donde meterlo. Las tarjetas del simulador
  ensenan la plantilla tal cual y marcan las dos rotas —una es una fila de rayas, la otra son
  las columnas de un certificado escaneado con datos reales de un vehiculo (placa y VIN)—.
  **Decision pendiente del usuario:** si esto se le devuelve a Simplificacion como observacion
  (las plantillas hay que redactarlas con `{{campo}}`) o si se acepta que los documentos salgan
  en blanco para que el funcionario los llene a mano. Relacionado: `DOC-03`, `DOC-04` y P-19.
  **Decidido el 2026-09-22 por la tarde: se devuelve a Simplificacion.** Mensaje en
  `docs/guias/Mensaje a Simplificacion - las plantillas de los documentos.md`, con un antes/despues
  del oficio de Prorroga y la plantilla de Reposicion reescrita con los campos que ya existen
  (las once variables citadas se verificaron contra los dos Diccionarios). Enviado el mismo dia.
  **Esperamos su respuesta.** De paso salieron tres datos que el formato en papel pide y el
  Diccionario no captura (centro expedidor, semestre/fecha de expedicion, numero de oficio).

- **PLAT-11 — nombramos el grupo con una etiqueta legible, no con el identificador real.** El
  extractor toma el nombre del carril del TO-BE y lo emite tal cual: `Direccion De Verificacion
  Vehicular`. La plataforma usa **slugs**: `transparencia_admin`, `area_primer_contacto`,
  `licitaciones_admin`, `verificacion_vehicular`. Comparacion A/B sobre el MISMO tramite:

      Constancia de No Infraccion, hecha a mano:  ['verificacion_vehicular', 'grupo práctica']
      Constancia de No Infraccion, generada:      ['Direccion De Verificacion Vehicular']

  Consecuencia observada el 2026-09-22: las tareas del funcionario salen con `acceso_modo:
  grupos_usuarios` **apuntando a un grupo que no existe**, asi que la restriccion no ata y
  cualquiera puede llenarlas desde el portal del servidor publico. El usuario lo noto antes que
  nosotros.

  **Necesita una decision de alcance:** el catalogo de grupos vive en la plataforma y el
  compilador no lo conoce. O se pide como hueco al analista, o se mantiene un mapa de
  equivalencias, o se deja el nombre y se documenta que hay que reasignarlo tras importar. Hoy no
  se avisa de nada.
- **PLAT-10 — `init_capture` iba fijo en "0" y el portal rechazaba el arranque.** La plataforma
  contesto **403 «Usuario no puede iniciar este proceso»** al intentar arrancar Prorroga desde
  `tramites.hidalgo.gob.mx` (2026-09-21). `esquema.tarea` emitia `init_capture: "0"` para TODAS
  las tareas. En los catorce exports autenticos la tarea inicial lleva **siempre** `"1"`; el unico
  `"0"` con `inicial` esta en los dos tramites que declaran una segunda inicial alternativa.
  Emitir `"0"` en la unica inicial es una forma que no aparece en ningun tramite que funcione.
  **Corregido el mismo dia.** Falta la confirmacion en plataforma: reimportar y comprobar que el
  ciudadano puede arrancarlo. Hasta entonces no se da por cerrado.

- **P-06 — los catálogos se parten por coma sin respetar los paréntesis.** `$226.00 (fijo, Ley
  Estatal de Derechos Art. 40 Fracción V)` sale como **dos** opciones de catálogo. El `.gpm`
  lleva datos inventados y **no se emite ningún hueco**: nadie se entera. Verificado en código
  el 2026-09-21 (`extractores/diccionario.py:312` y `:392`). Determinista y fácil de probar;
  es el trabajo inmediato siguiente.
- **P-07 — un `select` con catalogo manual Y endpoint emite una forma que no existe.** Comprobado
  el 2026-09-21 emitiendo el `.gpm`: el campo sale con `catalog_type: "url"`, su `catalog_url` y
  ademas `datos` con las opciones manuales. En los exports autenticos, el select manual lleva
  `datos` y los remotos **no traen esa clave en absoluto**; la combinacion no aparece en ninguno,
  y la regla del proyecto es no emitir formas no observadas. Ademas las opciones manuales se
  quedan sin decir nada, cuando el invariante es «propone, no adivina». Viene del encargo de
  revision del 2026-08-30, Tarea 2. **Necesita una decision**: el codigo de hueco libre siguiente
  ya no es `API-05` —esta ocupado por el endpoint autenticado—, asi que seria `API-06`.
- **P-13 — «max. N caracteres» se emite como longitud EXACTA. Lo mas urgente de la lista.**
  `_LONGITUD = r"(\d+)\s*caracteres"` toma el numero y no mira si delante decia «max.». En
  Prorroga salen **once campos** asi: `razon_social_institucion` exige exactamente 150 caracteres
  cuando el Diccionario dice «max. 150», y una razon social de 40 no se puede capturar. Rompe el
  tramite en produccion y ninguna prueba nuestra lo veia. El reverso del mismo patron: «exactamente
  4 digitos» de `modelo` no se lee, porque exige la palabra «caracteres». Lo destapo el analisis de
  Simplificacion del 2026-09-21, que lo reporto como un detalle.
- **P-14 — «Condicional» en la columna Obligatorio se lee como «No».** `obligatorio` sale de
  `_babel(celda).startswith("si")`, asi que los 7 campos condicionales de Prorroga salen
  opcionales. **La plataforma si sabe expresarlo**, comprobado en los exports autenticos: un campo
  condicional lleva `validacion: "required"` JUNTO con su `dependiente_campo`. Esta asi en cuatro
  tramites publicados.
- **P-15 — la `ayuda` de los campos va vacia siempre.** El modelo `Campo` tiene el atributo y la
  plataforma lo usa para el texto de apoyo que ve el ciudadano. En Prorroga: **0 de 36 campos**
  con ayuda. El Diccionario trae una Descripcion por campo y una columna «Ejemplo Real» que no
  leemos: es ayuda ya redactada que se tira.
- **P-16 — tipos mal derivados y datos de archivo que no se leen.** En Prorroga `fecha_vigencia`
  sale `text` en vez de `date` y `doc_oficio_resolucion` sale `text` en vez de `file`. Y de los
  campos de archivo no se lee el formato admitido, el tamano maximo ni la carga multiple.
- **P-17 — todo `.gpm` que emitimos sale OCULTO del portal del ciudadano, y nadie lo dice.**
  `ruts.publico` nace en `False` y **ningun extractor lo pone nunca en `True`**: no hay una sola
  ruta que lo derive del AS-IS, del TO-BE ni del Diccionario. El compilador ata `public` y
  `add_in_menu` correctamente (PLAT-6), asi que el `.gpm` importa limpio, el funcionario ve el
  tramite en `admin.hidalgo.gob.mx` y el ciudadano **no lo ve en ningun lado**. Paso el
  2026-09-21 con Prorroga: se importo, se veia del lado del funcionario y no aparecia en
  `tramites.hidalgo.gob.mx/panel/dashboard`.
  Faltan dos cosas: derivarlo del expediente cuando se pueda, y **decirlo** —hoy no hay hueco
  que avise de que el tramite saldra invisible—. Mientras tanto se corrige a mano en el
  manifiesto (`publico: true`) o en la plataforma.
- **P-19 — todos los documentos se generan al enviar la solicitud del ciudadano.** Comprobado en
  plataforma el 2026-09-22 (proceso 1103): los **cinco** oficios de Prorroga cuelgan de «Nueva
  Solicitud» con `instante: "despues"`. En cuanto el ciudadano envia, se generan a la vez el
  oficio de prorroga, el de ampliacion y los **dos de rechazo**, antes de que nadie decida nada.

  La forma autentica es otra: la accion es un objeto suelto y el enganche vive en los `Eventos`
  de la tarea. En `constancia-de-no-infraccion` (misma direccion, hecha a mano) `crear-folio`
  cuelga de la tarea del ciudadano y **`generar-constancia-pdf` cuelga de la tarea de validacion
  del funcionario**.

  **No es silencioso** —se emiten cinco `DOC-04` diciendo «se genera al terminar la tarea Nueva
  Solicitud, la primera en la que...»— pero el nivel es `por_confirmar`, o sea que no bloquea, y
  el valor por omision es indefendible: elegir la primera tarea con campos es adivinar, y adivina
  mal siempre que el documento dependa de una decision.

  **Propuesta, a decidir:** subir `DOC-04` a `falta_dato` y darle control en la pantalla para
  elegir la tarea. Cambia la puerta del linter —un tramite con documentos dejaria de poder
  descargarse hasta asignarlos—, y por eso no se hace sin aprobacion.
- **P-22 — el repositorio vive en una cuenta personal de GitHub y es publico.** Decision del
  usuario el 2026-09-22: se migrara a **Bitbucket** de la Direccion; hoy esta en
  `github.com/DanielHR3` por como nacio el proyecto.

  **Consecuencia mientras tanto:** todo lo que se comitea es publico en el momento del push. Ya
  obligo a parafrasear la descripcion de `SEG-04` (2026-09-21), y ahora condiciona la seccion de
  consulta que se pidio: las **tarjetas informativas son de uso exclusivo de la DGT** hasta que un
  mando superior las solicite, asi que no pueden empaquetarse con el asistente.

  **Regla que conviene mantener incluso despues de migrar:** el material reservado se lee del
  disco de la maquina, fuera del repo, como ya se hace con las sesiones y el registro. Si el repo
  cambia de sitio o se clona, lo reservado no viaja con el.
- **P-21 — el catalogo de endpoints: hecha la mitad automatica (A) y la seccion (D), 2026-09-22.**
  El registro distingue `catalogo` de `consulta`; los sinonimos resuelven lo que un Diccionario
  escribe («CURP», «Codigo Postal», «colonia», «municipio»); lo de pago, llave o convenio queda
  registrado como propuesta y produce `API-05` con nombre; `GET /api/v1/catalogos` y la seccion
  «Catalogos» del asistente lo enseñan. **Sigue pendiente B**, el selector en la tarjeta cuando
  el extractor no puede decidir. Lo que sigue aqui abajo es el texto original, que explica la
  medicion:

- **P-21 (original) — el catalogo de endpoints se queda corto frente al de la Direccion.** `integraciones.py`
  conoce **4** catalogos (mgee, mgem, zip_codes, consultacurpn). El «Catalogo Maestro de APIs para
  Tramites Gubernamentales» de la boveda (2026-08-11) documenta **38 APIs, 21 con endpoint**, casi
  todas oficiales y gratuitas: REPUVE, CFDI del SAT, padron de notarias, CCT de escuelas, COFEPRIS,
  cedula profesional, codigos postales alternos.

  Lo que pidio el usuario el 2026-09-22: **que se puedan seleccionar, o ponerse automaticamente**.
  Dos mitades distintas:
  - *Automatico*: ampliar `CATALOGOS` y `SINONIMOS` para que un Diccionario que escriba «REPUVE» o
    «CURP» resuelva solo. Es lo barato y no necesita interfaz.
  - *Seleccionable*: cuando el extractor no puede decidir, ofrecer la lista al analista en la
    pantalla, como ya se hace con el campo de `DIC-08`. Necesita control nuevo.

  **Cuidado al ampliarlo:** las cuatro entradas de hoy salen del export autentico, o sea que son
  las que GPM usa de verdad. El catalogo de la Direccion es una referencia mas amplia y trae
  endpoints que la plataforma no ha usado nunca, y otros de pago (Tlaloc, ApiMarket) que van a
  `API-05` por el invariante. No sustituir una URL observada por una del documento sin prueba.

- **P-20 — el autollenado por CURP se puede emitir, y nuestra URL no coincide con la autentica.**
  La «cuestion abierta» de `CLAUDE.md` (`Api variable` frente a `api_ajax`) **queda contestada el
  2026-09-22**: la captura del disenador de la plataforma muestra **«Api ajax» y «Api variable»
  como dos entradas distintas** del catalogo de Scripts. Son componentes distintos, asi que el
  invariante que prohibe `Api variable` NO cubre `api_ajax`.

  Ademas `api_ajax` esta **observado**: 7 campos en 3 exports autenticos, todos el mismo
  `api_curp_trigger`. Y no toca RENAPO directo: llama a **SIPUBEH**, que responde sin credencial
  (verificado el 2026-08-28), asi que no hay `SEG-04` que lo impida.

  **Pero la URL que tenemos registrada no es la que se usa:**

      nuestra:   https://sipubeh.hidalgo.gob.mx/api/consultacurpn/@@{padre}
      autentica: https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn   (GET, param `curp`)

  La forma autentica es un campo aparte, `tipo: api_ajax`, que se dispara con `blur` sobre el
  campo de la CURP y escribe en tres campos: `nombres`, `apePat`, `apeMat`.

  **Confirmado en la plataforma el 2026-09-22** (acta
  `actas/2026-09-22-componentes-de-script-en-el-modelador.md`): el panel Scripts lista
  `Javascript`, `Redireccion`, `Api ajax` y `Api variable` como **cuatro entradas distintas**, y
  el formulario de *Api ajax* —titulado «Edicion de Web service Ajax»— mapea uno a uno con el
  `extra` del export autentico.

  **Decision pendiente antes de implementar:** el Diccionario de Prorroga declara UN solo campo
  `@@nombre_propietario` y SIPUBEH devuelve los tres por separado. O se parte en tres, o se
  escribe solo `nombres`. Eso lo decide Simplificacion.
- **P-18 — una integracion descrita en prosa no se detecta, y no se reporta.** El extractor busca
  integraciones solo en columnas dedicadas (`Dependencia`, `Endpoint / API`). El Diccionario de
  Prorroga no las tiene: documenta la consulta en la Descripcion —«Dispara la consulta a RENAPO
  que autocompleta el nombre», «[Solo lectura, autocompletado por RENAPO]»—. Medido el
  2026-09-22: **0 huecos `API-*` emitidos** y los dos campos sin `endpoint`. En la plataforma el
  autocompletado simplemente no existe y nada lo dijo.

  Ojo con el arreglo: detectarlo NO significa emitirlo. RENAPO pide credencial, asi que sigue
  siendo `API-05` —se resuelve con una Accion PHP del lado del servidor— por el invariante de
  `CLAUDE.md`. Lo que falta es **enterarse y avisar**, que es justo lo que ese invariante promete
  y hoy no cumple cuando la integracion viene en prosa.
- **P-11 — las Notificaciones del Diccionario no se leen, y ni siquiera se reportan.** La
  «Seccion 3 — Notificaciones» documenta pantalla, evento que la dispara, destinatario, medio y
  contenido del mensaje: exactamente lo que necesita el arquetipo `notificacion`. Medido el
  2026-09-21 sobre Reposicion de Certificado: **8 notificaciones documentadas, 0 emitidas**, y
  **ningun hueco** lo dice. Es una perdida silenciosa, que es la clase de defecto contra la que
  existe la regla de «propone, no adivina». Lo destapo un ejercicio del equipo de Simplificacion.
- **P-12 — la Ficha tecnica del Diccionario no se mira para los metadatos.** `metadatos.extraer`
  recibe solo el AS-IS y el TO-BE. En Reposicion emitimos `META-06` («no se encontro 'A quien va
  dirigido'») mientras su Ficha tecnica declara «Poblacion / usuario objetivo: Propietarios o
  poseedores de un vehiculo automotor que extraviaron o les robaron su certificado». Le pedimos a
  mano un dato que ya nos dieron. El patron `_DIRIGIDO` exige la forma `**A quien va dirigido:**`
  y no contempla la tabla de la Ficha.
- **P-09 — el compilador no emite Pasos en modo visualizacion.** De los 19 pasos de ese tipo que
  hay en los exports autenticos (8 de 12 trámites), nuestro compilador emite **cero**: el flujo
  sale en linea recta y cada pantalla se muestra una vez, en edicion. Es lo que Simplificacion
  documenta como «Vista de solo lectura (Origen → Destino)», y la forma de la plataforma es
  reutilizar la MISMA pantalla: en `acceso-informacion-publica.gpm` el formulario 9250 lo edita el
  ciudadano (tarea 1) y lo ve el funcionario en visualizacion (tarea 2). El manifiesto ya tiene la
  pieza —`PasoPantalla.modo` acepta `visualizacion` y `a_gpm` la emite—; falta que el extractor la
  derive del TO-BE. Ver `docs/guias/Respuesta a Simplificacion - vistas de solo lectura.md`.
- **P-10 — `is_reusable` se emite distinto a como lo hacen los exports (latente).** Nuestra regla
  es `is_reusable = (la pantalla se usa en mas de un paso)`. En los exports autenticos hay **11
  formularios usados por 2, 3 y hasta 4 pasos, y los once traen `is_reusable: "0"`**. O sea que
  reutilizar una pantalla NO es lo que activa esa clave. Hoy no se dispara porque nunca
  reutilizamos una pantalla (ver P-09), pero **se disparara en el primer tramite que lleve un Paso
  de visualizacion**, y seria una forma no observada. Arreglar junto con P-09, no antes.
- **P-08 — `POST /resolver` y el selector de la SPA aceptan un campo de nombre repetido.** Desde
  el 2026-09-21 `agentes/verificar.py` rechaza como `campo_ambiguo` una condicion que mira un
  nombre tecnico duplicado: ganaba el primer campo, y si ese no traia catalogo se aceptaba
  cualquier valor. La via manual sigue indexando por nombre y no lo comprueba, asi que vuelve a
  ser mas permisiva que la de la IA. De raiz se arregla en el extractor: el primer `@@` de una
  descripcion se lleva el nombre del campo (ocho duplicados en Reposicion de Certificado).
- **Revisar los seis expedientes del lote** con el arreglo del falso `DIC-02` puesto (una opción
  llamada «Pendiente de…» tumbaba el catálogo entero, `5228358`): puede haber varios huecos que
  desaparecen solos.
- **`FileResponse` no contesta `304`** ante un `If-None-Match`. Irrelevante en local con medio
  kilobyte; no lo sería en un servidor de verdad.

Notas que no son defectos de este repo:

- **Externo (otra sesión):** el proceso `1044` ("b5a8defd46ca96d2") de otro agente sigue en la
  plataforma. No es deuda de este compilador; se revisa/borra aparte con quien administra la
  plataforma. (Los demás procesos de prueba de estas sesiones ya se borraron; los expedientes
  que quedan huérfanos en la cuenta de prueba no tienen borrado del lado del ciudadano.)
- **Mejora opcional (no defecto):** ver con los ojos el **avance** del contador de folio exige
  un trámite con acción `documento` que imprima `{{folio}}` y dos expedientes. PLAT-4 ya está
  resuelto —emitimos la forma de dos trámites de producción y corre en runtime—; esto sería
  sólo evidencia visual del consecutivo.

*(Cerrado el 2026-08-31: los 8 scripts `fix_*.py` y los `dummy*.md` sueltos se borraron y
`.gitignore` ya los excluye. Fase A tiene spec y plan
—`planeacion/planes/2026-08-29-fase-A-apis-y-catalogos.md`— implementados y fusionados.)*

---

## Preguntas de plataforma — las tres CERRADAS al 2026-08-31

Documentadas en `actas/2026-08-30-prueba-en-plataforma.md`:

1. **¿Basta `catalog_type: "manual"` sin `catalog_url`?** **NO** — reventaba
   (`CampoSelect.php:468`). Arreglado y reconfirmado (PLAT-1).
2. **¿Acepta la plataforma un `proceso_id` ajeno?** **NO** — lo reasigna y no reescribe las
   referencias del PHP (PLAT-4). El folio se corrigió llaveando por variable en
   `dato_seguimiento`.
3. **`SINTAXIS_ESTRICTA`** — **PROBADA**: `@@campo=='valor'` evalúa sobre un `select` en el
   runtime del ciudadano; cuatro trámites de producción usan esa forma sobre selects. La
   constante se queda en `False`. Ver acta, séptima prueba.

## Menores — cerrados

- `_campo_gpm` ya llevaba anotaciones de tipo (la nota era vieja).
- Docstring de `_campo_gpm` actualizado: el fallo de `CampoSelect.php` ya no es hipótesis
  (confirmado en PLAT-1).
- `ejemplos/` ya ejercita un `select` (ver tabla de resueltos).
- `:::nota` sola ya estaba cubierta por el nodo N3 y `test_una_nota_se_reconoce_por_el_carril_sin_la_forma_de_barras`; además se añadió `test_la_forma_de_barras_gana_sobre_un_carril_real`, que fija que `[/.../]` gana sobre un carril real contradictorio (comportamiento intencional, ahora documentado en el código).
