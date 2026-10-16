# tests/test_verificar_comparativa.py
"""La verificacion de lo que el modelo propone para la comparativa. Sin modelo."""
from gpmc.agentes.verificar_comparativa import (
    indexar, tramo_literal, verificar_evidencia, verificar_mejoras)
from gpmc.comparativa.documentos import Referencia

_ASIS = """# Análisis AS-IS — Reposición

## Estado actual
- **Canal:** presencial.
- **Flujo AS-IS completo:**
  1. **Usuario:** recibe el formato, lo requisita y lo entrega junto con los documentos.
  2. **Dirección de Verificación Vehicular:** revisa la documentación.
  3. La Dirección consulta la "Base Datos de Excel y plataforma de verificación".
  4. Usuario lo lleva a Ventanilla.
  5. Usuario recibe el F7 y paga (en banco).
- **Tiempo de respuesta:** 3 a 5 días hábiles — POR CONFIRMAR.
- El formato pide el **nombre del propietario** y la placa; la Ventanilla vuelve a capturar
  el nombre del propietario en el Formato F7.
"""

_TOBE = """# Propuesta TO-BE — Reposición

**Tiempo de respuesta:** 2 días hábiles

## Problema
El ciudadano debe trasladarse físicamente para entregar su solicitud.

## Propuesta
Todo se resuelve en la plataforma GPM.

```mermaid
flowchart TD
    C3a --> S1[Sistema: Consultar RENAPO por<br/>@@curp_propietario y autocompletar<br/>@@nombre_propietario]:::sistema
```

## Impacto estimado
- 100% digital de principio a fin — no queda ninguna visita presencial residual.
- El ciudadano captura su CURP **una sola vez** y el sistema autocompleta el nombre.
- Se adjunta la tarjeta de circulación en formato digital PDF para la revisión del funcionario.
"""

_TODO = [("actores", "antes"), ("sistemas", "antes"), ("sistemas", "despues"),
         ("tiempo", "despues"), ("visitas", "antes"), ("visitas", "despues"),
         ("capturas", "antes"), ("capturas", "despues"), ("pasos", "antes")]


def _lado(metrica, lado, *elementos, ninguno=False, motivo="m"):
    return {"metrica": metrica, "lado": lado, "ninguno": ninguno, "motivo": motivo,
            "elementos": [{"nombre": n, "cita": c} for n, c in elementos]}


def _una(items, faltan=_TODO):
    propuestas, alertas = verificar_evidencia(items, _ASIS, _TOBE, faltan)
    return propuestas, alertas


# --- el tramo literal -------------------------------------------------------

def test_una_cita_literal_se_devuelve_como_esta_en_el_documento():
    # El modelo quita acentos y negritas; lo que se guarda es el texto del documento.
    t = tramo_literal("usuario: recibe el formato, lo requisita y lo entrega", indexar(_ASIS))
    assert t == "Usuario: recibe el formato, lo requisita y lo entrega"


def test_las_etiquetas_html_no_son_texto():
    t = tramo_literal("Sistema: Consultar RENAPO por @@curp_propietario y autocompletar "
                      "@@nombre_propietario", indexar(_TOBE))
    assert t == "Sistema: Consultar RENAPO por @@curp_propietario y autocompletar @@nombre_propietario"


def test_de_una_cita_mal_copiada_en_la_orilla_queda_el_tramo_que_si_esta():
    t = tramo_literal("En resumen el usuario lo lleva a Ventanilla.", indexar(_ASIS))
    assert t == "Usuario lo lleva a Ventanilla"


def test_una_frase_que_no_esta_no_da_tramo():
    assert tramo_literal("el ciudadano acude tres veces a la oficina central", indexar(_ASIS)) == ""
    # Cuatro palabras sueltas en comun no sostienen una cita de quince.
    larga = ("el usuario lo lleva a otra dependencia distinta para que le sellen el "
             "formato de pago correspondiente")
    assert tramo_literal(larga, indexar(_ASIS)) == ""
    assert tramo_literal("", indexar(_ASIS)) == "" and tramo_literal(None, indexar(_ASIS)) == ""


# --- evidencia por metrica --------------------------------------------------

