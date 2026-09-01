# Pendientes — estado verificado

Última verificación: 2026-08-31, suite en **245 passed, 22 skipped**.

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

## Abiertos

**Ninguno bloqueante.** Todo lo del compilador quedó cerrado el 2026-08-31; la suite pasa en
245. Quedan sólo estas dos notas, que no son defectos de este repo:

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
