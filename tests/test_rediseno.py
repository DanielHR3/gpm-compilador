# tests/test_rediseno.py
from gpmc.extractores.rediseno import extraer

_TOBE = """# Propuesta TO-BE — Alta de Avisos

## Propuesta

### Principio aplicado: eliminar, no solo digitalizar
Antes de automatizar cada paso se evaluó si puede eliminarse.

- **El Excel para oficios se elimina por completo**: el oficio sale de la plantilla.

- **La orden de trabajo llenada a mano se elimina**: la sustituye la solicitud.

**Diagrama 1 de 2:**

```mermaid
flowchart TD
    A --> B
```

**Cambios concretos frente al AS-IS:**
1. **Captura 100% a distancia**, sin depender de Oficialía.
   - detalle que no cuenta
2. Monto calculado por el Sistema.
3. **Dirección General eliminada del flujo por completo** (confirmado).

## Impacto estimado
> Estimación cualitativa del agente, no un dato medido.

- **Elimina cualquier traslado físico del Notario.**
- Abre la puerta a procesar avisos de forma individual.

## Métricas del rediseño

| Métrica | Antes | Después |
| --- | --- | --- |
| Tiempo de respuesta | 13 días hábiles | 3 días hábiles |
| Visitas presenciales | 2 | 0 |

## Riesgos
- Esto no es impacto.
"""


def test_cambios_concretos_solo_el_primer_nivel():
    r = extraer(_TOBE)
    assert [p.titulo for p in r.cambios] == [
        "Captura 100% a distancia",
        "Monto calculado por el Sistema",
        "Dirección General eliminada del flujo por completo",
    ]
    assert "sin depender de Oficialía" in r.cambios[0].texto


def test_eliminaciones_juntan_el_principio_y_los_cambios_que_eliminan():
    r = extraer(_TOBE)
    assert [p.titulo for p in r.eliminaciones] == [
        "El Excel para oficios se elimina por completo",
        "La orden de trabajo llenada a mano se elimina",
        "Dirección General eliminada del flujo por completo",
    ]


def test_impacto_no_se_traga_la_seccion_siguiente():
    assert [p.titulo for p in extraer(_TOBE).impacto] == [
        "Elimina cualquier traslado físico del Notario",
        "Abre la puerta a procesar avisos de forma individual",
    ]


def test_metricas_declaradas_sin_encabezado_ni_separador():
    assert extraer(_TOBE).declaradas == [
        ("Tiempo de respuesta", "13 días hábiles", "3 días hábiles"),
        ("Visitas presenciales", "2", "0"),
    ]


def test_un_to_be_sin_nada_de_esto_devuelve_vacio():
    for texto in ("", None, "# TO-BE\n\n```mermaid\nflowchart TD\n A --> B\n```\n"):
        r = extraer(texto)
        assert r.cambios == [] and r.eliminaciones == []
        assert r.impacto == [] and r.declaradas == []


def test_una_fila_de_metricas_con_dos_celdas_se_ignora():
    texto = "## Métricas del rediseño\n\n| Métrica | Antes |\n| --- | --- |\n| Pasos | 9 |\n"
    assert extraer(texto).declaradas == []
