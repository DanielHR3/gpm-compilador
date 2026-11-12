"""Respuesta a la fabrica: segunda ronda de observaciones de «Alta de Avisos de Testamento».

Genera el PDF que se envio el 2026-11-12 junto con el .gpm de produccion de ese dia. Es un
documento de una sola vez: el texto describe ESE archivo (8 tareas, 41 campos) y no se
recalcula. Se guarda para poder rehacerlo o corregirlo cuando la fabrica conteste las ocho
preguntas, que tambien estan en `planeacion/pendientes.md` (P-27).

Uso (necesita el extra `[guia]`, que trae reportlab):

    .venv/bin/python planeacion/fabrica/2026-11-12-atencion-a-observaciones.py salida.pdf
"""
import sys
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

GUINDA = colors.HexColor("#691C32")
base = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
h1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=GUINDA, spaceAfter=4)
h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=GUINDA, spaceBefore=12, spaceAfter=6, keepWithNext=1)
h3 = ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3, keepWithNext=1)
sub = ParagraphStyle("sub", parent=base, fontName="Helvetica-Bold", spaceAfter=2, keepWithNext=1)
chico = ParagraphStyle("c", parent=base, fontSize=9, leading=12, spaceAfter=0)
chicob = ParagraphStyle("cb", parent=chico, fontName="Helvetica-Bold", textColor=colors.white)
vin = ParagraphStyle("v", parent=base, leftIndent=14, bulletIndent=4, spaceAfter=3)
preg_s = ParagraphStyle("q", parent=base, spaceAfter=7)
nota = ParagraphStyle("n", parent=base, spaceBefore=8)
C = "<font face='Courier'>%s</font>"


def P(t, s=base):
    return Paragraph(t, s)


def L(items):
    return [Paragraph(t, vin, bulletText="•") for t in items]


h = [
    P("Atención a las observaciones generales del trámite – GPM", h1),
    P("<b>Trámite:</b> Alta de Avisos de Testamento &nbsp;·&nbsp; <b>Fecha:</b> 12 de noviembre de 2026"),
    P("<b>Archivo que se entrega:</b> Alta-de-Avisos-de-Testamento (produccion, 2026-11-12).gpm"),
    P("Este documento responde, una por una, a las siete observaciones recibidas sobre el archivo enviado el "
      "11 de noviembre. Dice qué se corrigió, qué sigue pendiente y qué necesitamos saber para terminar. "
      "El archivo nuevo pasó nuestra revisión automática sin hallazgos, pero <b>todavía no lo hemos importado "
      "a la plataforma</b>: si algo falla al importarlo, agradecemos el mensaje de error tal cual."),
    P("Resumen", h2),
]

filas = [
    ("#", "Observación", "Estado", "Qué cambió en el archivo"),
    ("1", "Reglas de validación en los campos", "Atendida", "Formato según el tipo de campo, además de obligatoriedad y longitud."),
    ("2", "Exceso de tareas", "Atendida en parte", "9 tareas pasan a 8. Las rutas de pago siguen como tareas separadas."),
    ("3", "Condicionamiento entre vistas", "Pendiente", "Necesitamos confirmar la forma de la condición de un paso (pregunta 1)."),
    ("4", "Generación de documentos", "Pendiente", "Los dos documentos existen, pero su contenido aún sale vacío."),
    ("5", "Variables de tipo Acción con PHP", "Atendida en parte", "El folio ya es una Acción. El monto y otros cuatro datos siguen sin calcularse."),
    ("6", "Modos de las vistas en validaciones", "Atendida", "Quien revisa ve primero, en modo visualización, la vista que revisa."),
    ("7", "Reglas entre tareas con selectores", "Por precisar", "Sin cambio. Necesitamos saber qué regla falló (pregunta 2)."),
]
t = Table([[P(c, chicob if i == 0 else chico) for c in f] for i, f in enumerate(filas)],
          colWidths=[0.8 * cm, 5.0 * cm, 3.0 * cm, 8.2 * cm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), GUINDA), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F1F2")]),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
h += [t, P("El archivo en cifras: 8 tareas con 14 pasos (6 en modo visualización), 9 vistas, 41 campos, "
           "9 conexiones (4 con condición), 3 acciones, 2 documentos y 3 eventos.", nota),
      P("Detalle por observación", h2)]


def obs(titulo, hecho, queda=None):
    b = [P(titulo, h3)]
    if hecho:
        b += [P("Qué se hizo", sub)] + L(hecho)
    if queda:
        b += [P("Qué queda", sub)] + L(queda)
    return b


