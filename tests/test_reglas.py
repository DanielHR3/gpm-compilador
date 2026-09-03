import pytest

from gpmc.nucleo import reglas
from gpmc.nucleo.manifiesto import Condicion


def test_emite_la_forma_laxa_por_omision():
    """Por omision se emite ==, la forma que usan los dos exports autenticos."""
    assert reglas.SINTAXIS_ESTRICTA is False
    assert reglas.emitir(Condicion(campo="correcto", igual="no")) == "@@correcto=='no'"


def test_emite_la_forma_estricta_si_se_activa(monkeypatch):
    monkeypatch.setattr(reglas, "SINTAXIS_ESTRICTA", True)
    assert reglas.emitir(Condicion(campo="correcto", igual="no")) == "@@correcto->value === 'no'"


@pytest.mark.parametrize("regla,valores,esperado", [
    ("@@correcto=='si'", {"correcto": "si"}, True),
    ("@@correcto=='si'", {"correcto": "no"}, False),
    ("@@correcto->value === 'si'", {"correcto": "si"}, True),
    ("@@correcto->value === 'si'", {"correcto": "no"}, False),
    ("@@oficio_tipo == ''", {"oficio_tipo": ""}, True),
    ("@@x=='a' && @@y=='b'", {"x": "a", "y": "b"}, True),
    ("@@x=='a' && @@y=='b'", {"x": "a", "y": "z"}, False),
    ("@@x!='a'", {"x": "b"}, True),
])
def test_evalua_ambas_sintaxis(regla, valores, esperado):
    """El evaluador acepta las dos formas: mientras la cuestion siga abierta,
    debe poder recorrer .gpm existentes escritos de cualquiera de las dos."""
    assert reglas.evaluar(regla, valores) is esperado


def test_campo_ausente_evalua_falso():
    assert reglas.evaluar("@@x=='a'", {}) is False


def test_extrae_los_campos_de_una_regla():
    assert reglas.campos_de("@@x=='a' && @@y!='b'") == ["x", "y"]
    assert reglas.campos_de("@@correcto->value === 'si'") == ["correcto"]
    assert reglas.campos_de("") == []


def test_regla_no_reconocida_lanza_error():
    with pytest.raises(ValueError, match="no reconocida"):
        reglas.evaluar("esto no es una regla", {})


def test_emite_la_forma_de_desigualdad():
    """Una condicion de visibilidad puede ser 'campo != valor'
    (@@tipo_solicitante != 'usuario' en busqueda-de-testamento)."""
    assert reglas.emitir(Condicion(campo="x", igual="a", operador="!=")) == "@@x!='a'"


def test_emite_desigualdad_en_forma_estricta(monkeypatch):
    monkeypatch.setattr(reglas, "SINTAXIS_ESTRICTA", True)
    assert reglas.emitir(Condicion(campo="x", igual="a", operador="!=")) == "@@x->value !== 'a'"
