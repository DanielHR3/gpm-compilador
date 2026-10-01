# tests/test_agente_comparativa.py
"""El agente de la comparativa: dos llamadas, ninguna toca la red."""
import json

from gpmc.agentes import bitacora
from gpmc.agentes import comparativa as agente
from gpmc.agentes import prompt_comparativa as prompt
from gpmc.agentes.proveedor import ProveedorFalso
from tests.test_comparativa import _m
from tests.test_verificar_comparativa import _ASIS, _TOBE, _lado, _mejora

_FALTAN = [("visitas", "antes"), ("visitas", "despues"), ("tiempo", "despues")]
_EVIDENCIA = json.dumps({"lados": [
    _lado("visitas", "antes", ("Ir a ventanilla", "Usuario lo lleva a Ventanilla."),
          ("Ir al banco", "Usuario recibe el F7 y paga (en banco)."), motivo="Va dos veces."),
    _lado("visitas", "despues", ("Ninguna", "no queda ninguna visita presencial residual"),
          ninguno=True),
    _lado("tiempo", "despues", ("2 días hábiles", "Tiempo de respuesta: 2 días hábiles")),
]})
_MEJORAS = json.dumps({"mejoras": [
    _mejora(campo=None, cita="El ciudadano captura su CURP una sola vez", titulo="Validar la CURP",
            tipo="captura", servicio="consultacurpn")]})


def _sin_espera(monkeypatch):
    monkeypatch.setattr(agente, "ESPERAS_REINTENTO", (0.0, 0.0))


def _analizar(p, tmp_path, faltan=_FALTAN, **k):
    return agente.analizar(_ASIS, _TOBE, _m(), faltan, p, tmp_path, "a" * 16, **k)


def test_dos_llamadas_dan_evidencia_verificada_y_puntos_de_mejora(tmp_path):
    p = ProveedorFalso([_EVIDENCIA, _MEJORAS], modelo="falso-1")
    pasos = []
    a = _analizar(p, tmp_path, avisar=pasos.append)
    assert (a.estado, a.motivo, a.modelo, p.llamadas) == ("lista", None, "falso-1", 2)
    assert [(x["metrica"], x["lado"], len(x["evidencias"])) for x in a.propuestas] == [
        ("visitas", "antes", 2), ("visitas", "despues", 1), ("tiempo", "despues", 1)]
    assert a.propuestas[0]["motivo"] == "Va dos veces."
    assert [(x["titulo"], x["requiere"]) for x in a.mejoras] == [
        ("Validar la CURP", "servicio_publico")]
    assert len(pasos) >= 2 and "AS-IS" in pasos[0]


def test_el_contexto_lleva_los_lados_que_faltan_y_el_catalogo_publico(tmp_path):
    capturados = []

    class Espia(ProveedorFalso):
        def completar(self, instrucciones, contexto, esquema):
            capturados.append((instrucciones, contexto, esquema))
            return super().completar(instrucciones, contexto, esquema)

    _analizar(Espia([_EVIDENCIA, _MEJORAS]), tmp_path)
    (i1, c1, e1), (i2, c2, e2) = capturados
    assert i1 == prompt.INSTRUCCION_EVIDENCIA and e1 == prompt.ESQUEMA_EVIDENCIA
    assert "<<FALTAN>>\nvisitas antes\nvisitas despues\ntiempo despues\n<</FALTAN>>" in c1
    assert "<<AS_IS>>" in c1 and "<<TO_BE>>" in c1
    assert i2 == prompt.INSTRUCCION_MEJORAS and e2 == prompt.ESQUEMA_MEJORAS
    assert "<<CAMPOS>>" in c2 and "doc_0 | archivo_ciudadano" in c2
    assert "consultacurpn | Datos de la persona a partir de su CURP" in c2
    # Lo de pago o convenio no se le ofrece al modelo como si estuviera disponible.
    assert "repuve" not in c2.split("<<SERVICIOS>>")[1].lower()