h += obs("1. Reglas de validación en los campos", [
    "31 de los 41 campos llevan regla. De los 10 restantes, 9 son de solo lectura y 1 es una opción no obligatoria "
    "(«Disposiciones de Contenido Irrevocable»).",
    "Se agregaron reglas de formato: CURP con " + C % "required|alpha_numeric|exact_length[18]" + "; "
    "Número de Notaría con " + C % "required|numeric|max_length[3]" + "; Número de Escritura con "
    + C % "required|numeric|max_length[20]" + ".",
    "«Referencia de Pago» salía obligatoria y de solo lectura a la vez, lo que impedía avanzar. Ahora es de captura.",
    "Dependencias: 5 campos se muestran solo cuando se cumple su condición (por ejemplo, «Texto de las Observaciones» "
    "solo si «¿Tiene Observaciones?» es Sí).",
], [
    "Las tres fechas piden «fecha válida, no futura» y hoy solo llevan obligatoriedad (pregunta 6).",
])
h += obs("2. Exceso de tareas que fragmentan el flujo", [
    "Dos tareas seguidas del mismo responsable, sin decisión entre ellas, ahora son una sola con dos pasos: "
    "«Importación a RENAT / Verificar Notario y Firmar» (Área de Avisos de Testamento).",
    "Las demás tareas se conservan porque entre ellas cambia el responsable (Notario y Área se alternan) o hay una decisión.",
], [
    "«Selección de Modalidad de Pago» y «Pago en Línea» son del Notario y podrían ser una sola tarea, pero entre ellas "
    "hay una decisión. Unirlas depende de la observación 3.",
])
h += obs("3. Falta de condicionamiento entre vistas", None, [
    "No lo aplicamos todavía. Para mostrar u ocultar una vista dentro de la misma tarea hay que escribir una condición "
    "en el paso, y en los trámites publicados que tenemos de referencia ningún paso trae una. No quisimos entregar una "
    "forma que no hemos visto funcionar.",
    "Con la respuesta a la pregunta 1 uniríamos las rutas de pago en una sola tarea del Notario, con la vista de pago "
    "en línea condicionada a la modalidad elegida.",
])
h += obs("4. Ausencia de generación de documentos", [
    "Los dos documentos («Archivo CSV» y «Oficio de contestación») están dados de alta, cada uno con su Acción y su evento.",
], [
    "Su contenido sale vacío: no tenemos todavía las plantillas con los datos del trámite ya colocados. Las estamos "
    "pidiendo al área de Simplificación; no vamos a decidir nosotros dónde va cada dato en un oficio.",
    "Los dos se generan hoy al terminar la captura. El oficio debería generarse en «Verificar Notario y Firmar»; "
    "lo movemos en cuanto tengamos la plantilla (pregunta 4).",
])
h += obs("5. Falta de aprovechamiento de variables de tipo Acción con PHP", [
    "El «Número de Folio» ya se genera con una Acción de tipo variable: consecutivo con bloqueo sobre "
    + C % "dato_seguimiento" + ", con la forma GPM-AAAA-00001, ejecutada antes de la tarea de captura. "
    "El prefijo «GPM» es provisional mientras la dependencia confirma el suyo.",
], [
    "Cinco datos que debe llenar el sistema siguen sin Acción: «Monto a Pagar», «Fuera del Plazo Legal Sugerido», "
    "«Pago en Línea Confirmado», «Archivo CSV para RENAT» y «Nombre del Funcionario que Firma».",
    "El monto (tarifa Ordinario o Simplificado, más 30 UMA de multa fuera de plazo) lo podemos escribir, pero "
    "necesitamos saber qué debe devolver la Acción para el cobro (pregunta 3).",
])
h += obs("6. Uso inadecuado de los modos de las vistas durante las validaciones", [
    "Cinco tareas abren ahora con la vista que se revisa en modo visualización y después muestran la vista propia. "
    "Ejemplo: «Revisar la Solicitud» muestra primero la captura completa del Notario, sin poder modificarla, "
    "y después el dictamen.",
    "Se quitaron los campos de texto que ocupaban ese lugar («Vista de solo lectura…»).",
    "«Pago en Línea», donde nadie captura, va completa en modo visualización.",
], [
    "«Verificar Notario y Firmar» conserva un campo de texto para ver el oficio generado; se sustituye cuando el "
    "documento tenga contenido (observación 4).",
])
h += obs("7. Uso incorrecto de reglas de validación entre tareas mediante selectores", [
    "No cambiamos nada, porque no pudimos identificar la regla a la que se refiere la observación.",
    "Las cuatro condiciones del archivo comparan el <b>valor</b> de la opción, no su etiqueta: "
    + C % "@@tiene_observaciones=='si'" + ", " + C % "@@tiene_observaciones=='no'" + ", "
    + C % "@@modalidad_pago=='en_linea'" + " y " + C % "@@modalidad_pago=='banco_o_transferencia'"
    + ". Esta forma avanzó correctamente en una prueba nuestra en el portal con un campo de lista.",
], [
    "Cuatro decisiones del funcionario no tienen ruta para la respuesta «No»: «¿Pago Validado?», «¿Importación validada "
    "en RENAT?», «Notario Verificado» y «Autoriza y Firma». El diseño del trámite no dice qué ocurre en esos casos; "
    "lo estamos consultando con Simplificación.",
])

