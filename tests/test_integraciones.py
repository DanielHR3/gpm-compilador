from gpmc.nucleo.integraciones import CATALOGOS, Catalogo, resolver


def test_los_tres_catalogos_verificados_estan_registrados():
    assert set(CATALOGOS) == {"mgee", "mgem", "zip_codes"}


def test_mgee_trae_la_url_y_el_mapeo_del_export_autentico():
    c = resolver("mgee")
    assert c.url == "https://gaia.inegi.org.mx/wscatgeo/v2/mgee"
    assert c.nodo == "datos"
    assert c.etiqueta == "nomgeo"
    assert c.valor == "cvegeo"
    assert c.requiere_padre is False


def test_mgem_requiere_padre_e_interpola_su_nombre():
    c = resolver("mgem")
    assert c.requiere_padre is True
    assert c.url_para("estado_sol") == (
        "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/@@estado_sol"
    )


def test_zip_codes_interpola_en_el_query_string():
    c = resolver("zip_codes")
    assert c.url_para("cp_sol") == (
        "https://sepomex.kurenn.dev/api/v1/zip_codes?zip_code=@@cp_sol"
    )
    assert c.nodo == "zip_codes"
    assert c.etiqueta == c.valor == "d_asenta"


def test_resolver_tolera_mayusculas_y_espacios():
    assert resolver("  MGEE ") is CATALOGOS["mgee"]


def test_un_endpoint_desconocido_devuelve_none_sin_reventar():
    assert resolver("consultarfc") is None
    assert resolver("") is None
    assert resolver(None) is None


def test_un_catalogo_sin_padre_ignora_el_argumento():
    assert resolver("mgee").url_para(None) == resolver("mgee").url_para("lo_que_sea")
