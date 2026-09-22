from pathlib import Path

import pytest

from tests.conftest import WIKI, legible as _legible

from gpmc.extractores.diccionario import extraer, _tipo_de
from gpmc.nucleo.huecos import Hueco



MUESTRA = """
## Sección 1 — Pantallas

### Pantalla 1 — NOTARIO — Captura del Aviso

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |
| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |
| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura, generado] Campo `@@monto_pago`. |

### Pantalla 2 — ÁREA DE AVISOS — Validar

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Documento | Archivo | Carga de archivo (file) | Sí | Siempre visible | PDF, máx 5MB | N/A | acta.pdf | [Captura] Campo `@@archivo_acta`. |
"""


def test_detecta_las_pantallas_y_su_actor():
    r = extraer(MUESTRA)
    assert len(r.pantallas) == 2
    assert r.pantallas[0].nombre == "Captura del Aviso"
    assert r.pantallas[0].actor == "notario"
    assert r.pantallas[1].actor == "area de avisos"


def test_toma_el_nombre_tecnico_de_la_descripcion():
    r = extraer(MUESTRA)
    nombres = [c.nombre for c in r.pantallas[0].campos]
    assert nombres == ["curp_testador", "sexo_testador", "monto_pago"]


def test_conserva_la_etiqueta_visible():
    r = extraer(MUESTRA)
    assert r.pantallas[0].campos[0].etiqueta == "CURP"


def test_mapea_el_componente_al_tipo_de_gpm():
    r = extraer(MUESTRA)
    tipos = {c.nombre: c.tipo for c in r.pantallas[0].campos}
    assert tipos["curp_testador"] == "text"
    assert tipos["sexo_testador"] == "select"
    assert extraer(MUESTRA).pantallas[1].campos[0].tipo == "file"


def test_lee_obligatorio_y_longitud():
    r = extraer(MUESTRA)
    curp = r.pantallas[0].campos[0]
    assert curp.obligatorio is True
    assert curp.longitud_exacta == 18
    assert r.pantallas[0].campos[2].obligatorio is False


def test_lee_el_catalogo():
    r = extraer(MUESTRA)
    sexo = r.pantallas[0].campos[1]
    assert [o.valor for o in sexo.catalogo] == ["hombre", "mujer"]
    assert [o.etiqueta for o in sexo.catalogo] == ["Hombre", "Mujer"]


def test_marca_solo_lectura():
    r = extraer(MUESTRA)
    assert r.pantallas[0].campos[2].solo_lectura is True
    assert r.pantallas[0].campos[0].solo_lectura is False


def test_reporta_hueco_si_un_campo_no_trae_nombre_tecnico():
    sin_nombre = MUESTRA.replace("Campo `@@curp_testador`.", "sin nombre tecnico.")
    r = extraer(sin_nombre)
    dic01 = [h for h in r.huecos if h.codigo == "DIC-01"]
    assert dic01, r.huecos
    assert dic01[0].nivel == "por_confirmar"
    assert dic01[0].propuesta
    assert dic01[0].ubicacion.startswith("p")


def test_reporta_hueco_si_el_catalogo_esta_pendiente():
    pend = MUESTRA.replace("Hombre · Mujer", "Pendiente de confirmar con la dependencia")
    r = extraer(pend)
    dic02 = [h for h in r.huecos if h.codigo == "DIC-02"]
    assert dic02, r.huecos
    assert dic02[0].nivel == "falta_dato"


def test_todos_los_huecos_son_del_tipo_Hueco():
    sin_nombre = MUESTRA.replace("Campo `@@curp_testador`.", "sin nombre tecnico.")
    r = extraer(sin_nombre)
    assert r.huecos
    assert all(isinstance(h, Hueco) for h in r.huecos)


@pytest.mark.parametrize("expediente", [
    "anita/Alta de Avisos de Testamento",
    "elesvan/Constancia de No Infracción Vehicular Ambiental",
])
def test_parsea_diccionarios_reales(expediente):
    ruta = WIKI / expediente / "Diccionario de Datos.md"
    if not _legible(ruta):
        pytest.skip(f"no disponible: {expediente}")
    r = extraer(ruta.read_text(encoding="utf-8"))
    assert len(r.pantallas) >= 3, f"solo {len(r.pantallas)} pantallas"
    total = sum(len(p.campos) for p in r.pantallas)
    assert total >= 15, f"solo {total} campos"


def test_acepta_pantallas_anidadas_bajo_el_stepper():
    """Los expedientes que siguen la regla fija 16 usan #### Pantalla bajo
    ### Paso N del stepper, y anotan el paso en el nombre."""
    texto = (
        "### Paso 1 del stepper — Solicitud\n\n"
        "#### Pantalla 1 — SOLICITANTE — Elegibilidad (Paso 1 — Solicitud)\n\n"
        "| Nombre del Campo | Componente Sugerido (GPM) | Obligatorio | Descripción |\n"
        "| --- | --- | --- | --- |\n"
        "| CURP | Campo de texto | Sí | [Captura] Campo `@@curp`. |\n"
    )
    r = extraer(texto)
    assert len(r.pantallas) == 1
    p = r.pantallas[0]
    assert p.actor == "solicitante"
    assert p.paso_ciudadano == 1
    assert "Paso 1" not in p.nombre
    assert p.campos[0].nombre == "curp"


_DICC_HIBRIDO = """# Diccionario de Datos Híbrido - Acceso a la Información

| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `estado_sol` | select | N/A | `mgee` (INEGI) | Despliega catálogo de 32 estados dinámicamente. |
| `municipio_sol` | select | `estado_sol` | `mgem` (INEGI) | Se inyecta la variable @@estado_sol en la URL para extraer sus dependencias. |
| `cp_sol` | text | N/A | N/A | Validación regex (exact_length[5]). |
| `colonia_sol` | select | `cp_sol` | `zip_codes` (SEPOMEX) | Inyecta la variable @@cp_sol para retornar el catálogo de esa zona. |
"""


def test_formato_hibrido_usa_la_columna_variable_como_nombre_tecnico():
    r = extraer(_DICC_HIBRIDO)
    assert len(r.pantallas) == 1
    nombres = [c.nombre for c in r.pantallas[0].campos]
    assert nombres == ["estado_sol", "municipio_sol", "cp_sol", "colonia_sol"]


def test_formato_hibrido_no_confunde_una_referencia_at_at_con_el_nombre():
    # @@estado_sol en el Comportamiento de municipio_sol es una dependencia
    # (select en cascada), no el nombre del campo: no debe colisionar.
    r = extraer(_DICC_HIBRIDO)
    nombres = [c.nombre for c in r.pantallas[0].campos]
    assert len(nombres) == len(set(nombres)), f"nombres colisionados: {nombres}"


def test_formato_hibrido_no_emite_DIC_01():
    # La columna Variable ES el nombre técnico declarado; no es una propuesta.
    r = extraer(_DICC_HIBRIDO)
    assert not [h for h in r.huecos if h.codigo == "DIC-01"], r.huecos


def test_no_absorbe_las_tablas_de_las_secciones_posteriores():
    """Las Secciones 2 a 5 del Diccionario traen tablas que no son de campos.
    Sin cortar, se colaban dentro de la ultima pantalla."""
    texto = MUESTRA + """
## Sección 2 — Documentos

| Documento | Formato | Pantalla |
| --- | --- | --- |
| Acta | PDF | Pantalla 1 |
| Oficio | PDF | Pantalla 2 |
"""
    r = extraer(texto)
    ultima = r.pantallas[-1]
    etiquetas = [c.etiqueta for c in ultima.campos]
    assert "Acta" not in etiquetas and "Oficio" not in etiquetas
    assert etiquetas == ["Documento"]


