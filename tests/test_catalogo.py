"""Catálogo de campos aprobados (spec 2026-11-11 «Fase 3 compacta»)."""
from gpmc.agentes import catalogo as cat
from gpmc.extractores.diccionario import extraer as extraer_dicc

_D1 = """# Diccionario de Datos — Trámite A

### Pantalla 1 — CIUDADANO — Solicitud

| Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio | Condición de Visibilidad | Límite/Especificaciones | Catálogo de Valores | Ejemplo Real del Campo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CURP | Texto | Campo de texto | Sí | | 18 caracteres | N/A | PEPJ800101HHGRRN09 `@@curp` |
| Modalidad de pago | Lista desplegable | Lista desplegable | Sí | | Valores definidos | En línea · Ventanilla | En línea `@@modalidad_pago` |
| Solo de A | Texto | Campo de texto | No | | 50 caracteres | N/A | x `@@solo_de_a` |
"""

_D2 = """# Diccionario de Datos — Trámite B

### Pantalla 1 — CIUDADANO — Datos

| Nombre del Campo | Tipo de Dato | Límite/Especificaciones | Catálogo de Valores | Descripción |
| --- | --- | --- | --- | --- |
| CURP | Texto | 18 caracteres | N/A | CURP de la persona. `@@curp` |
| Modalidad de pago | Lista desplegable | Valores definidos | En línea · Ventanilla | Cómo paga. `@@modalidad_pago` |
"""


def _wiki(tmp_path):
    for n, t in (("A", _D1), ("B", _D2)):
        d = tmp_path / "ANALISTA" / "Dep" / f"Trámite {n}"
        d.mkdir(parents=True)
        (d / "Diccionario de Datos.md").write_text(t, encoding="utf-8")
    return tmp_path


def test_entra_lo_que_se_repite_en_dos_tramites(tmp_path):
    c = cat.construir(_wiki(tmp_path))
    assert set(c["campos"]) == {"curp", "modalidad_pago"}
    assert c["campos"]["curp"]["tramites"] == 2


def test_nunca_copia_el_ejemplo_real(tmp_path):
    c = cat.construir(_wiki(tmp_path))
    texto = repr(c)
    assert "PEPJ800101HHGRRN09" not in texto
    assert "Ejemplo" not in "".join(c["campos"]["curp"]["celdas"])


def test_la_fila_del_catalogo_se_lee_igual_que_la_aprobada(tmp_path):
    c = cat.construir(_wiki(tmp_path))
    md = cat.diccionario_markdown("Prueba", [("CIUDADANO", "Solicitud",
                                              [cat.fila(c, "curp"), cat.fila(c, "modalidad_pago")])])
    r = extraer_dicc(md)
    campos = {x.nombre: x for x in r.pantallas[0].campos}
    assert campos["curp"].tipo == "text" and campos["curp"].obligatorio and campos["curp"].longitud_exacta == 18
    assert len(campos["modalidad_pago"].catalogo) == 2
    assert not [h for h in r.huecos if h.nivel == "bloqueante"]


def test_la_lista_para_el_modelo_es_corta():
    c = {"campos": {"curp": {"etiqueta": "CURP", "tipo": "Texto", "tramites": 9},
                    "modalidad_pago": {"etiqueta": "Modalidad de pago", "tipo": "Lista desplegable", "tramites": 5}}}
    lineas = cat.para_el_modelo(c).splitlines()
    assert lineas[0].startswith("@@curp") and len(lineas) == 2


# Recuperación (idea de ARGUS, Jiang et al. 2025): al modelo solo viaja lo que
# tiene que ver con el trámite, no el catálogo entero.

def test_solo_viajan_los_campos_que_tocan_el_as_is_y_los_universales():
    c = {"version": 1, "campos": {
        "numero_folio": {"etiqueta": "Número de Folio", "tipo": "Texto", "tramites": 14},
        "numero_placa": {"etiqueta": "Número de placa", "tipo": "Texto", "tramites": 4},
        "fecha_cita": {"etiqueta": "Fecha de la cita", "tipo": "Fecha", "tramites": 5},
        "nombre_usuaria": {"etiqueta": "Nombre de la usuaria", "tipo": "Texto", "tramites": 5}}}
    r = cat.relevantes(c, "El ciudadano presenta la tarjeta de circulación y la placa del vehículo.")
    assert set(r["campos"]) == {"numero_folio", "numero_placa"}     # universal + el que toca el AS-IS
    assert r["version"] == 1


def test_la_recuperacion_respeta_el_tope():
    c = {"version": 1, "campos": {f"c{i}": {"etiqueta": "Folio", "tipo": "Texto", "tramites": 20 - i}
                                  for i in range(10)}}
    assert list(cat.relevantes(c, "folio", maximo=3)["campos"]) == ["c0", "c1", "c2"]