h += [P("Preguntas para la fábrica", h2)]
preg = [
    ("Condición de un paso (observación 3).",
     "¿Cómo se escribe la condición que muestra u oculta una vista dentro de una tarea? "
     "¿Lleva la misma forma que una regla entre tareas (" + C % "@@campo=='valor'" + ")? ¿Puede depender de un "
     "campo capturado en un paso anterior de la misma tarea? Si tienen un trámite de ejemplo que lo use, nos basta con ese archivo."),
    ("Regla con selectores (observación 7).",
     "¿En qué conexión o tarea vieron el problema, y qué forma debe llevar la regla? ¿En qué sección del manual está?"),
    ("Acción de cobro (observación 5).",
     "¿Qué debe devolver la Acción que calcula el monto: solo la cantidad, o el arreglo de "
     "conceptos para la pasarela (concepto, partida, tipo de servicio)? Si es el arreglo, ¿qué partida y qué tipo de servicio "
     "corresponden a este trámite? ¿De dónde se toma el valor vigente de la UMA?"),
    ("Documentos (observación 4).",
     "¿Es correcto que el contenido del documento lo arme una Acción de tipo variable y el "
     "documento solo cite esa variable? ¿El evento debe ir antes o después de la tarea? ¿Cómo debe verlo quien firma: con un "
     "campo de tipo documento dentro de la vista?"),
    ("Dato de sesión (observación 5).",
     "¿Cómo se obtiene en una Acción el nombre del funcionario que tiene la tarea, para "
     "«Nombre del Funcionario que Firma»? ¿Y la confirmación de la pasarela para «Pago en Línea Confirmado»?"),
    ("Fechas.", "¿Qué regla de validación admite la plataforma para «fecha no futura»?"),
    ("Grupos de usuarios.",
     "Las tareas van restringidas a los grupos «Notario» y «Area De Avisos De Testamento», que son los "
     "nombres de los responsables. ¿Con qué nombre exacto existen esos grupos en la plataforma?"),
    ("Tareas (observación 2).",
     "¿Es correcto haber unido «Importación a RENAT» y «Verificar Notario y Firmar»? ¿Esperan además "
     "que las tres tareas de la ruta de banco o transferencia se reduzcan, aunque entre ellas cambie el responsable?"),
]
for i, (t_, c_) in enumerate(preg, 1):
    h.append(P(f"<b>{i}. {t_}</b> {c_}", preg_s))

h += [P("Pendientes de nuestro lado", h2)]
h += L([
    "Importar el archivo a la plataforma y recorrerlo en el portal antes de darlo por bueno.",
    "Confirmar con la dependencia el prefijo del folio.",
    "Conseguir de Simplificación las plantillas de los dos documentos y definir en qué tarea se genera cada uno.",
    "Definir con Simplificación qué pasa cuando el funcionario responde «No» en las cuatro decisiones sin ruta.",
    "«Campos con Error» está descrito como una lista sin opciones definidas y hoy sale como campo de texto.",
])


def pie(c, d):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(2 * cm, 1.2 * cm, "Alta de Avisos de Testamento · Atención a observaciones · 2026-11-12")
    c.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm, f"Página {d.page}")


SimpleDocTemplate(
    sys.argv[1], pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    title="Atención a las observaciones generales del trámite – GPM", author="Dirección de Gestión Tecnológica",
).build(h, onFirstPage=pie, onLaterPages=pie)
