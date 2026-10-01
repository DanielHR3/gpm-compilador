# Herramientas de desarrollo

Solo para quien desarrolla; nada de esto entra al compilador. `pip install -e ".[dev]"`.

| Herramienta | Para qué | Cómo |
| --- | --- | --- |
| gitleaks + pre-commit | El repo es público: frena secretos e identificadores del despliegue antes del commit. Reglas propias en `.gitleaks.toml` | Una vez: `.venv/bin/pre-commit install`. Todo el repo: `.venv/bin/pre-commit run --all-files` |
| git-cliff | Borrador de «Lo que se hizo» de la bitácora a partir de los commits del día | `scripts/bitacora.sh 2026-10-01` |
| `scripts/trazabilidad.py` | Matriz historia → criterio → prueba; error si una prueba citada en la bóveda ya no existe | `scripts/trazabilidad.py --boveda "<…/02 - Historias de usuario>" [--salida …]` |
| `scripts/a-boveda.sh` | Copia specs, actas y decisiones a la bóveda (solo repo → bóveda) | `GPMC_BOVEDA="<…/Compilador GPM>" scripts/a-boveda.sh` |
| `docs/decisiones/` | Decisiones de arquitectura en forma MADR, con su acta | Copiar `plantilla.md` |

Las pruebas de `test_api.py` que sirven la SPA necesitan `frontend/dist/`; en un worktree sin
compilar, apunta `GPMC_FRONTEND_DIST` al `dist` de otro checkout.