def test_el_tipo_se_lee_tambien_de_la_columna_de_tipo():
    # El Diccionario hibrido no trae columna de componente: su columna
    # "Tipo (GPM)" nombra directamente el tipo de la plataforma.
    assert _tipo_de("", "select") == "select"
    assert _tipo_de("", "file") == "file"
    assert _tipo_de("", "textarea") == "textarea"


def test_el_componente_gana_sobre_la_columna_de_tipo():
    # Cuando ambas columnas existen manda la mas especifica, como hasta hoy.
    assert _tipo_de("Lista desplegable (select)", "String") == "select"
    assert _tipo_de("Campo de texto (input)", "String") == "text"


def test_los_tipos_del_diccionario_estandar_no_cambian():
    # Guarda de regresion: los valores de la columna "Tipo de Dato" del
    # Diccionario estandar deben resolver igual que antes de este cambio.
    assert _tipo_de("", "String") == "text"
    assert _tipo_de("", "Number") == "text"
    assert _tipo_de("", "Archivo") == "file"
    # "Fecha" resuelve a "date" desde la Tarea 2 (antes daba "text"). Se fija
    # aqui para que el cambio quede en el registro en cualquier sentido.
    assert _tipo_de("", "Fecha") == "date"


_DICC_HIBRIDO_PANTALLA_FECHA_NAC = """### Pantalla 1 — Solicitante — Datos

| Variable | Tipo (GPM) | Dependencia | Comportamiento |
| --- | --- | --- | --- |
| `nacimiento_sol` | select | `fecha_nac` | Catálogo que depende de la fecha. |
"""

_DICC_HIBRIDO_RESCATE_FECHA_NAC = """# Diccionario de Datos Híbrido

| Variable | Tipo (GPM) | Dependencia | Comportamiento |
| :--- | :--- | :--- | :--- |
| `nacimiento_sol` | select | `fecha_nac` | Catálogo que depende de la fecha. |
"""


def test_hibrido_el_tipo_declarado_gana_sobre_la_columna_dependencia_ruta_estandar():
    # 'Dependencia' = fecha_nac cae posicionalmente donde el codigo buscaba el
    # componente; 'fecha' NO debe ganarle al 'select' declarado en Tipo (GPM).
    r = extraer(_DICC_HIBRIDO_PANTALLA_FECHA_NAC)
    tipos = {c.nombre: c.tipo for c in r.pantallas[0].campos}
    assert tipos["nacimiento_sol"] == "select"


def test_hibrido_el_tipo_declarado_gana_sobre_la_columna_dependencia_ruta_rescate():
    r = extraer(_DICC_HIBRIDO_RESCATE_FECHA_NAC)
    tipos = {c.nombre: c.tipo for c in r.pantallas[0].campos}
    assert tipos["nacimiento_sol"] == "select"


def test_el_diccionario_hibrido_produce_selects():
    r = extraer(_DICC_HIBRIDO)
    tipos = {c.nombre: c.tipo for c in r.pantallas[0].campos}
    assert tipos["estado_sol"] == "select"
    assert tipos["municipio_sol"] == "select"
    assert tipos["cp_sol"] == "text"


_DICC_PANTALLA_CON_VARIABLE = """### Pantalla 2 — Solicitante — Datos

| Variable | Tipo (GPM) | Obligatorio | Comportamiento |
| --- | --- | --- | --- |
| `rfc_sol` | text | Sí | Validación de formato. |
"""


def test_la_etiqueta_derivada_se_reporta_como_DIC_05():
    r = extraer(_DICC_HIBRIDO)
    dic05 = [h for h in r.huecos if h.codigo == "DIC-05"]
    assert dic05, r.huecos
    assert dic05[0].nivel == "por_confirmar"
    # Las etiquetas viajan al .gpm y se imprimen en el formulario publicado:
    # "Estado sol" era la clave interna con un espacio.
    assert {h.propuesta for h in dic05} >= {
        "Estado del solicitante", "Municipio del solicitante",
    }


def test_hay_un_DIC_05_por_cada_etiqueta_derivada():
    # Los 4 campos de _DICC_HIBRIDO vienen de la columna Variable.
    r = extraer(_DICC_HIBRIDO)
    dic05 = [h for h in r.huecos if h.codigo == "DIC-05"]
    assert len(dic05) == len(r.pantallas[0].campos) == 4
    assert all(h.ubicacion == "p1" for h in dic05)


def test_la_ruta_estandar_tambien_reporta_DIC_05():
    r = extraer(_DICC_PANTALLA_CON_VARIABLE)
    dic05 = [h for h in r.huecos if h.codigo == "DIC-05"]
    assert dic05, r.huecos
    assert dic05[0].ubicacion == "p2"
    assert dic05[0].propuesta == "RFC del solicitante"


def test_el_diccionario_estandar_no_levanta_DIC_05():
    # Ahi la etiqueta ya es legible y la escribio una persona: no hay nada que
    # confirmar.
    r = extraer(MUESTRA)
    assert r.pantallas[0].campos[0].etiqueta == "CURP"
    assert not [h for h in r.huecos if h.codigo == "DIC-05"]


def test_el_endpoint_queda_desnudo_sin_acentos_graves_ni_proveedor():
    # El Diccionario escribe "`mgem` (INEGI)"; el registro se busca por "mgem".
    r = extraer(_DICC_HIBRIDO)
    por_nombre = {c.nombre: c for c in r.pantallas[0].campos}
    assert por_nombre["estado_sol"].endpoint == "mgee"
    assert por_nombre["municipio_sol"].endpoint == "mgem"
    assert por_nombre["colonia_sol"].endpoint == "zip_codes"


def test_la_dependencia_de_campo_queda_desnuda():
    r = extraer(_DICC_HIBRIDO)
    municipio = {c.nombre: c for c in r.pantallas[0].campos}["municipio_sol"]
    assert municipio.dependencia_tipo == "campo"
    assert municipio.dependencia_campo == "estado_sol"


def test_api_ajax_es_su_propio_tipo_de_dependencia_no_un_campo():
    # 'api_ajax' en la columna Dependencia significa "lo llena una API", no
    # "depende de un campo llamado api_ajax".
    dicc = """# Hibrido

| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `nombres_sol` | text | `api_ajax` | `consultacurpn` (SIPUBEH) | Del nodo data.nombres. |
"""
    c = extraer(dicc).pantallas[0].campos[0]
    assert c.dependencia_tipo == "api_ajax"
    assert c.dependencia_campo is None
    assert c.endpoint == "consultacurpn"


def test_api_ajax_levanta_API_04():
    dicc = """# Hibrido

| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `nombres_sol` | text | `api_ajax` | `consultacurpn` (SIPUBEH) | Del nodo data.nombres. |
"""
    r = extraer(dicc)
    api04 = [h for h in r.huecos if h.codigo == "API-04"]
    assert api04, r.huecos
    assert api04[0].nivel == "por_confirmar"


def test_na_y_vacio_no_producen_dependencia():
    r = extraer(_DICC_HIBRIDO)
    estado = {c.nombre: c for c in r.pantallas[0].campos}["estado_sol"]
    assert estado.dependencia_tipo is None
    assert estado.dependencia_campo is None


def test_los_campos_con_endpoint_conservan_origen():
    # estimador.py cuenta las integraciones con `if c.origen`; sin esta
    # señal un trámite con 6 integraciones se estima como si no tuviera.
    r = extraer(_DICC_HIBRIDO)
    con_endpoint = [c for c in r.pantallas[0].campos if c.endpoint]
    assert con_endpoint
    assert all(c.origen for c in con_endpoint)


