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


# ── Linter de expediente bloqueante (--estricto / --desde-expediente) ──

_ASIS_LIMPIO = """---
dependencia: Secretaría de Prueba
---
# Análisis AS-IS — Trámite Limpio

**Tiempo de respuesta:** 5 días hábiles
"""

_TOBE_LIMPIO = """# Propuesta TO-BE — Trámite Limpio

```mermaid
flowchart TD
    classDef solicitante fill:#eee
    Start([Inicio]):::solicitante --> T1[Solicitante: Datos]:::solicitante
    T1 --> Fin([Fin]):::solicitante
```
"""


def _exp_limpio(tmp_path):
    """Expediente completo cuyos huecos son todos 'por_confirmar' (no bloquean):
    Diccionario con @@, AS-IS con dependencia y tiempo, TO-BE lineal con carril."""
    c = tmp_path / "exp_ok"
    c.mkdir()
    (c / "5.-Diccionario de Datos.md").write_text(
        "### Pantalla 1 — Solicitante — Datos\n\n"
        "| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Descripcion |\n"
        "| CURP | Texto | Input | Sí | La CURP `@@curp` |\n",
        encoding="utf-8",
    )
    (c / "1.-Análisis AS-IS.md").write_text(_ASIS_LIMPIO, encoding="utf-8")
    (c / "3.-Propuesta TO-BE.md").write_text(_TOBE_LIMPIO, encoding="utf-8")
    return c


def test_extraer_estricto_no_escribe_y_sale_2_con_huecos(tmp_path, capsys):
    """El expediente mínimo (solo Diccionario) tiene INS-01 (falta TO-BE),
    bloqueante. Con --estricto no se escribe el .yaml y el código de salida es 2."""
    salida = tmp_path / "t.yaml"
    codigo = main(["extraer", str(_exp(tmp_path)), "-o", str(salida), "--estricto"])
    assert codigo == 2
    assert not salida.exists()
    err = capsys.readouterr().err
    assert "no se escribio" in err.lower()


def test_extraer_sin_estricto_escribe_aunque_haya_huecos(tmp_path):
    """Comportamiento actual intacto: sin --estricto, el .yaml se escribe."""
    salida = tmp_path / "t.yaml"
    assert main(["extraer", str(_exp(tmp_path)), "-o", str(salida)]) == 0
    assert salida.exists()


def test_extraer_estricto_deja_pasar_un_expediente_sin_huecos_bloqueantes(tmp_path):
    salida = tmp_path / "t.yaml"
    codigo = main(["extraer", str(_exp_limpio(tmp_path)), "-o", str(salida), "--estricto"])
    assert codigo == 0, salida
    assert salida.exists()


def test_compilar_desde_expediente_bloquea_si_hay_huecos(tmp_path, capsys):
    destino = tmp_path / "s.gpm"
    codigo = main(["compilar", "--desde-expediente", str(_exp(tmp_path)), "-o", str(destino)])
    assert codigo == 2
    assert not destino.exists()


def test_compilar_desde_expediente_compila_uno_limpio(tmp_path):
    destino = tmp_path / "s.gpm"
    codigo = main(["compilar", "--desde-expediente", str(_exp_limpio(tmp_path)), "-o", str(destino)])
    assert codigo == 0
    assert destino.exists()
    assert leer(destino)["Formularios"]