def test_la_cifra_de_visitas_son_las_frases_que_sobreviven():
    p, alertas = _una([_lado(
        "visitas", "antes",
        ("Entregar la solicitud", "recibe el formato, lo requisita y lo entrega junto con los documentos"),
        ("Ir a ventanilla", "Usuario lo lleva a Ventanilla."),
        ("Ir al banco", "Usuario recibe el F7 y paga (en banco)."),
        ("Recoger el certificado", "acude a recoger su certificado a la oficina"))])
    assert len(p) == 1 and (p[0].metrica, p[0].lado, p[0].ninguno) == ("visitas", "antes", False)
    assert [e.nombre for e in p[0].evidencias] == [
        "Entregar la solicitud", "Ir a ventanilla", "Ir al banco"]
    assert alertas == ["cita_inventada"]


def test_el_antes_solo_se_sostiene_en_el_as_is():
    # La frase existe, pero en el TO-BE: no prueba nada del «antes».
    p, alertas = _una([_lado("visitas", "antes", (
        "Entregar la solicitud",
        "El ciudadano debe trasladarse físicamente para entregar su solicitud"))])
    assert p == [] and alertas == ["cita_inventada"]


def test_una_frase_que_existe_pero_no_habla_de_ir_en_persona_no_es_una_visita():
    p, alertas = _una([_lado("visitas", "antes", (
        "Consulta", "La Dirección consulta la \"Base Datos de Excel y plataforma de verificación\""))])
    assert p == [] and alertas == ["cita_ajena"]


def test_la_misma_frase_dos_veces_cuenta_una():
    p, alertas = _una([_lado(
        "visitas", "antes",
        ("Ir a ventanilla", "Usuario lo lleva a Ventanilla."),
        ("Llevar el pre-recibo", "usuario lo lleva a ventanilla"))])
    assert len(p[0].evidencias) == 1 and alertas == ["duplicado"]


def test_ninguno_exige_una_frase_que_lo_diga():
    p, _ = _una([_lado("visitas", "despues",
                       ("Cero visitas", "no queda ninguna visita presencial residual"),
                       ninguno=True)])
    assert (p[0].ninguno, len(p[0].evidencias)) == (True, 1)
    # Una frase del tema que no dice que ya no hay, no es un cero.
    p, alertas = _una([_lado("visitas", "despues", (
        "Cero visitas", "debe trasladarse físicamente para entregar su solicitud"), ninguno=True)])
    assert p == [] and alertas == ["ninguno_sin_frase"]
    p, alertas = _una([_lado("visitas", "despues", ninguno=True)])
    assert p == [] and alertas == ["ninguno_sin_frase"]


def test_actores_y_sistemas_valen_si_el_nombre_esta_en_el_documento():
    p, alertas = _una([
        _lado("actores", "antes",
              ("Usuario", "Usuario lo lleva a Ventanilla."),
              ("Dirección de Verificación Vehicular", "una frase que el modelo inventó entera"),
              ("Tesorería del Estado", "Usuario recibe el F7 y paga (en banco)."),
              ("usuario", "Usuario recibe el F7 y paga (en banco).")),
        _lado("sistemas", "antes", ("plataforma de verificación",
                                   "Base Datos de Excel y plataforma de verificación"))])
    actores = next(x for x in p if x.metrica == "actores")
    assert [e.nombre for e in actores.evidencias] == [
        "Usuario", "Dirección de Verificación Vehicular"]
    # Sin cita buena, la evidencia es la linea del documento donde aparece el nombre.
    assert "revisa la documentación" in actores.evidencias[1].cita
    assert alertas == ["nombre_inventado", "duplicado"]
    assert next(x for x in p if x.metrica == "sistemas").evidencias[0].nombre == \
        "plataforma de verificación"


def test_el_tiempo_es_el_plazo_tal_como_esta_escrito():
    p, _ = _una([_lado("tiempo", "despues", ("2 dias habiles", "Tiempo de respuesta: 2 días hábiles"))])
    assert (p[0].texto, p[0].evidencias[0].nombre) == ("2 días hábiles", "2 días hábiles")
    # Un plazo que el documento no trae, o sin cifra, no entra.
    p, alertas = _una([_lado("tiempo", "despues", ("1 día hábil", "Tiempo de respuesta: 1 día hábil")),
                       ])
    assert p == [] and alertas == ["nombre_inventado"]
    p, alertas = _una([_lado("tiempo", "despues", ("días hábiles", "Tiempo de respuesta"))])
    assert p == [] and alertas == ["tiempo_sin_cifra"]


