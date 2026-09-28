# tests/test_as_is.py
from gpmc.extractores.as_is import casa, extraer, requisitos_del_as_is, titulo_de

_ANIDADO = """# Análisis AS-IS — Alta de Avisos

## Estado actual (según fuentes)
- **Canal:** Presencial (Oficialía de Partes), con procesamiento interno.
- **Pasos / ventanillas (3 pasos documentados en el manual):**
  1. El Notario entrega el formato.
  2. Oficialía genera el F7.
     - detalle que no es un paso
  3. El Notario paga en ventanilla.
- **Tiempo estimado:** 13 días hábiles, confirmado con la dependencia (2026-07-20).
- **Requisitos:** identificación oficial vigente, tarjeta de circulación y solicitud
- **Costo:** $534.00 MXN
- **Sistemas involucrados:** e-SIT (orden de pago F7), Drive/Excel ("uno" y "dos"), Word.

## Fricciones identificadas
1. **Doble transcripción del mismo dato.** Se vuelve a escribir en cuatro sistemas.
2. Sin folio de seguimiento.

## Otra sección
1. Esto no es una fricción.
"""

_EN_LINEA = ("- **Pasos / ventanillas:** 3 etapas — Recepción de Solicitud (5 min) → "
             "Revisión Documental (2 min) → Entrega.\n")


def test_lee_los_pasos_de_una_lista_anidada_solo_el_primer_nivel():
    assert extraer(_ANIDADO).pasos == [
        "El Notario entrega el formato",
        "Oficialía genera el F7",
        "El Notario paga en ventanilla",
    ]


def test_lee_los_pasos_en_la_misma_linea_separados_por_flecha():
    assert extraer(_EN_LINEA).pasos == [
        "Recepción de Solicitud (5 min)", "Revisión Documental (2 min)", "Entrega"]


def test_con_dos_listas_de_pasos_se_queda_con_la_primera():
    texto = ("- **Pasos y tiempos — dos mediciones:**\n  - Medición del manual\n"
             "- **Pasos (según la ficha):**\n  1. Uno\n  2. Dos\n")
    assert extraer(texto).pasos == ["Medición del manual"]


def test_tiempo_canal_costo_y_sistemas():
    e = extraer(_ANIDADO)
    assert e.tiempo == "13 días hábiles"
    assert e.canal.startswith("Presencial")
    assert e.costo == "$534.00 MXN"
    assert e.sistemas == ["e-SIT", "Drive/Excel", "Word"]


def test_tiempo_de_respuesta_sin_vineta_tambien_se_lee():
    assert extraer("**Tiempo de respuesta:** 3 días hábiles\n").tiempo == "3 días hábiles"


def test_fricciones_solo_de_su_seccion_y_con_el_titulo_en_negrita():
    assert extraer(_ANIDADO).fricciones == [
        "Doble transcripción del mismo dato", "Sin folio de seguimiento"]


def test_requisitos_van_en_el_estado_actual():
    assert extraer(_ANIDADO).requisitos == [
        "identificación oficial vigente", "tarjeta de circulación", "solicitud"]
    assert requisitos_del_as_is(_ANIDADO) == extraer(_ANIDADO).requisitos


def test_un_as_is_sin_forma_devuelve_vacio_sin_excepcion():
    for texto in ("", None, "# Título\n\nProsa sin viñetas.\n", "| a | b |\n|---|---|\n"):
        e = extraer(texto)
        assert e.pasos == [] and e.requisitos == [] and e.tiempo == ""
        assert e.sistemas == [] and e.fricciones == []


def test_casa_por_inclusion_sin_acentos_ni_mayusculas():
    assert casa("identificación oficial", "Documento: Identificación Oficial Vigente")
    assert not casa("acta de nacimiento", "Comprobante de pago")
    assert not casa("", "algo")


def test_titulo_de_prefiere_la_negrita_inicial():
    assert titulo_de("**Captura a distancia**, sin ventanilla.") == "Captura a distancia"
    assert titulo_de("Sin negrita.") == "Sin negrita"


def test_verificar_fase3_sigue_exportando_el_lector():
    from gpmc.agentes.verificar_fase3 import requisitos_del_as_is as viejo
    assert viejo is requisitos_del_as_is


def test_quitar_una_nota_entre_parentesis_no_deja_dos_espacios():
    texto = "- **Requisitos:** Ingresar el Formato (aprobado por el Consejo) con previo pago.\n"
    assert requisitos_del_as_is(texto) == ["Ingresar el Formato con previo pago"]


# --- Formas halladas en los expedientes reales (2026-09-28) ---------------------

def test_una_vineta_de_total_entre_pasos_numerados_no_es_un_paso():
    texto = ("- **Pasos / tiempos documentados (2 pasos):**\n"
             "  1. Recibir y revisar documentación (3 min)\n"
             "  2. Emitir holograma (3 min)\n"
             "  - **Tiempo interno documentado: 25 minutos** (sin contar el banco).\n")
    assert extraer(texto).pasos == [
        "Recibir y revisar documentación (3 min)", "Emitir holograma (3 min)"]


def test_el_tiempo_se_corta_donde_acaba_la_frase():
    texto = "- **Tiempo interno documentado:** 150 minutos en total. El caso real tomó 4 días.\n"
    assert extraer(texto).tiempo == "150 minutos en total"


_TABLAS = """- **Pasos y tiempos — dos mediciones distintas:**

  *Manual operativo (tiempo de trabajo activo):*
  | # | Paso | Tiempo |
  |---|---|---|
  | 1 | Solicitud de Información (el ciudadano pide información) | 3 min |
  | 5A | *Ruta Prórroga* — Evaluación de Supuestos | 3 min |

  **Total de trabajo activo: 24 min.**

  *Ficha RUTS oficial:*
  | Etapa | Área de atención | Tiempo | Producto |
  |---|---|---|---|
  | Solicitud | Atención a Usuarios | 5 minutos | Formato |
- **Requisitos:** uno, dos
"""


def test_los_pasos_en_tabla_salen_de_la_columna_paso_de_la_primera_tabla():
    assert extraer(_TABLAS).pasos == [
        "Solicitud de Información (el ciudadano pide información)",
        "*Ruta Prórroga* — Evaluación de Supuestos",
    ]


def test_las_etapas_en_tabla_tambien_son_pasos():
    texto = ("- **Etapas y tiempos (ficha RUTS oficial):**\n"
             "  | Etapa | Área de atención | Tiempo | Producto |\n"
             "  |---|---|---|---|\n"
             "  | Solicitud | Atención a Usuarios | 5 minutos | Formato |\n"
             "  | Búsqueda de certificado | Dirección | 3 a 5 días hábiles | Copia |\n")
    assert extraer(texto).pasos == ["Solicitud", "Búsqueda de certificado"]


def test_una_tabla_sin_columna_de_paso_no_se_adivina():
    texto = ("- **Pasos:**\n  | Área | Tiempo |\n  |---|---|\n  | Ventanilla | 5 min |\n")
    assert extraer(texto).pasos == []
