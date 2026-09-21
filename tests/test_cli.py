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


# ── `servir --almacen` ──────────────────────────────────────────────────────

def test_servir_pasa_el_almacen_a_crear_app(tmp_path, monkeypatch):
    """Sin esto cada arranque estrena un tempfile.mkdtemp() y las sesiones se
    pierden al apagar: asi se perdieron los artefactos de una jornada entera de
    dogfooding. `crear_app` ya aceptaba el parametro; el CLI no lo exponia."""
    import gpmc.web.app as web_app

    vistos = {}

    def falso_crear_app(almacen=None):
        vistos["almacen"] = almacen
        return object()

    monkeypatch.setattr(web_app, "crear_app", falso_crear_app)
    monkeypatch.setitem(
        __import__("sys").modules, "uvicorn",
        type("U", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )

    destino = tmp_path / "sesiones"
    assert main(["servir", "--almacen", str(destino)]) == 0
    assert vistos["almacen"] == destino


def test_servir_sin_almacen_no_fija_ninguno(tmp_path, monkeypatch):
    import gpmc.web.app as web_app

    vistos = {}
    monkeypatch.setattr(web_app, "crear_app",
                        lambda almacen=None: vistos.setdefault("almacen", almacen) or object())
    monkeypatch.setitem(
        __import__("sys").modules, "uvicorn",
        type("U", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )

    assert main(["servir"]) == 0
    assert vistos["almacen"] is None


# ── Fase 2: entorno fuera del repo y medir-ia ──
def test_cargar_entorno_lee_clave_valor_sin_pisar_lo_existente(tmp_path, monkeypatch):
    import os
    from gpmc.cli import cargar_entorno
    f = tmp_path / "entorno"
    f.write_text("# comentario\nGPMC_IA_PROVEEDOR=gemini\nGPMC_IA_LLAVE = abc\n", encoding="utf-8")
    monkeypatch.delenv("GPMC_IA_PROVEEDOR", raising=False)
    monkeypatch.setenv("GPMC_IA_LLAVE", "ya-estaba")
    assert cargar_entorno(f) == 1
    assert os.environ["GPMC_IA_PROVEEDOR"] == "gemini" and os.environ["GPMC_IA_LLAVE"] == "ya-estaba"


def test_cargar_entorno_sin_archivo_es_cero(tmp_path):
    from gpmc.cli import cargar_entorno
    assert cargar_entorno(tmp_path / "no-existe") == 0


def test_medir_ia_reporta_tabla_con_proveedor_falso(tmp_path, capsys, monkeypatch):
    import json
    from pathlib import Path
    from gpmc import cli
    from gpmc.agentes.proveedor import ProveedorFalso
    ejemplos = Path(__file__).resolve().parents[1] / "ejemplos" / "expedientes"
    resp = json.dumps({"propuestas": []})
    monkeypatch.setattr(cli, "_proveedor_para_medir", lambda: ProveedorFalso([resp] * 20))
    assert cli.main(["medir-ia", str(ejemplos), "--almacen", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "TOTAL" in out and "DIC-08" in out


def test_medir_ia_con_proveedor_caido_avisa_sin_traceback(tmp_path, capsys, monkeypatch):
    """Un 401 o una caida de red no deben salir como traceback: una linea
    clara por expediente y codigo de salida 1."""
    import sys
    from pathlib import Path
    from gpmc import cli
    from gpmc.agentes.proveedor import ProveedorFalso
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.test_extractor_diccionario import _VIS
    (tmp_path / "exp").mkdir(); (tmp_path / "exp" / "Diccionario de Datos.md").write_text(_VIS, encoding="utf-8")
    monkeypatch.setattr(cli, "_proveedor_para_medir", lambda: ProveedorFalso([]))  # guion vacio = red caida
    rc = cli.main(["medir-ia", str(tmp_path), "--almacen", str(tmp_path / "alm")])
    out = capsys.readouterr()
    assert rc == 1
    assert "error del proveedor" in out.out and "guion agotado" in out.out
    assert "Traceback" not in out.err


def test_medir_ia_con_llave_invalida_avisa_sin_traceback(tmp_path, capsys, monkeypatch):
    """`ErrorDeProveedor` (4xx: llave invalida, modelo inexistente) es una
    excepcion distinta de `ErrorDeRed` desde el 2026-09-21. Si `medir-ia` solo
    captura la vieja, el 401 de siempre vuelve a salir como traceback."""
    import sys
    from pathlib import Path
    from gpmc import cli
    from gpmc.agentes.proveedor import ErrorDeProveedor, ProveedorFalso
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.test_extractor_diccionario import _VIS

    class LlaveInvalida(ProveedorFalso):
        def completar(self, instrucciones, contexto, esquema):
            raise ErrorDeProveedor("HTTP 401 llave invalida")

    (tmp_path / "exp").mkdir(); (tmp_path / "exp" / "Diccionario de Datos.md").write_text(_VIS, encoding="utf-8")
    monkeypatch.setattr(cli, "_proveedor_para_medir", lambda: LlaveInvalida([]))
    rc = cli.main(["medir-ia", str(tmp_path), "--almacen", str(tmp_path / "alm")])
    out = capsys.readouterr()
    assert rc == 1
    assert "error del proveedor" in out.out and "401" in out.out


def _servir_capturando(monkeypatch, argumentos, entorno=None):
    """Corre `gpmc servir` con un uvicorn de mentira y devuelve lo que recibio."""
    import gpmc.web.app as web_app
    from gpmc import cli
    visto = {}
    monkeypatch.setattr(web_app, "crear_app", lambda almacen=None: object())
    monkeypatch.setattr(cli, "cargar_entorno", lambda: None)
    for k in ("GPMC_LOG_NIVEL", "GPMC_LOG_ARCHIVO"):
        monkeypatch.delenv(k, raising=False)
    for k, v in (entorno or {}).items():
        monkeypatch.setenv(k, v)
    monkeypatch.setitem(
        __import__("sys").modules, "uvicorn",
        type("U", (), {"run": staticmethod(lambda *a, **k: visto.update(k))})(),
    )
    assert main(["servir"] + argumentos) == 0
    return visto


def test_servir_registra_las_peticiones_y_les_pone_fecha(monkeypatch):
    # `log_level="warning"` dejaba el log sin una sola peticion y sin fecha en
    # ninguna linea: tras un mes en marcha tenia 17.
    visto = _servir_capturando(monkeypatch, [])
    assert visto.get("access_log") is True
    assert visto["log_level"] == "info"
    cfg = visto["log_config"]
    assert "%(asctime)s" in cfg["formatters"]["con_fecha"]["format"]
    assert set(cfg["loggers"]) >= {"gpmc", "uvicorn.access", "uvicorn.error"}


def test_servir_con_log_escribe_en_un_archivo_que_rota(tmp_path, monkeypatch):
    destino = tmp_path / "logs" / "asistente.log"
    visto = _servir_capturando(monkeypatch, ["--log", str(destino)])
    salida = visto["log_config"]["handlers"]["salida"]
    assert salida["filename"] == str(destino) and salida["backupCount"] > 0


def test_servir_toma_nivel_y_archivo_del_entorno(tmp_path, monkeypatch):
    # El servicio de launchd lee `~/.config/gpmc/entorno`: se puede subir el
    # nivel a DEBUG para cazar algo sin tocar el plist ni reinstalar.
    destino = tmp_path / "desde-entorno.log"
    visto = _servir_capturando(monkeypatch, [], {"GPMC_LOG_NIVEL": "debug",
                                                 "GPMC_LOG_ARCHIVO": str(destino)})
    assert visto["log_level"] == "debug"
    assert visto["log_config"]["handlers"]["salida"]["filename"] == str(destino)
    assert visto["log_config"]["loggers"]["gpmc"]["level"] == "DEBUG"


def test_servir_el_flag_gana_sobre_el_entorno(tmp_path, monkeypatch):
    visto = _servir_capturando(monkeypatch, ["--log", str(tmp_path / "flag.log")],
                               {"GPMC_LOG_ARCHIVO": str(tmp_path / "entorno.log")})
    assert visto["log_config"]["handlers"]["salida"]["filename"].endswith("flag.log")