def test_del_tiempo_solo_entra_un_plazo():
    p, alertas = _una([_lado("tiempo", "despues",
                             ("2 días hábiles", "Tiempo de respuesta: 2 días hábiles"),
                             ("100", "100% digital de principio a fin"))])
    assert len(p[0].evidencias) == 1 and alertas == ["duplicado"]


def test_una_captura_repetida_tiene_que_hablar_de_capturar():
    p, alertas = _una([_lado(
        "capturas", "antes",
        ("Nombre del propietario", "la Ventanilla vuelve a capturar el nombre del propietario"),
        ("Placa", "Usuario recibe el F7 y paga (en banco)."))])
    assert [e.nombre for e in p[0].evidencias] == ["Nombre del propietario"]
    assert alertas == ["cita_ajena"]
    p, _ = _una([_lado("capturas", "despues",
                       ("Ninguna", "El ciudadano captura su CURP una sola vez"), ninguno=True)])
    assert p[0].ninguno is True


def test_solo_se_aceptan_los_lados_que_se_pidieron():
    p, alertas = _una([_lado("visitas", "antes", ("Ir", "Usuario lo lleva a Ventanilla."))],
                      faltan=[("visitas", "despues")])
    assert p == [] and alertas == ["lado_no_pedido"]
    p, alertas = _una([_lado("costo", "antes", ("x", "y")), "basura", {"metrica": "visitas"}])
    assert p == [] and alertas == ["lado_no_pedido", "respuesta_invalida", "respuesta_invalida"]


def test_un_lado_que_se_queda_sin_evidencia_no_es_una_propuesta():
    p, _ = _una([_lado("visitas", "antes", ("Ir", "frase que no existe en ningún lado del texto"))])
    assert p == []


def test_el_motivo_viaja_recortado():
    p, _ = _una([_lado("visitas", "antes", ("Ir", "Usuario lo lleva a Ventanilla."),
                       motivo="x" * 900)])
    assert len(p[0].motivo) == 300


# --- puntos de mejora -------------------------------------------------------

_REFS = [Referencia("doc_tarjeta", "Tarjeta de Circulación", "Solicitud", "Ciudadano",
                    "archivo_ciudadano"),
         Referencia("curp", "CURP", "Solicitud", "Ciudadano", "consulta")]
_SERVICIOS = {"consultacurpn", "zip_codes"}


def _mejora(**k):
    base = dict(titulo="Quitar la tarjeta de circulación", tipo="documento",
                propuesta="Consultarla en el padrón.", beneficio="Ahorra un escaneo.",
                fuente="to_be", cita="Se adjunta la tarjeta de circulación en formato digital PDF",
                campo="doc_tarjeta", servicio=None, requiere_convenio=False)
    base.update(k)
    return base


def _mejoras(items):
    return verificar_mejoras(items, _ASIS, _TOBE, _REFS, _SERVICIOS)


def test_un_punto_de_mejora_con_campo_y_frase_entra_completo():
    m, alertas = _mejoras([_mejora()])
    assert alertas == [] and len(m) == 1
    assert (m[0].titulo, m[0].tipo, m[0].campo, m[0].etiqueta_campo, m[0].fuente) == (
        "Quitar la tarjeta de circulación", "documento", "doc_tarjeta",
        "Tarjeta de Circulación", "to_be")
    assert m[0].cita == "Se adjunta la tarjeta de circulación en formato digital PDF"
    assert m[0].descartada is False and len(m[0].id) == 12


def test_basta_el_campo_cuando_la_frase_esta_mal_copiada():
    m, alertas = _mejoras([_mejora(cita="Tarjeta de Circulación, Certificado anterior, INE")])
    assert len(m) == 1 and (m[0].campo, m[0].cita) == ("doc_tarjeta", "")
    assert alertas == ["cita_inventada"]


