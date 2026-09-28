# tests/test_verificar_documentos.py
from gpmc.agentes.verificar_documentos import verificar
from gpmc.comparativa.documentos import Referencia

_ASIS = ("# Análisis AS-IS\n\n- **Requisitos:**\n"
         "  - Vehículo nuevo: tarjeta de circulación, factura, identificación oficial\n"
         "  - Orden de trabajo llenada a mano\n")
_TOBE = ("# TO-BE\n\n- **La orden de trabajo llenada a mano se elimina**: la sustituye la "
         "solicitud digital.\n- La identificación se valida con RENAPO.\n")
_REFS = [
    Referencia("doc_tarjeta", "Tarjeta de circulación", "Solicitud", "Ciudadano", "archivo_ciudadano"),
    Referencia("doc_factura", "Factura", "Solicitud", "Ciudadano", "archivo_ciudadano"),
    Referencia("curp", "CURP", "Solicitud", "Ciudadano", "consulta"),
    Referencia("doc_constancia", "Constancia", "Emisión", "Funcionario", "archivo_otro"),
    Referencia("oficio", "Oficio", "", "", "accion_documento"),
]


def _item(**k):
    base = dict(nombre="Tarjeta de circulación", cita_as_is="tarjeta de circulación",
                destino="conserva", campo="doc_tarjeta", cita_to_be=None,
                motivo="La sigue adjuntando.", confianza="alta")
    base.update(k)
    return base


def _uno(item, as_is=_ASIS, to_be=_TOBE):
    docs, alertas = verificar([item], as_is, to_be, _REFS)
    return next((d for d in docs if d.origen == "agente"), None), alertas


def test_una_propuesta_buena_pasa_entera():
    d, alertas = _uno(_item())
    assert (d.destino, d.campo, d.veredicto, d.estado) == ("conserva", "doc_tarjeta", "", "propuesto")
    assert (d.motivo, d.motivo_de, d.confianza, d.origen) == ("La sigue adjuntando.", "ia", "alta", "agente")


def test_una_linea_del_as_is_se_puede_partir_en_varios_documentos():
    docs, _ = verificar([
        _item(),
        _item(nombre="Factura", cita_as_is="factura", campo="doc_factura"),
        _item(nombre="Identificación oficial", cita_as_is="identificación oficial",
              destino="consulta", campo="curp"),
        _item(nombre="Orden de trabajo", cita_as_is="Orden de trabajo llenada a mano",
              destino="elimina", campo=None,
              cita_to_be="La orden de trabajo llenada a mano se elimina"),
    ], _ASIS, _TOBE, _REFS)
    assert [(d.nombre, d.destino, d.veredicto) for d in docs] == [
        ("Tarjeta de circulación", "conserva", ""),
        ("Factura", "conserva", ""),
        ("Identificación oficial", "consulta", ""),
        ("Orden de trabajo", "elimina", ""),
    ]


def test_la_cita_se_compara_sin_acentos_mayusculas_ni_espacios():
    d, _ = _uno(_item(cita_as_is="TARJETA   de  Circulacion"))
    assert d is not None and d.veredicto == ""


def test_un_documento_con_cita_del_as_is_inventada_se_descarta():
    d, alertas = _uno(_item(nombre="Acta de nacimiento", cita_as_is="acta de nacimiento certificada"))
    assert d is None
    assert "documento_inventado" in alertas


def test_una_cita_vacia_o_de_dos_letras_no_vale():
    for cita in ("", "de", None):
        d, alertas = _uno(_item(cita_as_is=cita))
        assert d is None and "documento_inventado" in alertas


def test_una_cita_del_to_be_parafraseada_deja_la_tarjeta_sin_destino():
    d, alertas = _uno(_item(nombre="Orden de trabajo", cita_as_is="Orden de trabajo llenada a mano",
                            destino="elimina", campo=None,
                            cita_to_be="Se suprime la orden de trabajo manual"))
    assert (d.destino, d.veredicto, d.cita_to_be) == ("sin_destino", "cita_inventada", "")
    assert "cita_inventada" in alertas


