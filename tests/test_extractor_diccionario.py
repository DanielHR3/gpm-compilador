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