def test_sin_lados_que_falten_solo_se_piden_las_mejoras(tmp_path):
    p = ProveedorFalso([_MEJORAS])
    a = _analizar(p, tmp_path, faltan=[])
    assert (a.estado, p.llamadas, a.propuestas, len(a.mejoras)) == ("lista", 1, [], 1)


def test_la_bitacora_registra_las_dos_interacciones_con_su_version(tmp_path):
    _analizar(ProveedorFalso([_EVIDENCIA, _MEJORAS]), tmp_path, usuario="ana@hidalgo.gob.mx")
    filas = bitacora.leer(tmp_path)
    assert [(f["version_prompt"], f["documento"], f["usuario"]) for f in filas] == [
        (prompt.VERSION_EVIDENCIA, "comparativa", "ana@hidalgo.gob.mx"),
        (prompt.VERSION_MEJORAS, "mejoras", "ana@hidalgo.gob.mx")]
    assert filas[0]["instruccion_hash"] == prompt.hash_de(prompt.INSTRUCCION_EVIDENCIA)
    assert filas[0]["estado"] == "procesada"


def test_lo_que_la_verificacion_descarta_queda_como_alerta_en_la_bitacora(tmp_path):
    mala = json.dumps({"lados": [_lado("visitas", "antes", ("Ir", "frase que nadie escribió nunca"))]})
    a = _analizar(ProveedorFalso([mala, _MEJORAS]), tmp_path)
    assert a.estado == "lista" and a.propuestas == [] and "cita_inventada" in a.alertas
    assert bitacora.leer(tmp_path)[0]["estado"] == "sujeta_a_validacion"


def test_si_la_red_falla_en_la_primera_llamada_no_se_gasta_la_segunda(tmp_path, monkeypatch):
    _sin_espera(monkeypatch)
    p = ProveedorFalso([])
    a = _analizar(p, tmp_path)
    assert (a.estado, a.motivo) == ("error", agente.MOTIVO_RED)
    assert p.llamadas == 3 and a.propuestas == [] and a.mejoras == []
    assert bitacora.leer(tmp_path)[0]["estado"] == "error"


def test_si_falla_solo_la_segunda_llamada_las_cifras_quedan(tmp_path, monkeypatch):
    _sin_espera(monkeypatch)
    a = _analizar(ProveedorFalso([_EVIDENCIA]), tmp_path)
    assert a.estado == "lista" and len(a.propuestas) == 3 and a.mejoras == []
    assert "mejoras_no_disponibles" in a.alertas and a.motivo == agente.MOTIVO_SIN_MEJORAS


def test_una_respuesta_ilegible_no_tira_la_otra_llamada(tmp_path):
    a = _analizar(ProveedorFalso(["{esto no es json", _MEJORAS]), tmp_path)
    assert a.estado == "lista" and a.propuestas == [] and len(a.mejoras) == 1
    assert "respuesta_invalida" in a.alertas
    a = _analizar(ProveedorFalso(["{", "[]"]), tmp_path)
    assert (a.estado, a.motivo) == ("error", agente.MOTIVO_INVALIDA)


def test_nada_escapa_del_agente(tmp_path):
    class Roto:
        nombre = "roto"

        def completar(self, *a, **k):
            raise RuntimeError("boom")

    a = _analizar(Roto(), tmp_path)
    assert (a.estado, a.motivo) == ("error", agente.MOTIVO_INESPERADO)


def test_cambiar_una_instruccion_obliga_a_cambiar_su_version():
    # Si esta prueba falla, sube VERSION_* en prompt_comparativa y actualiza el hash aqui.
    assert (prompt.VERSION_EVIDENCIA, prompt.hash_de(prompt.INSTRUCCION_EVIDENCIA)) == (
        "cmp-v1", "d94723c3f03f395f")
    assert (prompt.VERSION_MEJORAS, prompt.hash_de(prompt.INSTRUCCION_MEJORAS)) == (
        "mejoras-v2", "f38e6ed14352b4e0")