def test_dependencia_con_doble_arroba():
    # @@estado_sol en la columna Dependencia debe limpiarse a estado_sol.
    dicc = """# Diccionario de Datos Híbrido

| Variable | Tipo (GPM) | Dependencia | Comportamiento |
| :--- | :--- | :--- | :--- |
| `municipio` | select | `@@estado` | Se inyecta la variable. |
"""
    c = extraer(dicc).pantallas[0].campos[0]
    assert c.dependencia_tipo == "campo"
    assert c.dependencia_campo == "estado"


def test_endpoint_con_guion_y_barra():
    # `` `zip-codes/v2` (SEPOMEX) `` debe extraerse como "zip-codes/v2".
    dicc = """# Diccionario de Datos Híbrido

| Variable | Tipo (GPM) | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- |
| `colonia` | select | `zip-codes/v2` (SEPOMEX) | Consulta el API de códigos. |
"""
    c = extraer(dicc).pantallas[0].campos[0]
    assert c.endpoint == "zip-codes/v2"


def test_endpoint_na_en_minusculas_o_mixta():
    # n/a, N/a deben producir endpoint None, igual que N/A.
    dicc1 = """# Diccionario
| Variable | Tipo (GPM) | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- |
| `campo1` | text | n/a | Sin endpoint. |
"""
    dicc2 = """# Diccionario
| Variable | Tipo (GPM) | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- |
| `campo2` | text | N/a | Sin endpoint. |
"""
    assert extraer(dicc1).pantallas[0].campos[0].endpoint is None
    assert extraer(dicc2).pantallas[0].campos[0].endpoint is None


def test_cp_sol_tiene_endpoint_none():
    # cp_sol en _DICC_HIBRIDO tiene N/A en Endpoint / API; debe ser None.
    r = extraer(_DICC_HIBRIDO)
    cp = {c.nombre: c for c in r.pantallas[0].campos}["cp_sol"]
    assert cp.endpoint is None


def test_api_ajax_es_insensible_a_mayusculas():
    # API_AJAX, Api_Ajax, api_ajax deben todos producir dependencia_tipo='api_ajax'.
    for variante in ["API_AJAX", "Api_Ajax", "api_ajax", "`API_AJAX`"]:
        dicc = f"""# Diccionario
| Variable | Tipo (GPM) | Dependencia | Endpoint / API | Comportamiento |
| :--- | :--- | :--- | :--- | :--- |
| `test` | text | {variante} | `consultacurpn` (SIPUBEH) | Prueba. |
"""
        c = extraer(dicc).pantallas[0].campos[0]
        assert c.dependencia_tipo == "api_ajax", f"falló para {variante}"
        assert c.dependencia_campo is None, f"falló para {variante}"


def test_limpia_la_anotacion_de_prueba_del_nombre_de_pantalla():
    """El Diccionario de Testamento anota los nombres de pantalla con
    '*(Tarea GPM #7920 en una prueba/mockup ...)*'. Ese texto no es parte del
    nombre y, sin limpiar, desborda la columna 'nombre' de la plataforma y
    tumba el import entero con 'Data too long' (verificado 2026-08-31)."""
    texto = ("### Pantalla 1 — NOTARIO — Captura del Aviso (a distancia) "
             "*(Tarea GPM #7920 en una prueba/mockup — el tramite no esta en produccion)*\n\n"
             "| Nombre del Campo | Descripción |\n| CURP | La CURP @@curp |\n")
    r = extraer(texto)
    assert r.pantallas[0].nombre == "Captura del Aviso (a distancia)"


def test_el_nombre_tecnico_propuesto_cabe_en_la_columna_campo():
    """Un campo sin @@ con etiqueta larga hacía que _babel derivara un nombre
    de 40 chars ('nombre_s_completo_del_testador_apellido_'), que desborda la
    columna 'nombre' de la tabla campo y tumba el import entero con 'Data too
    long' (verificado 2026-08-31, proceso de Testamento). Los exports
    auténticos nunca pasan de 31 chars en ese nombre."""
    texto = MUESTRA.replace(
        "| CURP | String", "| Nombre(s) completo del Testador, Apellido Paterno Apellido Materno | String"
    ).replace("Campo `@@curp_testador`.", "sin nombre tecnico.")
    c = extraer(texto).pantallas[0].campos[0]
    assert len(c.nombre) <= 31, c.nombre


def test_capa_el_nombre_tecnico_declarado_que_desborda_la_columna():
    """Un `@@nombre` explícito de más de 30 chars reventaba el import con
    'Data too long for column nombre' (verificado 2026-09-02, expediente de
    Prórroga: `@@fecha_vencimiento_certificado_anterior`, 38 chars). El
    extractor solo capaba la ruta de nombre PROPUESTO; el declarado pasaba
    verbatim. Ahora se capa y se reporta DIC-06 para que una persona ajuste
    las referencias @@ del TO-BE y de las fórmulas."""
    texto = MUESTRA.replace(
        "Campo `@@curp_testador`.",
        "Campo `@@fecha_vencimiento_del_certificado_anterior`.",
    )
    r = extraer(texto)
    campo = r.pantallas[0].campos[0]
    assert len(campo.nombre) <= 30, campo.nombre
    assert not campo.nombre.endswith("_")
    dic06 = [h for h in r.huecos if h.codigo == "DIC-06"]
    assert dic06, r.huecos
    assert dic06[0].nivel == "falta_dato"
    assert dic06[0].propuesta == campo.nombre


def test_capa_el_nombre_de_la_columna_variable_que_desborda_la_columna():
    texto = """
### Pantalla 1 — NOTARIO — Captura

| Nombre del Campo | Variable | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fecha de Vencimiento | fecha_de_vencimiento_del_certificado_anterior | Date | Selector de fecha | Sí | Siempre visible | N/A | N/A | 10/04/2025 | [Captura]. |
"""
    r = extraer(texto)
    campo = r.pantallas[0].campos[0]
    assert len(campo.nombre) <= 30, campo.nombre
    assert [h for h in r.huecos if h.codigo == "DIC-06"], r.huecos


def test_un_nombre_tecnico_declarado_dentro_del_limite_no_dispara_DIC_06():
    r = extraer(MUESTRA)
    assert [h for h in r.huecos if h.codigo == "DIC-06"] == [], r.huecos


def test_catalogo_separado_por_comas():
    """El Diccionario de Reposición lista las opciones del select separadas por
    comas ('Doble cero, Cero, Uno, Dos, Voluntario'), no por '·'. Sin esto el
    campo salía sin opciones y la plataforma reventaba al renderizar la vista
    con 'Invalid argument supplied for foreach()' (models/CampoSelect.php:375)."""
    texto = MUESTRA.replace("Hombre · Mujer", "Doble cero, Cero, Uno, Dos, Voluntario")
    sexo = extraer(texto).pantallas[0].campos[1]
    assert [o.etiqueta for o in sexo.catalogo] == [
        "Doble cero", "Cero", "Uno", "Dos", "Voluntario",
    ]


def test_catalogo_si_no_declarado_en_la_columna_de_limite():
    """Los radios booleanos ('¿Es Persona Moral?') traen 'Sí / No' en la columna
    Límite/Especificaciones y 'N/A' en Catálogo de Valores. El campo salía sin
    opciones -> foreach() en radio/display.php:4 al abrir la vista."""
    texto = """
### Pantalla 1 — CIUDADANO — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ¿Es Persona Moral? | Boolean | Switch / radio Sí-No | Sí | Siempre visible | Sí / No | N/A | No | [Captura] Campo `@@es_persona_moral`. |
"""
    campo = extraer(texto).pantallas[0].campos[0]
    assert campo.tipo == "radio"
    assert [o.etiqueta for o in campo.catalogo] == ["Sí", "No"]
    assert [o.valor for o in campo.catalogo] == ["si", "no"]


