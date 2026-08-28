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


def test_el_diccionario_hibrido_produce_selects():
    r = extraer(_DICC_HIBRIDO)
    tipos = {c.nombre: c.tipo for c in r.pantallas[0].campos}
    assert tipos["estado_sol"] == "select"
    assert tipos["municipio_sol"] == "select"
    assert tipos["cp_sol"] == "text"
