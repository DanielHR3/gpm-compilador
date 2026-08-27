from pathlib import Path

import pytest

from tests.conftest import WIKI, legible as _legible
from gpmc.nucleo.huecos import Hueco

from gpmc.extractores.mermaid import extraer



SIMPLE = """
flowchart TD
    classDef ciudadano fill:#E4EFEA
    classDef sistema fill:#E7EDF2

    Start([Inicia solicitud]):::ciudadano --> C1[Ciudadano: Capturar datos]:::ciudadano
    C1 --> D1{Sistema: ¿Datos completos? @@datos_correctos}:::sistema
    D1 -- no --> C1
    D1 -- sí --> F1[Sistema: Concluir]:::sistema
"""


def test_reconoce_las_formas_de_nodo():
    r = extraer(SIMPLE)
    por_id = {n.id: n for n in r.nodos}
    assert por_id["Start"].clase_nodo == "inicio_fin"
    assert por_id["C1"].clase_nodo == "tarea"
    assert por_id["D1"].clase_nodo == "compuerta"


def test_asigna_el_carril_desde_la_clase():
    r = extraer(SIMPLE)
    por_id = {n.id: n for n in r.nodos}
    assert por_id["C1"].actor == "ciudadano"
    assert por_id["D1"].actor == "sistema"


def test_limpia_el_texto_del_nodo():
    r = extraer("flowchart TD\n  A[Ciudadano: Capturar<br/>datos del<br/>vehículo]:::x\n  A --> B[Fin]:::x")
    a = next(n for n in r.nodos if n.id == "A")
    assert a.texto == "Capturar datos del vehículo", "quita <br/> y el prefijo de actor"


def test_extrae_las_aristas_con_y_sin_etiqueta():
    r = extraer(SIMPLE)
    sin = [a for a in r.aristas if a.etiqueta is None]
    con = [a for a in r.aristas if a.etiqueta]
    assert ("Start", "C1") in [(a.de, a.a) for a in sin]
    assert {a.etiqueta for a in con} == {"no", "sí"}


def test_detecta_el_campo_referenciado_en_una_compuerta():
    r = extraer(SIMPLE)
    d1 = next(n for n in r.nodos if n.id == "D1")
    assert d1.campos == ["datos_correctos"]


def test_reporta_hueco_cuando_la_compuerta_no_nombra_campo():
    r = extraer("flowchart TD\n  A[X]:::c --> D{¿Procede?}:::c\n  D -- sí --> B[Y]:::c\n  D -- no --> A")
    mmd04 = [h for h in r.huecos if h.codigo == "MMD-04"]
    assert mmd04, r.huecos
    assert mmd04[0].nivel == "falta_dato"


def test_reporta_hueco_cuando_un_nodo_no_declara_carril():
    r = extraer("flowchart TD\n  A[Sin clase] --> B[Fin]:::c")
    mmd03 = [h for h in r.huecos if h.codigo == "MMD-03"]
    assert mmd03, r.huecos
    assert mmd03[0].nivel == "falta_dato"


def test_todos_los_huecos_de_mermaid_son_Hueco():
    r = extraer("flowchart TD\n  A[Sin clase] --> B[Fin]:::c")
    assert all(isinstance(h, Hueco) for h in r.huecos)


def test_normaliza_los_carriles_sinonimos():
    from gpmc.extractores.mermaid import normalizar_actor
    for v in ("usuaria", "ciudadano", "usuario", "solicitante"):
        assert normalizar_actor(v) == "ciudadano"
    assert normalizar_actor("sistema") == "sistema"
    assert normalizar_actor("coinhi") == "coinhi", "un carril propio se conserva"


@pytest.mark.parametrize("expediente", [
    "elesvan/Constancia de No Infracción Vehicular Ambiental",
    "anita/Alta de Avisos de Testamento",
])
def test_parsea_diagramas_reales_del_wiki(expediente):
    ruta = WIKI / expediente / "Propuesta TO-BE.md"
    if not _legible(ruta):
        pytest.skip(f"expediente no disponible: {expediente}")
    import re
    texto = ruta.read_text(encoding="utf-8")
    bloques = re.findall(r"```mermaid(.*?)```", texto, re.S)
    assert bloques, "el TO-BE no trae diagrama Mermaid"
    r = extraer(bloques[0])
    assert len(r.nodos) >= 5, f"solo {len(r.nodos)} nodos"
    assert len(r.aristas) >= 5
    assert any(n.clase_nodo == "tarea" for n in r.nodos)
    ids = {n.id for n in r.nodos}
    for a in r.aristas:
        assert a.de in ids and a.a in ids, f"arista a nodo inexistente: {a.de}->{a.a}"