def test_reporta_hueco_si_un_select_queda_sin_opciones():
    """Un select/radio sin catálogo parseable ni endpoint es un hueco DIC-07:
    la vista de la plataforma lo renderiza como lista vacía."""
    texto = MUESTRA.replace("Hombre · Mujer", "Valores definidos")
    r = extraer(texto)
    dic07 = [h for h in r.huecos if h.codigo == "DIC-07"]
    assert dic07, r.huecos
    assert dic07[0].nivel == "falta_dato"


def test_un_select_con_catalogo_no_dispara_DIC_07():
    r = extraer(MUESTRA)
    assert [h for h in r.huecos if h.codigo == "DIC-07"] == [], r.huecos


def test_selector_de_fecha_no_se_confunde_con_un_select():
    """'Selector de fecha (calendario)' contiene la subcadena 'select'
    ('sele-ctor'). Se clasificaba como lista desplegable y salía como un select
    vacío en la vista (verificado 2026-09-02, Prórroga: 'Fecha de Vencimiento
    del Certificado Anterior')."""
    assert _tipo_de("Selector de fecha (calendario)", "Date") == "date"
    assert _tipo_de("Lista desplegable (select)", "String") == "select"


def test_catalogo_largo_separado_por_medios_puntos_no_se_descarta():
    """El catálogo de Municipio de Publicación en el Periódico Oficial trae 84
    valores separados por ' · '. Un tope de conteo lo descartaba y el campo
    salía sin opciones (regresión detectada 2026-09-02)."""
    municipios = " · ".join(f"Municipio {i}" for i in range(1, 85))
    texto = MUESTRA.replace("Hombre · Mujer", municipios)
    sexo = extraer(texto).pantallas[0].campos[1]
    assert len(sexo.catalogo) == 84


def test_una_lista_por_comas_larguisima_se_trata_como_prosa():
    """La coma es ambigua: 40+ fragmentos o fragmentos largos son prosa."""
    prosa = ("si es doble cero, execto e ircopracion . colocar fecha de "
             "terminacion exacta o la fecha de formato de incorporacion . si es "
             "cero uno y dos de acuerdo al calendario de verificacion vehicular")
    texto = MUESTRA.replace("Hombre · Mujer", prosa)
    sexo = extraer(texto).pantallas[0].campos[1]
    assert sexo.catalogo == []


def test_catalogo_con_envoltura_de_parentesis_y_prefijo():
    """El Diccionario de Testamento escribe '(catálogo: A, B, C)' — con
    paréntesis y prefijo. Sin limpiarlos, la primera opción salía como
    '(catálogo: A' (verificado 2026-09-02, 'Tipo de Testamento')."""
    texto = MUESTRA.replace(
        "Hombre · Mujer",
        "(catálogo: Público abierto, Público Cerrado, Público simplificado)",
    )
    sexo = extraer(texto).pantallas[0].campos[1]
    assert [o.etiqueta for o in sexo.catalogo] == [
        "Público abierto", "Público Cerrado", "Público simplificado",
    ]


def test_catalogo_separado_por_br():
    """'Soltero <br>Casado <br>Viudo' — separador HTML."""
    texto = MUESTRA.replace("Hombre · Mujer", "Soltero <br>Casado <br>Viudo")
    sexo = extraer(texto).pantallas[0].campos[1]
    assert [o.etiqueta for o in sexo.catalogo] == ["Soltero", "Casado", "Viudo"]


def test_catalogo_con_corridas_de_espacios_se_despega_en_varios_valores():
    """El Diccionario de Testamento trae 'Estado Civil' así:
    '(Catálogo: Soltero        casado       <br>Divorciado  Viudo <br>Unión Libre)'
    — separadores irregulares: corridas de espacios además del <br>. Salía como
    3 opciones basura ('Soltero        casado', 'Divorciado  Viudo', 'Unión
    Libre') y el validador la daba por buena. Una corrida de 2+ espacios por
    dentro de una opción son dos valores que perdieron el separador; un espacio
    simple ('Unión Libre') es una etiqueta legítima."""
    texto = MUESTRA.replace(
        "Hombre · Mujer",
        "(Catálogo: Soltero        casado       <br>Divorciado  Viudo <br>Unión Libre)",
    )
    sexo = extraer(texto).pantallas[0].campos[1]
    assert [o.etiqueta for o in sexo.catalogo] == [
        "Soltero", "casado", "Divorciado", "Viudo", "Unión Libre",
    ]
    # y el valor técnico no arrastra corridas de guiones bajos
    assert all("__" not in o.valor for o in sexo.catalogo)


def test_un_campo_booleano_sin_catalogo_explicito_usa_si_no():
    """'Tipo de Dato = Boolean' con 'Sí-No' en Límite y sin lista en Catálogo:
    el dominio es {Sí, No}. Salía sin opciones -> foreach() en la vista
    (verificado 2026-09-02, 'Disposiciones de Contenido Irrevocable')."""
    texto = """
### Pantalla 1 — CIUDADANO — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Disposiciones Irrevocables | Boolean | Switch / radio Sí-No | No | Siempre visible | Sí-No | No | No | [Captura] Campo `@@disposiciones`. |
"""
    campo = extraer(texto).pantallas[0].campos[0]
    assert campo.tipo == "radio"
    assert [o.valor for o in campo.catalogo] == ["si", "no"]


# --- condicion de visibilidad (columna "Condición de Visibilidad") ---

_VIS = """
### Pantalla 1 — CIUDADANO — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ¿Es Persona Moral? | Boolean | Switch / radio Sí-No | Sí | Siempre visible | Sí / No | N/A | No | [Captura] Campo `@@es_persona_moral`. |
| Tipo de Solicitante | Select | Lista desplegable | Sí | Siempre visible | N/A | Persona física · Persona moral | Persona física | [Captura] Campo `@@tipo_solicitante`. |
| CURP del Solicitante | String | Campo de texto | Condicional | Visible y obligatorio solo si "¿Es Persona Moral?" = No | 18 caracteres | N/A | N/A | [Captura] Campo `@@curp_solicitante`. |
| Razón Social | String | Campo de texto | Condicional | Visible solo cuando `@@es_persona_moral` = Sí | N/A | N/A | N/A | [Captura] Campo `@@razon_social`. |
| Nombre del Representante | String | Campo de texto | Condicional | Visible solo si "Tipo de Solicitante" = Persona moral | N/A | N/A | N/A | [Captura] Campo `@@nombre_representante`. |
| PDF escrito | Archivo | Carga de archivo | Condicional | Visible solo si "Tipo de Solicitante" ≠ Persona física | N/A | N/A | N/A | [Captura] Campo `@@pdf_escrito`. |
| Nota rara | String | Campo de texto | Condicional | Visible y obligatoria cuando `@@tipo_documento` ∈ {Acuerdo, Decreto, Ley} | N/A | N/A | N/A | [Captura] Campo `@@nota_rara`. |
"""


def _campo(r, nombre):
    for p in r.pantallas:
        for c in p.campos:
            if c.nombre == nombre:
                return c
    raise AssertionError(nombre)


def test_condicion_visible_desde_etiqueta_si_no():
    c = _campo(extraer(_VIS), "curp_solicitante")
    assert c.condicion_visible is not None
    assert c.condicion_visible.campo == "es_persona_moral"
    assert c.condicion_visible.igual == "no"
    assert c.condicion_visible.operador == "=="


def test_condicion_visible_desde_referencia_at_at():
    c = _campo(extraer(_VIS), "razon_social")
    assert c.condicion_visible.campo == "es_persona_moral"
    assert c.condicion_visible.igual == "si"


def test_condicion_visible_resuelve_el_valor_contra_el_catalogo_del_campo_referido():
    c = _campo(extraer(_VIS), "nombre_representante")
    assert c.condicion_visible.campo == "tipo_solicitante"
    assert c.condicion_visible.igual == "persona_moral"


