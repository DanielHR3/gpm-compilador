"""El asistente recibe la carpeta del trámite y reparte solo cada archivo.

Banco de pruebas: los nombres reales de los seis expedientes que entrega el
equipo de Simplificación, con sus rarezas intactas (prefijos de orden, nombres
truncados a 8.3 por Windows, dobles espacios, dobles puntos, `.DS_Store`).
"""

import pytest

from gpmc.web.clasificador import clasificar


# Nombres tal como llegan, por expediente.
TESTAMENTO = [
    ".DS_Store",
    "1.-Análisis AS-IS.md",
    "2.-AVISOS DE TESTAMENTO.pdf",
    "3.-Propuesta TO-BE 1.md",
    "4.-Aviso de testamento notarias.pdf",
    "5.-Diccionario de Datos.md",
    "6.-Informe_de_aviso_de_testamento.pptx",
    "Documentos/1.- Archivo CSV.pdf",
    "Documentos/2.- Oficio de contestación.pdf",
]

PUBLICACION = [
    "1.-Análisis AS-IS.md",
    "2.-As Is avisos judiciales que deberán publicarse por disposición.pdf",
    "2.-As Is hasta media y una plana.pdf",
    "3.-Propuesta TO-BE.md",
    "4.-To Be Trámite general Periodico.pdf",
    "5.-Diccionario de Datos.md",
    "Documentos/Oficio de improcedencia de publicación.pdf",
]

PRORROGA = [
    "Análisis AS-IS Para Expediente Digital.md",
    "ASISSO~1.PDF",
    "Diccionario de Datos.md",
    "Documentos/(4) Oficio de Rechazó de Prórroga.pdf",
    "Propuesta TO-BE  para Expediente Digital.md",
    "TO-BEP~1.PDF",
]


def test_reparte_los_tres_insumos_de_un_expediente_real():
    a = clasificar(TESTAMENTO)
    assert a.as_is == "1.-Análisis AS-IS.md"
    assert a.to_be == "3.-Propuesta TO-BE 1.md"
    assert a.diccionario == "5.-Diccionario de Datos.md"


def test_el_md_le_gana_al_pdf_escaneado_del_mismo_insumo():
    """En los seis expedientes el AS-IS y el TO-BE vienen dos veces: el `.md`
    que se lee y su gemelo en PDF, que está escaneado. El PDF va a apoyo."""
    a = clasificar(PUBLICACION)
    assert a.as_is == "1.-Análisis AS-IS.md"
    assert a.to_be == "3.-Propuesta TO-BE.md"
    for pdf in ("2.-As Is hasta media y una plana.pdf",
                "4.-To Be Trámite general Periodico.pdf"):
        assert pdf in a.adjuntos, a.adjuntos


def test_un_nombre_truncado_por_windows_no_desplaza_al_md():
    a = clasificar(PRORROGA)
    assert a.as_is == "Análisis AS-IS Para Expediente Digital.md"
    assert a.to_be == "Propuesta TO-BE  para Expediente Digital.md"
    assert "ASISSO~1.PDF" in a.adjuntos
    assert "TO-BEP~1.PDF" in a.adjuntos


def test_los_pdf_de_Documentos_van_a_apoyo_no_a_plantilla():
    """Los 21 PDF de las carpetas `Documentos/` de los seis expedientes están
    escaneados: ninguno sirve como plantilla de documento de salida."""
    a = clasificar(TESTAMENTO)
    assert a.documentos == []
    assert "Documentos/2.- Oficio de contestación.pdf" in a.adjuntos


def test_un_Word_en_Documentos_si_es_plantilla_del_tramite():
    a = clasificar(["Diccionario de Datos.md",
                    "Documentos/Oficio de contestación.docx"])
    assert a.documentos == ["Documentos/Oficio de contestación.docx"]
    assert a.adjuntos == []


@pytest.mark.parametrize("carpeta", ["Documentos", "01 Documentos", "1.- Documentos"])
def test_la_carpeta_de_documentos_se_reconoce_pese_al_prefijo(carpeta):
    a = clasificar(["Diccionario de Datos.md", f"{carpeta}/Oficio.docx"])
    assert a.documentos == [f"{carpeta}/Oficio.docx"]


def test_el_html_de_vista_previa_va_a_su_zona():
    a = clasificar(["Diccionario de Datos.md",
                    "vista_previa_alta-de-avisos-test-ui.html"])
    assert a.vistas == "vista_previa_alta-de-avisos-test-ui.html"


def test_lo_que_no_es_insumo_se_ignora_pero_se_dice_cual():
    a = clasificar([".DS_Store", "Diccionario de Datos.md",
                    "build_full_gpm.py", "alta-de-avisos-v2.0.gpm"])
    assert set(a.ignorados) == {".DS_Store", "build_full_gpm.py",
                                "alta-de-avisos-v2.0.gpm"}
    assert a.adjuntos == []


def test_el_pptx_y_las_imagenes_son_apoyo_no_basura():
    a = clasificar(TESTAMENTO)
    assert "6.-Informe_de_aviso_de_testamento.pptx" in a.adjuntos
    assert "6.-Informe_de_aviso_de_testamento.pptx" not in a.ignorados


def test_ante_un_empate_real_no_adivina_y_lo_dice():
    """Mismo criterio que el hueco INS-02 del extractor: dos candidatos con la
    misma extensión y nadie que desempate -> la zona queda vacía."""
    a = clasificar(["Diccionario de Datos.md", "Diccionario de Datos copia.md"])
    assert a.diccionario is None
    assert any("Diccionario" in av for av in a.avisos), a.avisos
    # y no se pierden: quedan como apoyo para que la persona los vea
    assert len(a.adjuntos) == 2


def test_una_carpeta_sin_diccionario_lo_dice():
    a = clasificar(["1.-Análisis AS-IS.md"])
    assert a.diccionario is None
    assert any("Diccionario" in av for av in a.avisos), a.avisos


def test_los_seis_expedientes_reales_encuentran_su_diccionario():
    for nombres in (TESTAMENTO, PUBLICACION, PRORROGA):
        a = clasificar(nombres)
        assert a.diccionario is not None, nombres
        assert a.as_is is not None and a.to_be is not None, nombres


def test_ningun_archivo_se_pierde_por_el_camino():
    """Todo nombre que entra sale en exactamente una zona."""
    for nombres in (TESTAMENTO, PUBLICACION, PRORROGA):
        a = clasificar(nombres)
        salida = [x for x in (a.as_is, a.to_be, a.diccionario, a.vistas) if x]
        salida += a.adjuntos + a.documentos + a.ignorados
        assert sorted(salida) == sorted(nombres), nombres
        assert len(salida) == len(set(salida)), f"repetido en {nombres}"
