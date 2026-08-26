from pathlib import Path

from gpmc.cli import main
from gpmc.nucleo.formato import leer

EJEMPLO = Path(__file__).parent.parent / "ejemplos" / "vinculacion-organismos.yaml"


def test_compilar_produce_un_gpm(tmp_path, capsys):
    destino = tmp_path / "salida.gpm"
    assert main(["compilar", str(EJEMPLO), "-o", str(destino)]) == 0
    assert destino.exists()
    assert leer(destino)["homoclave"] == "SEDECO/02"
    assert "sin hallazgos" in capsys.readouterr().out.lower()


def test_compilar_falla_con_un_manifiesto_invalido(tmp_path, capsys):
    malo = tmp_path / "malo.yaml"
    malo.write_text("version: 1\ntramite: {nombre: X}\n", encoding="utf-8")
    assert main(["compilar", str(malo), "-o", str(tmp_path / "x.gpm")]) == 2
    assert "error" in capsys.readouterr().err.lower()


def test_validar_un_gpm_sano_devuelve_cero(tmp_path):
    destino = tmp_path / "s.gpm"
    main(["compilar", str(EJEMPLO), "-o", str(destino)])
    assert main(["validar", str(destino)]) == 0


def test_validar_un_gpm_defectuoso_devuelve_uno(gpm_del_equipo):
    """Al menos uno de los .gpm del equipo tiene un folio defectuoso."""
    codigos = [main(["validar", str(r)]) for r in gpm_del_equipo]
    assert 1 in codigos, "ninguno de los .gpm del equipo produjo hallazgos bloqueantes"


def test_sin_argumentos_devuelve_dos(capsys):
    assert main([]) == 2