def test_condicion_visible_con_desigualdad():
    c = _campo(extraer(_VIS), "pdf_escrito")
    assert c.condicion_visible.campo == "tipo_solicitante"
    assert c.condicion_visible.igual == "persona_fisica"
    assert c.condicion_visible.operador == "!="


def test_siempre_visible_no_pone_condicion_ni_hueco():
    r = extraer(_VIS)
    assert _campo(r, "tipo_solicitante").condicion_visible is None
    assert [h for h in r.huecos if h.codigo == "DIC-08"] == [] or \
        all("Nota rara" in h.mensaje for h in r.huecos if h.codigo == "DIC-08")


def test_condicion_no_interpretable_reporta_DIC_08():
    r = extraer(_VIS)
    dic08 = [h for h in r.huecos if h.codigo == "DIC-08"]
    assert dic08, r.huecos
    assert "nota_rara" in dic08[0].mensaje.lower() or "Nota rara" in dic08[0].mensaje
    assert _campo(r, "nota_rara").condicion_visible is None


def test_dic08_lleva_pantalla_y_campo_en_la_ubicacion():
    r = extraer(_VIS)
    dic08 = [h for h in r.huecos if h.codigo == "DIC-08"]
    assert dic08, r.huecos
    assert "::" in dic08[0].ubicacion
    pantalla, campo = dic08[0].ubicacion.split("::", 1)
    assert pantalla and campo
    assert dic08[0].ubicacion == "p1::nota_rara"


from gpmc.extractores.diccionario import _catalogo_de


# ── Envoltorios del catalogo y valores con anotacion ────────────────────────
#
# Estos dos no producian un hueco: producian un .gpm MAL. La plataforma
# importaba una opcion llamada literalmente "Catálogo (Dependencia u organismo".

def test_el_envoltorio_catalogo_con_parentesis_no_contamina_la_primera_opcion():
    """El Diccionario de Publicacion escribe: «Catálogo (A, B, C)». Ya se
    trataba la forma «(catálogo: A, B, C)» —comentario de 2026-09-02— pero no
    esta, con la palabra delante del parentesis."""
    opciones, pendiente = _catalogo_de(
        "Catálogo (Dependencia u organismo, Municipio, Público en general)"
    )

    assert [o.etiqueta for o in opciones] == [
        "Dependencia u organismo", "Municipio", "Público en general",
    ]
    assert not pendiente


def test_una_lista_con_anotaciones_entre_parentesis_no_se_desenvuelve():
    """«En línea (validación automática) · Banco...» es una lista con notas, no
    un envoltorio: desenvolverla se comeria la segunda opcion."""
    opciones, _ = _catalogo_de(
        "En línea (validación automática) · Banco o transferencia (con comprobante)"
    )

    assert [o.etiqueta for o in opciones] == [
        "En línea (validación automática)", "Banco o transferencia (con comprobante)",
    ]


def test_el_valor_casa_aunque_la_opcion_lleve_una_nota_entre_parentesis():
    """El Diccionario declara la opcion «En línea (validación automática)» y la
    condicion la cita como «= En línea». Exigir la cadena completa dejaba el
    campo sin condicion y emitia un DIC-08 por una diferencia de redaccion."""
    from gpmc.nucleo.manifiesto import Campo, OpcionCatalogo
    from gpmc.extractores.diccionario import _resolver_condicion_visible

    campo = Campo(
        nombre="modalidad_pago", etiqueta="Modalidad de Pago", tipo="select",
        catalogo=[
            OpcionCatalogo(etiqueta="En línea (validación automática)", valor="en_linea"),
            OpcionCatalogo(etiqueta="Banco o transferencia (con comprobante)", valor="banco"),
        ],
    )
    indice = {"campos": {"modalidad_pago": campo}, "por_etiqueta": {}}

    cond = _resolver_condicion_visible("@@modalidad_pago", "==", "En línea", indice)

    assert cond is not None
    assert cond.igual == "en_linea"


def test_un_valor_que_no_existe_en_el_catalogo_sigue_sin_resolver():
    """La tolerancia no puede convertirse en adivinanza."""
    from gpmc.nucleo.manifiesto import Campo, OpcionCatalogo
    from gpmc.extractores.diccionario import _resolver_condicion_visible

    campo = Campo(
        nombre="modalidad_pago", etiqueta="Modalidad de Pago", tipo="select",
        catalogo=[OpcionCatalogo(etiqueta="En línea (validación automática)", valor="en_linea")],
    )
    indice = {"campos": {"modalidad_pago": campo}, "por_etiqueta": {}}

    assert _resolver_condicion_visible("@@modalidad_pago", "==", "Efectivo", indice) is None


def test_salvo_cuando_esta_en_un_conjunto_se_vuelve_una_cadena_de_distintos():
    """«salvo cuando @@c ∈ {A, B}» es «≠A Y ≠B»: la conjuncion que el modelo ya
    sabe expresar desde SP2. No hace falta añadir O para este caso."""
    from gpmc.nucleo.manifiesto import Campo, OpcionCatalogo
    from gpmc.extractores.diccionario import _condicion_desde_conjunto

    campo = Campo(
        nombre="tipo_documento", etiqueta="Tipo de Documento", tipo="select",
        catalogo=[
            OpcionCatalogo(etiqueta="Convocatoria", valor="convocatoria"),
            OpcionCatalogo(etiqueta="Edicto", valor="edicto"),
            OpcionCatalogo(etiqueta="Ley", valor="ley"),
        ],
    )
    indice = {"campos": {"tipo_documento": campo}, "por_etiqueta": {}}

    cond = _condicion_desde_conjunto(
        "Visible y obligatoria salvo cuando `@@tipo_documento` ∈ {Convocatoria, Edicto}",
        indice,
    )

    assert cond is not None
    assert (cond.campo, cond.operador, cond.igual) == ("tipo_documento", "!=", "convocatoria")
    assert [(c.campo, c.operador, c.igual) for c in cond.y] == [
        ("tipo_documento", "!=", "edicto"),
    ]


def test_un_conjunto_en_positivo_no_se_inventa_una_conjuncion():
    """«@@c ∈ {A, B}» es una disyuncion: el modelo solo tiene Y. Convertirla en
    «=A Y =B» seria una condicion que nunca se cumple."""
    from gpmc.nucleo.manifiesto import Campo, OpcionCatalogo
    from gpmc.extractores.diccionario import _condicion_desde_conjunto

    campo = Campo(
        nombre="procedencia", etiqueta="Procedencia", tipo="select",
        catalogo=[
            OpcionCatalogo(etiqueta="Dependencia", valor="dependencia"),
            OpcionCatalogo(etiqueta="Municipio", valor="municipio"),
        ],
    )
    indice = {"campos": {"procedencia": campo}, "por_etiqueta": {}}

    assert _condicion_desde_conjunto(
        "Visible solo cuando `@@procedencia` ∈ {Dependencia, Municipio}", indice,
    ) is None


def test_sin_cabeceras_de_pantalla_el_aviso_no_cierra_la_puerta_del_gpm():
    """DIC-04 describe una decision que el compilador YA tomo —agrupar todo en
    una pantalla—, igual que DIC-05 cuando propone una etiqueta. DIC-05 es
    'por_confirmar'; DIC-04 era 'falta_dato' y bloqueaba la descarga.

    No ofrece ninguna respuesta posible: el unico control era "lo configuro a
    mano", que solo reconoce el hueco. Bloquear no arreglaba nada, solo pedia
    una configuracion manual para seguir."""
    texto = (
        "# Diccionario Híbrido\n\n"
        "| Variable | Tipo (GPM) | Comportamiento |\n"
        "| :--- | :--- | :--- |\n"
        "| `curp` | text | Fuerza uppercase |\n"
        "| `cp` | text | Validación regex |\n"
    )

    r = extraer(texto)

    d4 = [h for h in r.huecos if h.codigo == "DIC-04"]
    assert len(d4) == 1
    assert d4[0].nivel == "por_confirmar"


