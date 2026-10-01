"""Trazabilidad historia -> criterio -> prueba (scripts/trazabilidad.py).

Los criterios de aceptacion de la boveda citan pruebas por nombre. Si una
prueba se renombra, la cita queda muerta sin que nadie lo note: el script la
detecta y arma la matriz.
"""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("trazabilidad", RAIZ / "scripts" / "trazabilidad.py")
traz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traz)


HU = """# HU-ANA-09 - Algo

## Criterios de aceptacion

- [x] **CA1.** Hace una cosa. `test_existe_uno`.
- [ ] **CA2.** Hace otra, con dos lineas
  de texto. `test_existe_dos`, `test_ya_no_existe`.
- [x] **CA3.** Sin prueba citada: se mide en plataforma.

## Notas

`test_fuera_de_los_criterios` no cuenta.
"""


def test_lee_criterios_con_marca_y_pruebas_citadas():
    criterios = traz.criterios_de(HU)
    assert [c.clave for c in criterios] == ["CA1", "CA2", "CA3"]
    assert [c.hecho for c in criterios] == [True, False, True]
    assert criterios[1].pruebas == ["test_existe_dos", "test_ya_no_existe"]
    assert criterios[2].pruebas == []


def test_lo_citado_fuera_de_los_criterios_no_cuenta():
    citadas = [p for c in traz.criterios_de(HU) for p in c.pruebas]
    assert "test_fuera_de_los_criterios" not in citadas


def test_pruebas_del_repo_incluye_funciones_y_metodos(tmp_path):
    (tmp_path / "test_a.py").write_text(
        "def test_uno():\n    pass\n\nclass TestX:\n    def test_dos(self):\n        pass\n"
        "\nasync def test_tres():\n    pass\n",
        encoding="utf-8",
    )
    assert traz.pruebas_del_repo(tmp_path) == {"test_uno", "test_dos", "test_tres"}


def test_una_cita_muerta_se_reporta_y_la_matriz_la_marca(tmp_path):
    boveda = tmp_path / "boveda"
    (boveda / "HU-ANA-09").mkdir(parents=True)
    (boveda / "HU-ANA-09" / "HU-ANA-09.md").write_text(HU, encoding="utf-8")
    historias = traz.leer_boveda(boveda)
    existentes = {"test_existe_uno", "test_existe_dos"}

    muertas = traz.citas_muertas(historias, existentes)
    assert muertas == [("HU-ANA-09", "CA2", "test_ya_no_existe")]

    md = traz.matriz(historias, existentes)
    assert "HU-ANA-09" in md
    assert "`test_ya_no_existe` ⚠️ no existe" in md
    assert "Generado por scripts/trazabilidad.py" in md


def test_solo_lee_la_nota_principal_de_cada_historia(tmp_path):
    boveda = tmp_path / "boveda"
    (boveda / "HU-DGT-01").mkdir(parents=True)
    (boveda / "HU-DGT-01" / "HU-DGT-01.md").write_text(HU, encoding="utf-8")
    (boveda / "HU-DGT-01" / "02_Plan_Backend.md").write_text(
        "- [x] **CA9.** `test_del_plan`\n", encoding="utf-8"
    )
    historias = traz.leer_boveda(boveda)
    assert [h.id for h in historias] == ["HU-DGT-01"]
    assert all(c.clave != "CA9" for c in historias[0].criterios)


def test_las_tablas_del_expediente_aportan_pruebas_a_sus_criterios(tmp_path):
    """Las HU de la fase 1 citan la evidencia en una tabla del plan, no en el criterio."""
    boveda = tmp_path / "boveda"
    (boveda / "HU-DGT-01").mkdir(parents=True)
    (boveda / "HU-DGT-01" / "HU-DGT-01.md").write_text(HU, encoding="utf-8")
    (boveda / "HU-DGT-01" / "02_Plan_Backend.md").write_text(
        "| CA | Tarea | Prueba |\n| --- | --- | --- |\n"
        "| CA3 | Tarea 1 | `test_de_la_tabla` |\n"
        "| CA9 | Huerfano | `test_sin_criterio` |\n",
        encoding="utf-8",
    )
    (h,) = traz.leer_boveda(boveda)
    por_clave = {c.clave: c.pruebas for c in h.criterios}
    assert por_clave["CA3"] == ["test_de_la_tabla"]
    assert "CA9" not in por_clave