def test_un_campo_que_no_existe():
    d, _ = _uno(_item(campo="doc_que_no_existe"))
    assert (d.destino, d.veredicto, d.campo) == ("sin_destino", "campo_inventado", "")


def test_conserva_exige_un_archivo_del_ciudadano():
    for campo in ("doc_constancia", "curp", "oficio", None):
        d, _ = _uno(_item(campo=campo))
        assert (d.destino, d.veredicto) == ("sin_destino", "evidencia_insuficiente"), campo


def test_consulta_vale_con_campo_de_consulta_o_con_frase_del_to_be():
    d, _ = _uno(_item(destino="consulta", campo="curp"))
    assert d.veredicto == ""
    d, _ = _uno(_item(destino="consulta", campo=None,
                      cita_to_be="La identificación se valida con RENAPO"))
    assert d.veredicto == ""
    d, _ = _uno(_item(destino="consulta", campo="doc_tarjeta"))
    assert (d.destino, d.veredicto) == ("sin_destino", "evidencia_insuficiente")


def test_sistema_vale_con_accion_archivo_de_otro_actor_o_frase():
    for campo in ("oficio", "doc_constancia"):
        d, _ = _uno(_item(destino="sistema", campo=campo))
        assert d.veredicto == "", campo
    d, _ = _uno(_item(destino="sistema", campo="doc_tarjeta"))
    assert d.veredicto == "evidencia_insuficiente"


def test_elimina_sin_frase_del_to_be_no_tiene_fundamento():
    d, _ = _uno(_item(destino="elimina", campo=None, cita_to_be=None))
    assert (d.destino, d.veredicto) == ("sin_destino", "sin_fundamento")


def test_un_destino_que_no_existe():
    d, _ = _uno(_item(destino="fusiona"))
    assert (d.destino, d.veredicto) == ("sin_destino", "destino_invalido")


def test_un_mismo_campo_no_respalda_dos_documentos():
    docs, _ = verificar([_item(), _item(nombre="Factura", cita_as_is="factura")],
                        _ASIS, _TOBE, _REFS)
    assert [(d.nombre, d.veredicto) for d in docs if d.origen == "agente"] == [
        ("Tarjeta de circulación", ""), ("Factura", "campo_repetido")]


def test_el_mismo_documento_dos_veces_cuenta_una():
    docs, alertas = verificar([_item(), _item(campo="doc_factura")], _ASIS, _TOBE, _REFS)
    assert len([d for d in docs if d.origen == "agente"]) == 1
    assert "duplicado" in alertas


def test_lo_que_el_modelo_omite_entra_igual_al_tablero():
    docs, alertas = verificar([_item()], _ASIS, _TOBE, _REFS)
    omitidos = [d for d in docs if d.veredicto == "omitido_por_el_modelo"]
    assert [d.nombre for d in omitidos] == ["Orden de trabajo llenada a mano"]
    assert (omitidos[0].destino, omitidos[0].origen) == ("sin_destino", "lector")
    assert "requisito_omitido" in alertas


def test_filas_que_no_son_objetos_o_sin_nombre_se_saltan():
    docs, alertas = verificar(["texto", None, {"cita_as_is": "factura"}, _item()],
                              _ASIS, _TOBE, _REFS)
    assert len([d for d in docs if d.origen == "agente"]) == 1
    assert alertas.count("respuesta_invalida") == 3


def test_el_motivo_se_corta_y_la_confianza_se_normaliza():
    d, _ = _uno(_item(motivo="x" * 500, confianza="altísima"))
    assert len(d.motivo) == 300 and d.confianza == "baja"


def test_el_nucleo_y_la_comparativa_no_importan_de_agentes():
    import ast
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1] / "src" / "gpmc"
    for ruta in sorted((raiz / "comparativa").glob("*.py")):
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom):
                assert not (nodo.module or "").startswith("gpmc.agentes"), ruta.name