def test_un_select_toma_su_catalogo_de_la_descripcion_si_no_hay_columna():
    """El Diccionario Hibrido no tiene columna 'Catálogo de Valores', pero
    escribe las opciones entre parentesis en la descripcion: «Clasificación de
    la Unidad de Transparencia (Entregable, Reservada, Inexistente)». El
    compilador emitia DIC-07 con las opciones a la vista."""
    texto = (
        "# Diccionario Híbrido\n\n"
        "| Variable | Tipo (GPM) | Comportamiento |\n"
        "| :--- | :--- | :--- |\n"
        "| `dictamen_ut` | select | Clasificación de la UT (Entregable, Reservada, Inexistente). |\n"
    )

    r = extraer(texto)

    campo = r.pantallas[0].campos[0]
    assert [o.etiqueta for o in campo.catalogo] == [
        "Entregable", "Reservada", "Inexistente",
    ]
    assert not [h for h in r.huecos if h.codigo == "DIC-07"]


def test_una_descripcion_con_un_parentesis_que_no_es_catalogo_no_inventa_opciones():
    """«Validación regex (exact_length[5])» no es una lista de opciones: un solo
    elemento no es un catalogo."""
    texto = (
        "# Diccionario Híbrido\n\n"
        "| Variable | Tipo (GPM) | Comportamiento |\n"
        "| :--- | :--- | :--- |\n"
        "| `cp_sol` | select | Validación regex (exact_length[5]). |\n"
    )

    r = extraer(texto)

    assert r.pantallas[0].campos[0].catalogo == []


def test_la_etiqueta_propuesta_se_lee_en_castellano_no_en_clave():
    """Cuando el Diccionario no trae etiqueta visible, la propuesta se emite AL
    .gpm y el ciudadano la ve impresa en el formulario. 'Nombres sol' y 'Cp
    sol' no son etiquetas de un tramite de gobierno."""
    from gpmc.extractores.diccionario import etiqueta_desde_nombre

    assert etiqueta_desde_nombre("nombres_sol") == "Nombres del solicitante"
    assert etiqueta_desde_nombre("cp_sol") == "Código Postal del solicitante"
    assert etiqueta_desde_nombre("curp_representante") == "CURP del representante"
    assert etiqueta_desde_nombre("dictamen_ut") == "Dictamen de la Unidad de Transparencia"
    assert etiqueta_desde_nombre("rfc_dependencia") == "RFC de la dependencia"
    # «Paterno del solicitante» no es como se pide un apellido en un formulario.
    assert etiqueta_desde_nombre("paterno_sol") == "Apellido paterno del solicitante"
    assert etiqueta_desde_nombre("materno_sol") == "Apellido materno del solicitante"


def test_un_nombre_que_no_conozco_al_menos_se_lee():
    from gpmc.extractores.diccionario import etiqueta_desde_nombre

    assert etiqueta_desde_nombre("motivo_rechazo") == "Motivo rechazo"
    assert etiqueta_desde_nombre("curp") == "CURP"


def test_una_opcion_que_dice_pendiente_no_marca_el_catalogo_como_pendiente():
    """Constancia de No Infraccion declara el catalogo de estatus completo:
    «En revisión, Pendiente de regularización, Concluido — Constancia emitida».
    La marca de pendiente se buscaba como subcadena en toda la celda, asi que
    la etiqueta legitima «Pendiente de regularización» tumbaba el catalogo
    entero y emitia un DIC-02 falso (verificado 2026-09-18)."""
    opciones, pendiente = _catalogo_de(
        "En revisión, Pendiente de regularización, Concluido — Constancia emitida"
    )

    assert not pendiente
    assert [o.etiqueta for o in opciones] == [
        "En revisión", "Pendiente de regularización", "Concluido — Constancia emitida",
    ]


def test_una_celda_declarada_pendiente_sigue_marcandose_pendiente():
    """El contrapeso del test de arriba: una celda que de verdad declara el
    catalogo como pendiente no parte en opciones y sigue dando DIC-02."""
    for celda in (
        "Pendiente de confirmar con la dependencia",
        "N/A (sin catálogo confirmado — ver Pendientes)",
        "Por definir",
    ):
        opciones, pendiente = _catalogo_de(celda)
        assert pendiente, celda
        assert not opciones


# ── El primer @@ de la descripcion se llevaba el nombre del campo ──
#
# Medido el 2026-09-21 sobre el lote de reingenieria: 27 campos fantasma en 5 de
# los 6 tramites. La causa: las filas de «Vista de solo lectura» escriben su
# descripcion citando OTRO campo —«Muestra @@observaciones capturadas por la
# Direccion»— y ese `@@` se tomaba como nombre propio. En Reposicion dejo tres
# campos llamados `estatus_tramite`, y el que ganaba no traia catalogo.
#
# La regla la acordamos con Simplificacion el 2026-09-21: un `@@` que ya esta
# declarado por otro campo es una REFERENCIA, no un nombre.

_REFERENCIA = MUESTRA.replace(
    "| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura, generado] Campo `@@monto_pago`. |",
    "| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura, generado] Campo `@@monto_pago`. |\n"
    "| Vista de solo lectura (Notario → Área) | N/A | Vista | No | Siempre visible | N/A | N/A | N/A | [Solo lectura] Muestra `@@curp_testador` capturado en la Pantalla 1. |",
)


def test_una_descripcion_que_cita_otro_campo_no_le_roba_el_nombre():
    r = extraer(_REFERENCIA)
    nombres = [c.nombre for p in r.pantallas for c in p.campos]
    assert nombres.count("curp_testador") == 1, f"nombre duplicado: {nombres}"


def test_la_fila_de_vista_sigue_produciendo_un_campo_con_nombre_propio():
    # No se descarta la fila: el compilador aun no sabe emitir un Paso de
    # visualizacion (P-09). Hasta entonces sale como campo, pero con nombre
    # propio derivado de su etiqueta, no robado.
    r = extraer(_REFERENCIA)
    nombres = [c.nombre for p in r.pantallas for c in p.campos]
    assert len(nombres) == len(set(nombres)), f"hay duplicados: {nombres}"
    assert any(n.startswith("vista_de_solo_lectura") for n in nombres), nombres


def test_un_campo_que_declara_su_propio_nombre_lo_conserva():
    # El contrapeso: sin el, ignorar SIEMPRE el @@ de la descripcion romperia
    # la via normal, que es justo como se declara un nombre tecnico.
    c = _campo(extraer(MUESTRA), "curp_testador")
    assert c.nombre == "curp_testador"


def test_el_primer_campo_que_declara_un_nombre_gana_sobre_el_que_lo_cita():
    # Orden inverso: si la fila que CITA va antes que la que declara, sigue sin
    # poder quedarse el nombre. Se comprueba mirando quien conserva el catalogo.
    texto = MUESTRA.replace(
        "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
        "| Vista previa | N/A | Vista | No | Siempre visible | N/A | N/A | N/A | [Solo lectura] Muestra `@@sexo_testador` ya capturado. |\n"
        "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
    )
    r = extraer(texto)
    nombres = [c.nombre for p in r.pantallas for c in p.campos]
    assert nombres.count("sexo_testador") == 1, nombres
    assert _campo(r, "sexo_testador").catalogo, "el dueño del nombre conserva su catalogo"