def test_sin_campo_ni_frase_el_punto_se_descarta():
    m, alertas = _mejoras([_mejora(campo="doc_que_no_existe", cita="frase que nadie escribió nunca")])
    assert m == [] and alertas == ["campo_inventado", "cita_inventada", "mejora_sin_evidencia"]


def test_la_frase_se_busca_en_el_bloque_que_dice_la_fuente():
    m, _ = _mejoras([_mejora(campo=None, fuente="as_is",
                             cita="la Ventanilla vuelve a capturar el nombre del propietario")])
    assert (m[0].fuente, m[0].campo) == ("as_is", "")
    m, alertas = _mejoras([_mejora(campo=None, fuente="as_is",
                                   cita="Se adjunta la tarjeta de circulación en formato digital PDF")])
    assert m == [] and "mejora_sin_evidencia" in alertas


def test_un_servicio_del_catalogo_publico_se_puede_hacer_hoy_y_otro_pide_convenio():
    m, alertas = _mejoras([_mejora(servicio="consultacurpn"),
                           _mejora(titulo="Otra", campo=None, servicio="padron_vehicular",
                                   cita="no queda ninguna visita presencial residual"),
                           _mejora(titulo="Tercera", campo=None, requiere_convenio=True,
                                   cita="El ciudadano captura su CURP una sola vez")])
    assert [(x.servicio, x.requiere) for x in m] == [
        ("consultacurpn", "servicio_publico"), ("", "convenio"), ("", "convenio")]
    assert alertas == ["servicio_fuera_del_catalogo"]


def test_puntos_repetidos_vacios_o_de_mas_no_entran():
    m, alertas = _mejoras([_mejora(), _mejora(titulo="Eliminar tarjeta"),
                           _mejora(titulo="  "), "basura"])
    assert len(m) == 1 and alertas == ["duplicado", "respuesta_invalida", "respuesta_invalida"]
    muchos = [_mejora(titulo=f"Punto {i}", campo=None,
                      cita=c) for i, c in enumerate([
                          "no queda ninguna visita presencial residual",
                          "El ciudadano captura su CURP una sola vez",
                          "Todo se resuelve en la plataforma GPM",
                          "El ciudadano debe trasladarse físicamente para entregar su solicitud",
                          "100% digital de principio a fin",
                          "el sistema autocompleta el nombre del propietario ya",
                          "Se adjunta la tarjeta de circulación en formato digital"])]
    m, _ = _mejoras(muchos)
    assert len(m) <= 6


def test_un_tipo_desconocido_cae_en_friccion_y_los_textos_se_recortan():
    m, _ = _mejoras([_mejora(tipo="otra cosa", propuesta="p" * 900, beneficio="b" * 900)])
    assert m[0].tipo == "friccion" and len(m[0].propuesta) == 400 and len(m[0].beneficio) == 300


# --- lo que enseño la prueba en vivo del 2026-10-01 -------------------------

def test_un_plazo_que_el_documento_da_por_pendiente_no_es_un_plazo():
    tobe = ('**Tiempo de respuesta:** [Pendiente de confirmar] — sin cambio frente al AS-IS '
            '("1 día hábil" declarado); esta Propuesta no fija un tiempo de respuesta objetivo.\n')
    p, alertas = verificar_evidencia(
        [_lado("tiempo", "despues", ("1 día hábil", '"1 día hábil" declarado'))],
        _ASIS, tobe, [("tiempo", "despues")])
    assert p == [] and alertas == ["tiempo_pendiente"]


def test_una_captura_sin_repeticion_no_es_una_captura_repetida():
    asis = _ASIS + '- Tarjeta de circulación — "con la placa que se registró la verificación".\n' \
                   "- El usuario llena el formato de solicitud con sus datos.\n"
    p, alertas = verificar_evidencia(
        [_lado("capturas", "antes",
               ("Placa", "con la placa que se registró la verificación"),
               ("Datos", "El usuario llena el formato de solicitud con sus datos"))],
        asis, _TOBE, [("capturas", "antes")])
    assert p == [] and alertas == ["cita_ajena", "cita_ajena"]


