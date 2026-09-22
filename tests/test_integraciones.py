from gpmc.nucleo.integraciones import CATALOGOS, Catalogo, resolver


def test_los_catalogos_verificados_estan_registrados():
    assert set(CATALOGOS) == {"mgee", "mgem", "zip_codes", "consultacurpn"}


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

def test_los_sinonimos_se_resuelven_al_catalogo_base():
    assert resolver("INEGI").clave == "mgee"
    assert resolver("SEPOMEX").clave == "zip_codes"
    assert resolver("SIPUBEH").clave == "consultacurpn"
    # Ademas, las claves originales siguen resolviendo
    assert resolver("mgem").clave == "mgem"
    assert resolver("mgee").clave == "mgee"


def test_los_endpoints_con_token_se_reconocen():
    from gpmc.nucleo.integraciones import requiere_token
    assert requiere_token("SAT") is True
    assert requiere_token("tlaloc_curp") is True
    assert requiere_token("mgee") is False        # público, registrado
    assert requiere_token("cualquier_cosa") is False
    assert requiere_token(None) is False


def test_la_url_de_sipubeh_es_la_que_usa_la_plataforma():
    """Dos fuentes independientes coinciden, y ninguna es la que teniamos:

    - el export autentico `acceso-informacion-publica.gpm`, en el `extra` de su
      campo `api_curp_trigger`;
    - el «Catalogo Maestro de APIs» de la Direccion (2026-08-11), que ademas
      documenta la respuesta.

    Las dos dicen `/efirma/api/consultacurpn` con la CURP como **parametro de
    consulta**. Nosotros teniamos `/api/consultacurpn/` con la CURP pegada a la
    ruta: otro camino y otra forma de llamar. Habria fallado al primer intento.
    """
    from gpmc.nucleo.integraciones import CATALOGOS
    c = CATALOGOS["consultacurpn"]
    assert c.url.startswith("https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn")
    assert "curp=" in c.url, "la CURP viaja como parametro, no dentro de la ruta"


def test_sipubeh_declara_los_tres_campos_del_nombre():
    # SIPUBEH devuelve `nombres`, `apePat` y `apeMat` por separado. Un
    # autollenado que solo escriba `nombres` deja el tramite a medias.
    from gpmc.nucleo.integraciones import CATALOGOS
    c = CATALOGOS["consultacurpn"]
    assert c.campos_respuesta == ("nombres", "apePat", "apeMat")


def test_cada_entrada_dice_si_es_catalogo_o_consulta():
    """El catalogo de la Direccion mezcla dos cosas que el registro no
    distinguia: una LISTA para poblar un select (estados, colonias) y una
    CONSULTA que recibe un dato y devuelve otros para autollenar (CURP ->
    nombre). La segunda es un `api_ajax` y necesita `campos_respuesta`; la
    primera no. Sin el tipo, el compilador no sabe cual emitir."""
    from gpmc.nucleo.integraciones import CATALOGOS
    tipos = {clave: c.tipo for clave, c in CATALOGOS.items()}
    assert tipos == {
        "mgee": "catalogo", "mgem": "catalogo", "zip_codes": "catalogo",
        "consultacurpn": "consulta",
    }


def test_una_consulta_declara_que_devuelve_y_un_catalogo_no():
    from gpmc.nucleo.integraciones import CATALOGOS
    assert CATALOGOS["consultacurpn"].campos_respuesta == ("nombres", "apePat", "apeMat")
    assert CATALOGOS["mgee"].campos_respuesta == ()
