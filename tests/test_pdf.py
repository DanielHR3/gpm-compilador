"""Lectura de un Diccionario entregado en PDF (con texto, no escaneado).

A diferencia del .docx —donde la tabla es explicita en el XML— en un PDF las
columnas se deducen de la posicion del texto. Por eso todo se ancla en la
cabecera del propio documento, y si no aparece se falla en voz alta en vez de
partir las filas a ojo.
"""
import pytest

from gpmc.extractores.pdf import a_markdown_desde_texto, columnas_por_rios


# Salida literal de pypdf en modo trazado sobre el «Diccionario de datos de
# Búsqueda de Testamento». Construir el caso a mano no sirve: las columnas de un
# PDF real no estan donde uno las imagina.
REAL = (
    "Nombre del        Tipo de         Límite de              Descripción                     Ejemplo\n"
    "   campo            dato        caracteres y\n"
    "                              especiﬁcacione\n"
    "                                       s\n"
    "\n"
    "Folio             Alfanu      30                    Número consecutivo          BT-2026-00001\n"
    "                  mérico                            generado\n"
    "                                                    automáticamente\n"
    "                                                    por el sistema\n"
    "\n"
    "Fecha de          Date        Valor deﬁnido         Fecha en que se             DD/MM/AAAA\n"
    "registro                                            registra la solicitud"
)


def test_las_columnas_salen_de_los_rios_de_espacios_no_de_la_cabecera():
    """El PDF centra los titulos sobre la columna y alinea los datos a la
    izquierda: «Límite de» empieza en la 34 y su dato «30» en la 30."""
    cortes = columnas_por_rios(REAL.splitlines())

    # Cinco columnas, y el corte del limite cae donde estan los DATOS.
    assert len(cortes) == 5
    assert 30 in cortes


def test_sin_una_cabecera_reconocible_se_falla_en_voz_alta():
    with pytest.raises(ValueError, match="cabecera"):
        a_markdown_desde_texto("una hoja suelta\nsin tabla ninguna\n")


def test_una_fila_partida_en_varias_lineas_se_recompone():
    """El PDF separa registros con una linea en blanco y parte las celdas largas
    dentro del registro. «Fecha de» / «registro» es UNA fila, y las dos lineas
    traen primera columna: agrupar por lineas en blanco es la senal fiable."""
    md = a_markdown_desde_texto(REAL)

    assert (
        "| Fecha de registro | Date | Valor definido "
        "| Fecha en que se registra la solicitud | DD/MM/AAAA |"
    ) in md
    assert (
        "| Número consecutivo generado automáticamente por el sistema |"
    ) in md


def test_una_letra_suelta_es_el_rabo_de_una_palabra_partida():
    """«especiﬁcacione» + «s» en lineas distintas es una sola palabra."""
    md = a_markdown_desde_texto(REAL)

    assert "especificaciones" in md
    assert "especificacione s" not in md


def test_las_ligaduras_del_pdf_se_normalizan():
    """Un PDF escribe «especiﬁcaciones» con la ligadura U+FB01; sin normalizar,
    ese texto viaja al .gpm y no casa con nada."""
    md = a_markdown_desde_texto(REAL)

    assert "definido" in md
    assert "ﬁ" not in md