def test_un_nombre_corto_y_su_nombre_largo_son_el_mismo():
    tobe = _TOBE + ("- El oficio se publica en el Expediente Digital Ciudadano.\n"
                    "- El folio se vincula desde su Expediente Digital.\n")
    p, alertas = verificar_evidencia(
        [_lado("sistemas", "despues",
               ("Expediente Digital", "El folio se vincula desde su Expediente Digital"),
               ("Expediente Digital Ciudadano", "El oficio se publica en el Expediente Digital Ciudadano"),
               ("RENAPO", "Sistema: Consultar RENAPO por @@curp_propietario"))],
        _ASIS, tobe, [("sistemas", "despues")])
    assert [e.nombre for e in p[0].evidencias] == ["Expediente Digital", "RENAPO"]
    assert alertas == ["duplicado"]


def test_el_tramo_no_deja_un_parentesis_abierto():
    asis = "- La Dirección proporciona el Formato de Solicitud de Reposición (1).\n"
    t = tramo_literal("Dirección proporciona el Formato de Solicitud de Reposición (1)", indexar(asis))
    assert t == "Dirección proporciona el Formato de Solicitud de Reposición (1)"


def test_la_plataforma_donde_corre_el_tramite_no_es_un_sistema_externo():
    tobe = _TOBE + "- La búsqueda se hace sobre el sistema interno de verificación.\n"
    p, alertas = verificar_evidencia(
        [_lado("sistemas", "despues",
               ("plataforma GPM", "Todo se resuelve en la plataforma GPM."),
               ("sistema interno de verificación", "La búsqueda se hace sobre el sistema interno"))],
        _ASIS, tobe, [("sistemas", "despues")])
    assert [e.nombre for e in p[0].evidencias] == ["sistema interno de verificación"]
    assert alertas == ["plataforma_propia"]


def test_ningun_sistema_exige_una_frase_que_hable_de_sistemas():
    # Prueba en vivo (Prórroga): el modelo dio «ninguno» con una frase sobre papel y firmas.
    asis = _ASIS + ("- Todo el flujo depende de documentos físicos y firmas autógrafas, sin copia digital.\n"
                    "- El área no usa ningún sistema: todo se lleva en libretas.\n")
    p, alertas = verificar_evidencia(
        [_lado("sistemas", "antes", ("ninguno", "Todo el flujo depende de documentos físicos y "
                                                "firmas autógrafas, sin copia digital"), ninguno=True)],
        asis, _TOBE, [("sistemas", "antes")])
    assert p == [] and alertas == ["ninguno_sin_frase"]
    p, _ = verificar_evidencia(
        [_lado("sistemas", "antes", ("ninguno", "El área no usa ningún sistema"), ninguno=True)],
        asis, _TOBE, [("sistemas", "antes")])
    assert p[0].ninguno is True


def test_que_el_tramite_sea_digital_no_dice_que_no_haya_capturas_repetidas():
    tobe = _TOBE + "- El ciudadano llena el formulario digital en línea.\n"
    p, alertas = verificar_evidencia(
        [_lado("capturas", "despues", ("ninguna", "El ciudadano llena el formulario digital en línea"),
               ninguno=True)],
        _ASIS, tobe, [("capturas", "despues")])
    assert p == [] and alertas == ["ninguno_sin_frase"]


def test_un_enlace_de_la_boveda_se_lee_por_su_nombre():
    tobe = ("- A diferencia de [[1. REINGENIERIA/_recuperados/Holograma Exento]], aquí no queda "
            "ninguna visita presencial; ver [[wiki/Análisis AS-IS|el análisis]] del trámite.\n")
    t = tramo_literal("A diferencia de Holograma Exento, aquí no queda ninguna visita presencial; "
                      "ver el análisis del trámite", indexar(tobe))
    assert t == ("A diferencia de Holograma Exento, aquí no queda ninguna visita presencial; "
                 "ver el análisis del trámite")


# --- mejoras-v2: los limites de diseño de Simplificacion (2026-10-01) ------

def test_cada_mejora_dice_cual_de_las_cuatro_preguntas_contesta():
    m, _ = _mejoras([_mejora(accion="eliminar"), _mejora(titulo="Otra", campo=None,
                     cita="El ciudadano captura su CURP una sola vez", accion="inventada")])
    assert [x.accion for x in m] == ["eliminar", ""]


