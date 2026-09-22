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
