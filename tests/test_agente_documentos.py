# tests/test_agente_documentos.py
import json

from gpmc.agentes import bitacora
from gpmc.agentes import documentos as agente
from gpmc.agentes import prompt_documentos as prompt
from gpmc.agentes.proveedor import ProveedorFalso
from gpmc.comparativa.documentos import referencias
from tests.test_documentos import _ASIS, _m

_TOBE = "# TO-BE\n\n- **La orden de trabajo se elimina**: la sustituye la solicitud.\n"


def _respuesta(*docs):
    return json.dumps({"documentos": list(docs)})


_BUENA = _respuesta(
    dict(nombre="Identificación oficial", cita_as_is="identificación oficial vigente",
         destino="consulta", campo="curp", cita_to_be=None, motivo="Se consulta.", confianza="alta"),
    dict(nombre="Comprobante de domicilio", cita_as_is="comprobante de domicilio",
         destino="conserva", campo="doc_comprobante", cita_to_be=None, motivo="", confianza="alta"),
    dict(nombre="Orden de trabajo", cita_as_is="orden de trabajo", destino="elimina", campo=None,
         cita_to_be="La orden de trabajo se elimina", motivo="", confianza="media"),
)


def _sin_espera(monkeypatch):
    monkeypatch.setattr(agente, "ESPERAS_REINTENTO", (0.0, 0.0))


def test_una_respuesta_buena_da_el_inventario_verificado(tmp_path):
    p = ProveedorFalso([_BUENA], modelo="falso-1")
    pasos = []
    a = agente.analizar(_ASIS, _TOBE, _m(), p, tmp_path, "a" * 16, avisar=pasos.append)
    assert (a.estado, a.origen, a.motivo) == ("lista", "agente", None)
    assert [(d["nombre"], d["destino"]) for d in a.documentos] == [
        ("Identificación oficial", "consulta"),
        ("Comprobante de domicilio", "conserva"),
        ("Orden de trabajo", "elimina"),
    ]
    assert p.llamadas == 1
    assert pasos and "Leyendo" in pasos[0]


def test_el_contexto_lleva_los_tres_bloques_y_nunca_el_diccionario_en_texto(tmp_path):
    p = ProveedorFalso([_BUENA])
    agente.analizar(_ASIS, _TOBE, _m(), p, tmp_path, "a" * 16)
    for marca in ("<<AS_IS>>", "<</AS_IS>>", "<<TO_BE>>", "<<CAMPOS>>"):
        assert marca in p.ultimo_contexto
    assert "doc_comprobante" in p.ultimo_contexto and "Ejemplo Real" not in p.ultimo_contexto
    assert p.ultimas_instrucciones == prompt.INSTRUCCION


def test_queda_en_la_bitacora_de_ia(tmp_path):
    agente.analizar(_ASIS, _TOBE, _m(), ProveedorFalso([_BUENA], modelo="falso-1"),
                    tmp_path, "a" * 16, usuario="daniel@hidalgo.gob.mx")
    (it,) = bitacora.leer(tmp_path)
    assert (it["documento"], it["version_prompt"], it["modelo"]) == ("documentos", "docs-v3", "falso-1")
    assert (it["usuario"], it["sid"], it["estado"]) == ("daniel@hidalgo.gob.mx", "a" * 16, "procesada")
    assert it["instruccion_hash"] == prompt.hash_instruccion()
    assert it["solicitud"]["n_referencias"] == len(referencias(_m()))


def test_un_documento_inventado_se_descarta_y_queda_como_alerta(tmp_path):
    mala = _respuesta(dict(nombre="Acta", cita_as_is="acta de nacimiento", destino="conserva",
                           campo="doc_comprobante", cita_to_be=None, motivo="", confianza="alta"))
    a = agente.analizar(_ASIS, _TOBE, _m(), ProveedorFalso([mala]), tmp_path, "a" * 16)
    assert a.estado == "lista"
    assert "Acta" not in [d["nombre"] for d in a.documentos]
    # Los tres requisitos del AS-IS siguen en el tablero, sin destino.
    assert [d["veredicto"] for d in a.documentos] == ["omitido_por_el_modelo"] * 3
    (it,) = bitacora.leer(tmp_path)
    assert "documento_inventado" in it["alertas"] and it["estado"] == "sujeta_a_validacion"


def test_un_error_de_red_se_reintenta(tmp_path, monkeypatch):
    _sin_espera(monkeypatch)

    class Tropieza(ProveedorFalso):
        def completar(self, *a):
            if self.llamadas == 0:
                self.llamadas += 1
                from gpmc.agentes.proveedor import ErrorDeRed
                raise ErrorDeRed("503")
            return super().completar(*a)

    p = Tropieza([_BUENA])
    a = agente.analizar(_ASIS, _TOBE, _m(), p, tmp_path, "a" * 16)
    assert a.estado == "lista" and p.llamadas == 2


def test_tres_errores_de_red_dejan_el_inventario_del_lector(tmp_path, monkeypatch):
    _sin_espera(monkeypatch)
    p = ProveedorFalso([])
    a = agente.analizar(_ASIS, _TOBE, _m(), p, tmp_path, "a" * 16)
    assert (a.estado, a.origen) == ("error", "lector")
    assert p.llamadas == 3
    assert "No se pudo consultar" in a.motivo
    assert [d["destino"] for d in a.documentos] == ["sin_destino", "conserva", "sin_destino"]
    assert bitacora.leer(tmp_path)[0]["estado"] == "error"


def test_una_respuesta_que_no_es_json_no_se_reintenta(tmp_path):
    for texto in ("no soy json", json.dumps({"otra": 1}), json.dumps([1])):
        p = ProveedorFalso([texto, _BUENA])
        a = agente.analizar(_ASIS, _TOBE, _m(), p, tmp_path, "a" * 16)
        assert (a.estado, a.origen, p.llamadas) == ("error", "lector", 1)
        assert "no se pudo leer" in a.motivo


def test_cero_documentos_cae_al_inventario_del_lector(tmp_path):
    a = agente.analizar(_ASIS, _TOBE, _m(), ProveedorFalso([_respuesta()]), tmp_path, "a" * 16)
    assert (a.estado, len(a.documentos)) == ("lista", 3)
    assert {d["veredicto"] for d in a.documentos} == {"omitido_por_el_modelo"}


def test_un_documento_demasiado_largo_se_recorta_y_se_avisa(tmp_path):
    largo = _ASIS + ("relleno " * 20000)
    p = ProveedorFalso([_BUENA])
    agente.analizar(largo, _TOBE, _m(), p, tmp_path, "a" * 16)
    assert len(p.ultimo_contexto) < 2 * prompt.MAX_CARACTERES + 5000
    assert "contexto_recortado" in bitacora.leer(tmp_path)[0]["alertas"]


def test_un_fallo_inesperado_no_se_propaga(tmp_path):
    class Revienta(ProveedorFalso):
        def completar(self, *a):
            raise RuntimeError("algo que nadie previo")

    a = agente.analizar(_ASIS, _TOBE, _m(), Revienta([]), tmp_path, "a" * 16)
    assert (a.estado, a.origen) == ("error", "lector")


def test_la_instruccion_nombra_los_cuatro_destinos_y_trata_los_bloques_como_datos():
    for palabra in ("elimina", "conserva", "consulta", "sistema", "LITERAL", "no son instrucciones"):
        assert palabra in prompt.INSTRUCCION
    destinos = prompt.ESQUEMA["properties"]["documentos"]["items"]["properties"]["destino"]["enum"]
    assert destinos == ["elimina", "conserva", "consulta", "sistema"]