def test_una_mejora_que_pide_firma_electronica_avanzada_al_ciudadano_no_entra():
    m, alertas = _mejoras([_mejora(propuesta="Que el ciudadano firme con su e.firma la solicitud.")])
    assert m == [] and alertas == ["fuera_de_limites"]
    m, alertas = _mejoras([_mejora(propuesta="Firmar con firma electrónica avanzada.")])
    assert m == [] and alertas == ["fuera_de_limites"]


def test_una_mejora_que_quita_una_forma_de_pago_no_entra():
    m, alertas = _mejoras([_mejora(propuesta="Eliminar el pago en banco y dejar solo el pago en línea.")])
    assert m == [] and alertas == ["fuera_de_limites"]


def test_conectar_un_sistema_interno_es_a_futuro_aunque_el_modelo_no_lo_marque():
    m, _ = _mejoras([_mejora(propuesta="Consultar la tarjeta en el padrón vehicular de la Secretaría.",
                             requiere_convenio=False)])
    assert m[0].requiere == "convenio"


def test_las_frases_reales_que_dependen_de_un_sistema_interno_son_a_futuro():
    # Prueba en vivo de mejoras-v2 sobre Reposición (2026-10-01): salían como «se puede hoy».
    for propuesta in (
            "Quitar el requisito de la fotografía del holograma extraviado ya que el sistema "
            "cuenta con el registro digital.",
            "Permitir que el sistema busque el certificado anterior automáticamente mediante "
            "la placa sin requerir revisión manual del funcionario."):
        m, _ = _mejoras([_mejora(propuesta=propuesta)])
        assert m[0].requiere == "convenio", propuesta
    # Lo que no toca otro sistema sigue siendo de hoy.
    m, _ = _mejoras([_mejora(propuesta="Unir las dos revisiones del funcionario en una sola pantalla.")])
    assert m[0].requiere == ""


# --- una frase que nombra varios elementos (2026-10-16) ---------------------

_ASIS_PROSA = """# Análisis AS-IS — Constancia de Residencia

El ciudadano acude a la ventanilla con una identificación y un comprobante de domicilio.
Un funcionario revisa los documentos a ojo, transcribe los datos a un formato de Word,
lo imprime y lo pasa a firma. Si algo falta, el ciudadano regresa otro día.
"""


def _prosa(items):
    return verificar_evidencia(items, _ASIS_PROSA, "", [("requisitos", "antes"), ("pasos", "antes"),
                                                       ("visitas", "antes")])


def test_una_frase_que_nombra_dos_requisitos_cuenta_dos():
    # Constancia de Residencia (2026-10-16): «con una identificacion y un
    # comprobante de domicilio» daba 1 requisito y la comparativa salia
    # «No reduce, +100 %». La frase repetida vale si nombra al elemento.
    frase = "El ciudadano acude a la ventanilla con una identificación y un comprobante de domicilio."
    p, alertas = _prosa([_lado("requisitos", "antes",
                               ("identificación", frase), ("comprobante de domicilio", frase))])
    assert [e.nombre for e in p[0].evidencias] == ["identificación", "comprobante de domicilio"]
    assert alertas == []


def test_una_frase_con_cuatro_pasos_cuenta_los_que_nombra():
    frase = ("Un funcionario revisa los documentos a ojo, transcribe los datos a un formato "
             "de Word, lo imprime y lo pasa a firma.")
    p, alertas = _prosa([_lado("pasos", "antes",
                               ("revisión de documentos a ojo", frase),
                               ("transcripción de datos a Word", frase),
                               ("firma del documento", frase),
                               ("cobro en caja", frase))])
    assert [e.nombre for e in p[0].evidencias] == [
        "revisión de documentos a ojo", "transcripción de datos a Word", "firma del documento"]
    # El cuarto no comparte ninguna palabra con la frase: es la frase repetida sin mas.
    assert alertas == ["duplicado"]


def test_en_visitas_la_misma_frase_sigue_siendo_una_sola_visita():
    frase = "El ciudadano acude a la ventanilla con una identificación y un comprobante de domicilio."
    p, alertas = _prosa([_lado("visitas", "antes",
                               ("ir a la ventanilla", frase), ("entregar la identificación", frase))])
    assert len(p[0].evidencias) == 1 and alertas == ["duplicado"]
