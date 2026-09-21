# Acta — el lote de reingeniería: nombres que desbordan y vistas que revientan

- **Fecha de los hechos:** 2026-09-02
- **Acta redactada:** 2026-09-21, a partir de la bitácora de esa jornada y de
  `planeacion/pendientes.md`. Se escribe tarde: quedó comprometida el mismo 2 de septiembre y
  no se había hecho. **No contiene nada que no estuviera registrado entonces**; lo que no quedó
  anotado se dice aquí como no anotado.
- **Material:** carpeta "EXPEDIENTES DE TRAMITES CON REINGENIERIA" entregada por el equipo de
  Simplificación — 7 expedientes, 6 con los tres insumos y uno vacío (IHM).
- **Corrección:** commit `16dc52c`, `fix(PLAT-7/8/9): tres defectos detectados al importar el
  lote de reingenieria` (3 archivos de código, 3 de pruebas, +458 líneas).

Esta acta existe porque `CLAUDE.md` exige que una cuestión de plataforma no se cierre sin prueba
documentada. Las tres de aquí se cerraron **importando**, no razonando: ninguna la atrapaba la
suite de escritorio.

---

## PLAT-7 — `Data too long for column 'nombre'`

**Observado al importar Prórroga y o Ampliación de Verificación Vehicular:** la plataforma
rechaza el archivo. El nombre técnico `@@fecha_vencimiento_certificado_anterior` tiene 38
caracteres y la columna admite 30.

**Causa:** el compilador recortaba a 30 los nombres que **él proponía**, pero no los que el
analista **declara** en el Diccionario. Esa tercera ruta no pasaba por el cap.

**Corregido:** se recorta en las tres rutas de nombre; el extractor emite el hueco `DIC-06`
—revisa las referencias `@@` en el TO-BE, porque al recortar el nombre las referencias del
diagrama dejan de casar— y el validador marca `EST-05`, bloqueante, si algún `campo.nombre`
pasa de 30.

**Pruebas de regresión:** `test_capa_el_nombre_tecnico_declarado_que_desborda_la_columna`,
`test_capa_el_nombre_de_la_columna_variable_que_desborda_la_columna`,
`test_un_nombre_tecnico_declarado_dentro_del_limite_no_dispara_DIC_06`,
`test_detecta_nombre_de_campo_que_desborda_la_columna_de_la_plataforma`.

---

## PLAT-8 — `Invalid argument supplied for foreach()` al abrir las Vistas

**Observado:** el import pasa, pero abrir las Vistas produce el error de PHP en
`radio/display.php` y `models/CampoSelect.php`. Los `select` y `radio` salían **sin opciones**.

**Dos causas, no una:**

1. El extractor no reconocía varios de los formatos con los que el Diccionario escribe un
   catálogo: separado por comas, por ` / `, por `<br>`, envuelto en `(catálogo: …)`, o un campo
   `Boolean` / `Switch Sí-No` que no declara valores porque su dominio se da por sabido.
2. Un `select` vacío revienta la vista **aunque `datos` sea `"[]"` y no `null`**. No hay forma
   segura de emitir un select sin opciones.

**Corregido:** parser de catálogos ampliado a esos formatos, con `{Sí, No}` derivado para los
booleanos; y un **piso seguro** — un `select`/`radio` sin opciones, sin endpoint y sin campo
padre **se degrada a campo de texto**, con el hueco `DIC-07` y la regla `EST-06` del validador.
Nunca se emite un select vacío.

**Pruebas de regresión:** `test_un_select_sin_opciones_se_degrada_a_texto`,
`test_un_radio_sin_opciones_se_degrada_a_texto`, `test_un_select_con_opciones_sigue_siendo_select`,
`test_catalogo_separado_por_comas`, `test_catalogo_separado_por_br`,
`test_catalogo_con_envoltura_de_parentesis_y_prefijo`,
`test_un_campo_booleano_sin_catalogo_explicito_usa_si_no`,
`test_reporta_hueco_si_un_select_queda_sin_opciones`.

---

## PLAT-9 — un calendario clasificado como lista desplegable

**Observado:** los campos declarados `Selector de fecha (calendario)` salían como `select`, y
por tanto como select vacío.

**Causa:** la palabra «select» es subcadena de «**select**or». El clasificador de tipo casaba
por subcadena y ganaba el orden de evaluación.

**Corregido:** `selector de fecha` y `calendario` se resuelven **antes** que `select`; el campo
sale como tipo `date`.

**Prueba de regresión:** `test_selector_de_fecha_no_se_confunde_con_un_select`.

---

## Resultado de la jornada

| Indicador | Valor |
| --- | --- |
| Expedientes con insumos | 6 de 7 (IHM llegó vacía) |
| Importados sin errores tras la corrección | **6 de 6** (procesos `1068`–`1073`) |
| Defectos de plataforma nuevos | 3, los tres corregidos con prueba |
| Suite | 245 → 268, en verde |

## Lo que no es defecto y se resuelve a mano

1. **El flujo sale lineal.** Las compuertas del TO-BE se cuentan y se reportan, no se reproducen.
   Es deliberado.
2. **Componente de agendamiento de citas** (Publicación en el Periódico Oficial): el Diccionario
   define turnos de 20 min entre 9:20 y 16:40 con bloqueo de horarios ocupados. El compilador no
   sabe emitir ese componente y deja un campo de fecha simple: la vista no rompe, pero no reserva
   un turno real.
3. **Campos degradados a texto** por falta de catálogo (`DIC-07` / `DIC-02`), entre ellos
   `campos_con_error`, `tipo_de_sancion`, `tipo_multa` y `municipio_propietario`.

## La lección, que vale para todo el lote

PLAT-7 y PLAT-8 nacen en el Diccionario: nombres `@@` largos y catálogos escritos de seis
maneras distintas. El compilador no puede exigir consistencia al insumo, así que **degrada de
forma segura y lo reporta como hueco** en vez de emitir algo que la plataforma rechaza.

> **Anotado el 2026-09-21, al redactar el acta:** esa misma familia de defectos sigue viva. El
> `2026-09-18` se descubrió que una opción legítima llamada «Pendiente de…» tumbaba el catálogo
> entero (`5228358`), y **P-06** —partir por coma sin respetar los paréntesis— continúa abierto
> en `extractores/diccionario.py`. Ver `planeacion/pendientes.md`.