# ── Un nombre que proponemos nosotros no puede chocar con otro ──
#
# Medido el 2026-09-21 sobre 49 expedientes reales: de los 92 campos fantasma
# que quedaban tras arreglar lo del `@@` citado, **74 eran nombres que
# inventabamos nosotros** y chocaban entre si al capar a 30 caracteres —tres
# filas «Vista de solo lectura (X → Y)» distintas se quedaban todas en
# `vista_de_solo_lectura_ciudadan`—. El Diccionario no tiene la culpa de eso.

_DOS_VISTAS = MUESTRA.replace(
    "| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura, generado] Campo `@@monto_pago`. |",
    "| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura, generado] Campo `@@monto_pago`. |\n"
    "| Vista de solo lectura (Ciudadano → Notario) | N/A | Vista | No | Siempre visible | N/A | N/A | N/A | [Solo lectura] Lo capturado antes. |\n"
    "| Vista de solo lectura (Ciudadano → Área de Avisos) | N/A | Vista | No | Siempre visible | N/A | N/A | N/A | [Solo lectura] Lo capturado antes. |",
)


def test_dos_etiquetas_que_derivan_al_mismo_nombre_no_producen_dos_campos_iguales():
    r = extraer(_DOS_VISTAS)
    nombres = [c.nombre for p in r.pantallas for c in p.campos]
    assert len(nombres) == len(set(nombres)), f"nombres repetidos: {nombres}"


def test_el_nombre_desambiguado_respeta_el_limite_de_la_columna():
    # El cap de 30 es lo que hace chocar los nombres; la solucion no puede
    # saltarselo, o vuelve el 'Data too long for column nombre' de PLAT-7.
    from gpmc.extractores.diccionario import LIMITE_NOMBRE_CAMPO
    r = extraer(_DOS_VISTAS)
    for p in r.pantallas:
        for c in p.campos:
            assert len(c.nombre) <= LIMITE_NOMBRE_CAMPO, c.nombre


def test_un_nombre_propuesto_que_no_choca_se_queda_como_estaba():
    # El contrapeso: sin el, añadir sufijo a todos cambiaria nombres que hoy
    # estan bien y romperia las referencias del TO-BE.
    r = extraer(MUESTRA)
    nombres = [c.nombre for p in r.pantallas for c in p.campos]
    assert "curp_testador" in nombres and not any(n.endswith("_2") for n in nombres)


def test_un_at_declarado_dos_veces_por_el_diccionario_se_reporta():
    # Esto NO es culpa nuestra: dos filas dicen «Campo @@x». No se renombra a
    # la callada —seria adivinar cual es cual—, se reporta para que lo corrijan
    # en el Diccionario, que es donde vive el dato.
    texto = MUESTRA.replace(
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |",
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |\n"
        "| Sexo del cónyuge | String | Lista desplegable (select) | No | Siempre visible | N/A | Hombre · Mujer | Mujer | [Captura] Campo `@@sexo_testador`. |",
    )
    r = extraer(texto)
    h = [x for x in r.huecos if x.codigo == "DIC-09"]
    assert h, [x.codigo for x in r.huecos]
    assert "sexo_testador" in h[0].mensaje


def test_un_at_repetido_sin_la_palabra_campo_tambien_se_reporta():
    """El caso real del expediente del IHM: cuatro filas muestran el mismo
    folio en pantallas distintas y ninguna escribe «Campo @@…», solo
    «[Solo lectura] `@@numero_folio`». Sin la palabra clave no habia forma de
    saber cual declaraba, y las cuatro se quedaban el nombre en silencio.

    Es el caso 2 que Simplificacion planteo el 2026-09-21 —el mismo dato
    mostrado de nuevo— y cuya respuesta depende de una prueba en plataforma que
    aun no se ha hecho. Hasta entonces no se adivina: se reporta.
    """
    texto = MUESTRA.replace(
        "| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura, generado] Campo `@@monto_pago`. |",
        "| Monto | Number | Campo numérico | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura] `@@monto_pago`. |\n"
        "| Monto (confirmación) | Number | Solo lectura | No | Siempre visible | N/A | N/A | 76.00 | [Solo lectura] `@@monto_pago` — como constancia. |",
    )
    r = extraer(texto)
    h = [x for x in r.huecos if x.codigo == "DIC-09"]
    assert h, [x.codigo for x in r.huecos]
    assert "monto_pago" in h[0].mensaje


def test_la_columna_variable_repetida_tambien_se_reporta():
    # La otra via por la que entra un nombre: la columna Variable.
    texto = """
### Pantalla 1 — CIUDADANO — Datos

| Nombre del Campo | Variable | Tipo de Dato | Obligatorio | Descripción |
| --- | --- | --- | --- | --- |
| Estatus | estatus_tramite | String | Sí | El estatus. |
| Estatus (vista) | estatus_tramite | String | No | El mismo, mostrado de nuevo. |
"""
    r = extraer(texto)
    assert "DIC-09" in [x.codigo for x in r.huecos], [x.codigo for x in r.huecos]


def test_el_hueco_del_nombre_repetido_dice_donde_esta_el_gemelo():
    """Visto en la pantalla el 2026-09-21 con Reposicion cargada: la tarjeta
    decia «'@@estatus_tramite' lo declara mas de un campo» y nada mas. Con 41
    campos, encontrar el gemelo a mano es la misma busqueda que costo la tarde
    del 2026-09-18 y que ya se arreglo en el selector de campo.
    """
    texto = MUESTRA.replace(
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |",
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |\n"
        "| Sexo del cónyuge | String | Lista desplegable (select) | No | Siempre visible | N/A | Hombre · Mujer | Mujer | [Captura] Campo `@@sexo_testador`. |",
    )
    (h,) = [x for x in extraer(texto).huecos if x.codigo == "DIC-09"]
    # Las dos etiquetas, para reconocerlas en pantalla sin buscar.
    assert "Sexo" in h.mensaje and "Sexo del cónyuge" in h.mensaje
    # Y en que pantalla, por su NOMBRE: «p1» no le dice nada a quien documenta.
    assert "Captura del Aviso" in h.mensaje
    assert h.ubicacion == "p1", "la tarjeta se ancla igual a la pantalla"


def test_el_hueco_distingue_el_mismo_dato_de_dos_datos_distintos():
    """Los tres duplicados reales de los expedientes del 2026-09-21 eran dos
    cosas distintas: `@@estatus_tramite` (misma etiqueta y tipo: el mismo dato
    mostrado de nuevo) y `@@doc_certificado_final` (un `file` que sube el
    ciudadano contra un `text` que emite el tramite: dos datos que colisionan).
    La accion que toca es distinta, asi que el mensaje tambien.
    """
    distintos = MUESTRA.replace(
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |",
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |\n"
        "| Acta de nacimiento | Archivo | Carga de archivo | No | Siempre visible | N/A | N/A | N/A | [Captura] Campo `@@sexo_testador`. |",
    )
    (h,) = [x for x in extraer(distintos).huecos if x.codigo == "DIC-09"]
    assert "distinto" in h.mensaje.lower(), h.mensaje

    iguales = MUESTRA.replace(
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |",
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |\n"
        "| Sexo | String | Lista desplegable (select) | No | Siempre visible | N/A | Hombre · Mujer | Hombre | [Solo lectura] Campo `@@sexo_testador`. |",
    )
    (h2,) = [x for x in extraer(iguales).huecos if x.codigo == "DIC-09"]
    assert "mismo dato" in h2.mensaje.lower(), h2.mensaje


