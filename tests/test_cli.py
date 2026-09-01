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


_DICC = """### Pantalla 1 — Solicitante — Datos

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |
| CURP | Texto | Input | Sí | La CURP @@curp |
| Nombre | Texto | Input | Sí | El nombre del solicitante |
"""


def _exp(tmp_path):
    c = tmp_path / "exp"
    c.mkdir()
    (c / "5.-Diccionario de Datos.md").write_text(_DICC, encoding="utf-8")
    return c


def test_extraer_agrupa_huecos_por_nivel(tmp_path, capsys):
    salida = tmp_path / "t.yaml"
    codigo = main(["extraer", str(_exp(tmp_path)), "-o", str(salida)])
    out = capsys.readouterr().out
    assert codigo == 0
    assert "BLOQUEANTE" in out            # falta TO-BE
    assert "POR CONFIRMAR" in out         # 'Nombre' sin @@
    assert "[INS-01]" in out


def test_extraer_nombre_sobrescribe_el_del_expediente(tmp_path):
    """P-03: sin AS-IS el nombre cae al de la carpeta ('exp'), que se filtra al
    nombre del archivo descargado y al proceso_id derivado. El asistente web ya pide
    el nombre en la portada; --nombre da ese mismo camino a la CLI. Es un override
    explícito: si el analista lo pasa, gana."""
    import yaml
    salida = tmp_path / "t.yaml"
    codigo = main(["extraer", str(_exp(tmp_path)), "-o", str(salida), "--nombre", "Mi Trámite"])
    assert codigo == 0
    m = yaml.safe_load(salida.read_text(encoding="utf-8"))
    assert m["tramite"]["nombre"] == "Mi Trámite"


def test_extraer_sin_nombre_no_inventa(tmp_path):
    """Sin --nombre no se toca el nombre que derivó el extractor: --nombre suple, no
    fabrica por su cuenta."""
    import yaml
    salida = tmp_path / "t.yaml"
    main(["extraer", str(_exp(tmp_path)), "-o", str(salida)])
    m = yaml.safe_load(salida.read_text(encoding="utf-8"))
    assert m["tramite"]["nombre"] == "exp"  # el nombre de la carpeta


def test_bandera_huecos_no_trunca(tmp_path, capsys):
    # Diccionario con muchos campos sin @@ para forzar truncado por defecto
    filas = "\n".join(
        f"| Campo {i} | Texto | Input | No | sin nombre tecnico |" for i in range(10)
    )
    dicc = ("### Pantalla 1 — Solicitante — Datos\n\n"
            "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
            + filas + "\n")
    c = tmp_path / "exp"
    c.mkdir()
    (c / "5.-Diccionario de Datos.md").write_text(dicc, encoding="utf-8")
    salida = tmp_path / "t.yaml"

    main(["extraer", str(c), "-o", str(salida)])
    truncado = capsys.readouterr().out
    assert "y " in truncado and "más" in truncado          # se truncó

    main(["extraer", str(c), "-o", str(salida), "--huecos"])
    completo = capsys.readouterr().out
    assert "más" not in completo.split("POR CONFIRMAR")[1]  # ya no trunca