def test_un_nombre_propuesto_no_choca_con_uno_ya_declarado():
    """Regresion del 2026-09-21: al mover la deteccion de duplicados al punto
    donde el campo ya esta construido, los nombres DECLARADOS dejaron de
    registrarse en el mismo sitio que los propuestos, y `_unico` dejo de
    verlos. Resultado: una etiqueta «Modelo» derivaba a `modelo` aunque otra
    fila ya hubiera declarado `@@modelo`. Lo destapo Holograma Exento, que paso
    de 0 campos fantasma a 1.
    """
    texto = MUESTRA.replace(
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |",
        "| Sexo | String | Lista desplegable (select) | Sí | Siempre visible | N/A | Hombre · Mujer | Hombre | [Captura] Campo `@@sexo_testador`. |\n"
        "| Sexo testador | String | Campo de texto | No | Siempre visible | N/A | N/A | N/A | Sin nombre técnico declarado. |",
    )
    nombres = [c.nombre for p in extraer(texto).pantallas for c in p.campos]
    assert nombres.count("sexo_testador") == 1, nombres
    assert len(nombres) == len(set(nombres)), nombres


def test_el_choque_se_detecta_en_los_dos_ordenes():
    """El anterior cubre «declarado primero, derivado despues». Al reves —una
    etiqueta deriva `modelo` y una fila posterior declara `@@modelo`— el
    registro de duplicados no miraba, y salian dos campos iguales sin hueco.
    """
    texto = MUESTRA.replace(
        "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
        "| Monto pago | Number | Campo numérico | No | Siempre visible | N/A | N/A | N/A | Sin nombre técnico declarado. |\n"
        "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
    )
    r = extraer(texto)
    nombres = [c.nombre for p in r.pantallas for c in p.campos]
    assert len(nombres) == len(set(nombres)), nombres


# ── P-13: «max. N caracteres» no es una longitud exacta ──
#
# Lo reporto Simplificacion el 2026-09-21 entre los detalles, y era lo mas grave
# de su lista. `_LONGITUD` tomaba el numero y no miraba si delante decia «max.»:
# «max. 150 caracteres» salia como longitud EXACTA de 150, o sea que una razon
# social de 40 no se puede capturar. Once campos de Prorroga salian asi.
#
# La plataforma distingue las dos formas: en los exports autenticos conviven
# `exact_length[18]` y `max_length[9]`, y hasta `min_length[12]|max_length[13]`.

def _campo_con_limite(limite: str):
    texto = MUESTRA.replace(
        "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
        f"| CURP | String | Campo de texto (input) | Sí | Siempre visible | {limite} | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
    )
    return _campo(extraer(texto), "curp_testador")


def test_un_maximo_no_se_emite_como_longitud_exacta():
    c = _campo_con_limite("máx. 150 caracteres")
    assert c.longitud_exacta is None, "un máximo NO es una longitud exacta"
    assert c.longitud_max == 150


def test_las_otras_formas_de_decir_maximo():
    for limite in ("máximo 150 caracteres", "hasta 150 caracteres", "150 caracteres máx."):
        c = _campo_con_limite(limite)
        assert c.longitud_max == 150 and c.longitud_exacta is None, limite


def test_una_longitud_exacta_sigue_siendo_exacta():
    # El contrapeso: sin el, tratar TODO como maximo dejaria la CURP sin su
    # exact_length[18], que es lo que emiten los exports autenticos.
    for limite in ("18 caracteres", "exactamente 18 caracteres"):
        c = _campo_con_limite(limite)
        assert c.longitud_exacta == 18 and c.longitud_max is None, limite


def test_los_digitos_tambien_cuentan_como_longitud():
    # «exactamente 4 dígitos» de `modelo` no se leia: el patrón exigía la
    # palabra «caracteres» y salía sin longitud ninguna.
    c = _campo_con_limite("exactamente 4 dígitos")
    assert c.longitud_exacta == 4


def test_un_minimo_y_un_maximo_juntos():
    c = _campo_con_limite("entre 12 y 13 caracteres")
    assert c.longitud_min == 12 and c.longitud_max == 13


# ── P-14: «Condicional» es obligatorio cuando se muestra ──
#
# `obligatorio` salia de `.startswith("si")`, asi que «Condicional» se trataba
# como «No» y los 7 campos condicionales de Prorroga salian opcionales.
# La plataforma SI sabe expresarlo: en cuatro exports autenticos un campo
# condicional lleva `validacion: "required"` junto con su `dependiente_campo`.

def test_condicional_con_condicion_de_visibilidad_es_obligatorio():
    c = _campo(extraer(_VIS), "curp_solicitante")
    assert c.condicion_visible is not None, "la fila es «Condicional» y tiene condición"
    assert c.obligatorio is True


def test_condicional_sin_condicion_no_se_declara_obligatorio():
    # El contrapeso: sin condición no hay «cuando se muestra», así que marcarlo
    # obligatorio dejaría un campo que bloquea el envío sin decir por qué.
    texto = MUESTRA.replace(
        "| CURP | String | Campo de texto (input) | Sí | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
        "| CURP | String | Campo de texto (input) | Condicional | Siempre visible | 18 caracteres | N/A | GAGL651506HDFRNN01 | [Captura] Campo `@@curp_testador`. |",
    )
    assert _campo(extraer(texto), "curp_testador").obligatorio is False


def test_un_no_sigue_siendo_opcional():
    assert _campo(extraer(MUESTRA), "monto_pago").obligatorio is False


# ── P-15: el Ejemplo Real es ayuda para el ciudadano y se tiraba ──
#
# En Prorroga, `ayuda` iba vacia en los 36 campos. La plataforma la usa para la
# pista corta que se ve bajo el campo: en los exports autenticos hay
# «Ej. Secretaria de Finanzas, Obras Publicas» y «Teclea el CP para buscar».
# El Diccionario trae una columna «Ejemplo Real del Campo» que no leiamos.

def test_el_ejemplo_real_llega_como_ayuda():
    c = _campo(extraer(MUESTRA), "curp_testador")
    assert c.ayuda == "Ej. GAGL651506HDFRNN01"


def test_la_marca_de_ilustrativo_no_va_en_la_ayuda():
    # El Diccionario real escribe «OIPL800312HHGLRS05 *(ilustrativo)*»: esa
    # marca es una nota para ellos, no para el ciudadano.
    texto = MUESTRA.replace("GAGL651506HDFRNN01", "OIPL800312HHGLRS05 *(ilustrativo)*")
    assert _campo(extraer(texto), "curp_testador").ayuda == "Ej. OIPL800312HHGLRS05"


def test_un_ejemplo_vacio_o_N_A_no_inventa_ayuda():
    # El contrapeso: «N/A» como pista debajo del campo seria peor que nada.
    texto = MUESTRA.replace("| GAGL651506HDFRNN01 |", "| N/A |")
    assert _campo(extraer(texto), "curp_testador").ayuda is None


def test_un_endpoint_escrito_como_concepto_se_resuelve():
    """El Diccionario hibrido escribe `\\`mgem\\` (INEGI)`; el estandar, cuando
    trae columna Endpoint, escribe «Código Postal» o «CURP». El extractor solo
    entendia la primera forma."""
    from gpmc.extractores.diccionario import _clave_endpoint
    assert _clave_endpoint("`mgem` (INEGI)") == "mgem"
    assert _clave_endpoint("Código Postal") == "zip_codes"
    assert _clave_endpoint("CURP") == "consultacurpn"
    assert _clave_endpoint("N/A") is None


def test_un_endpoint_desconocido_sigue_llegando_como_texto():
    # El contrapeso: si lo desconocido volviera como None, `expediente.py`
    # lo saltaria (`if not c.endpoint: continue`) y el hueco API-01 «no esta
    # en el registro» desapareceria. Tiene que llegar como el token crudo.
    from gpmc.extractores.diccionario import _clave_endpoint
    assert _clave_endpoint("`consultarfc` (SAT)") == "consultarfc"
    assert _clave_endpoint("REPUVE") == "REPUVE"
