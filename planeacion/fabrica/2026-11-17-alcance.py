"""Alcance a la tercera entrega de «Alta de Avisos de Testamento» (2026-11-17, tarde).

La entrega de la mañana (`2026-11-17-tercera-entrega.py`) ya se había enviado cuando la prueba
en el portal (procesos 1141 y 1143, trámites 24177, 24186 y 24187; acta
`planeacion/actas/2026-11-17-importacion-tercera-entrega-testamento.md`) encontró tres
defectos. Este documento acompaña al `.gpm` corregido. Describe ESE archivo y no se recalcula.

Uso (extra `[guia]`):

    .venv/bin/python planeacion/fabrica/2026-11-17-alcance.py salida.pdf
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
    P("Alcance a la entrega del 17 de noviembre – GPM", h1),
    P("<b>Trámite:</b> Alta de Avisos de Testamento &nbsp;·&nbsp; <b>Fecha:</b> 17 de noviembre de 2026"),
    P("<b>Archivo que sustituye al de esta mañana:</b> Alta-de-Avisos-de-Testamento (produccion, 2026-11-17, corregido).gpm"),
    P("Después de enviar el archivo de esta mañana lo importamos a la plataforma y recorrimos el trámite en el "
      "portal, como ciudadano y como servidor público. Encontramos tres defectos de nuestro lado y los "
      "corregimos. Este archivo corregido <b>sí se probó en la plataforma</b>: la ruta de banco o transferencia "
      "completa, de la captura a la firma, y la ruta en línea hasta la selección de modalidad."),
    P("Qué cambió", h2),
]

filas = [
    ("#", "Defecto encontrado en el portal", "Corrección", "Comprobado"),
    ("1", "El Notario no podía iniciar: «Usuario no puede iniciar este proceso». Sus tareas iban restringidas a un grupo.",
     "Las tareas del Notario van con acceso público, como en su export de este trámite.", "Sí: el ciudadano inicia y captura."),
    ("2", "Con «@@modalidad_pago=='en_linea'» el trámite se finalizaba al salir de la selección de modalidad, y el paso «Pago en Línea» no aparecía.",
     "Las reglas sobre un selector usan ->value, en pasos y en conexiones.", "Sí: en línea muestra el paso; banco no lo muestra y continúa a «Generar y Cargar Formato»."),
    ("3", "«Número de Folio» salía vacío.",
     "La acción del folio ya no suma 1 al último folio guardado (un texto); toma el número de la serie GPM del año.", "Sí: GPM-2026-00001 y GPM-2026-00002 en dos trámites."),
]
t = Table([[P(c, chicob if i == 0 else chico) for c in f] for i, f in enumerate(filas)],
          colWidths=[0.7 * cm, 5.6 * cm, 5.6 * cm, 5.1 * cm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), GUINDA), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F1F2")]),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
h += [t]

h += [P("Una corrección a lo que dijimos esta mañana", h2),
      P("En el documento de esta mañana sostuvimos que " + C % "->value" + " no hacía falta porque "
        + C % "modalidad_pago" + " devuelve un valor simple. <b>Nos equivocamos</b>: en el portal, la regla sin "
        + C % "->value" + " sobre ese selector no se cumple ni en el paso ni en la conexión. Su recomendación "
        "(preguntas 1 y 2) era la correcta. Un botón de opción (" + C % "tiene_observaciones" + ") sí funciona con "
        "la forma simple, y la visibilidad de campos funcionó con las dos formas.")]

h += [P("Lo que se comprobó en el portal", h2)]
h += L([
    "Cada tarea del Área abre primero, en modo visualización, la vista que revisa, y después la propia.",
    "«Pago en Línea» es un paso de «Selección de Modalidad de Pago»: aparece solo con «En línea».",
    "«Nombre del Funcionario que Firma» se llena solo con " + C % "@!nombres @!apellido_paterno @!apellido_materno"
    + ": mostró el nombre del servidor público que tenía la tarea.",
    "Los campos condicionados aparecen cuando corresponde (por ejemplo, «Número de Folio RENAT» al validar la importación).",
    "La ruta de banco o transferencia terminó completa: siete etapas en estado «Completado».",
])

h += [P("Un aviso sobre la forma del folio en sus exports", h2),
      P("La acción de folio de sus exports (por ejemplo, la de Constancia de No Infracción) suma 1 al último valor "
        "guardado de la variable, y ese valor es un folio como «CNIVA-2026-00003». En PHP 8 esa suma lanza un error "
        "en cuanto existe un folio guardado, así que el folio queda vacío desde el segundo trámite. Además, varios "
        "trámites usan el mismo nombre de variable (" + C % "numero_folio" + "). Lo comprobamos en PHP 8.3 con los "
        "dos códigos. Si les sirve, la forma que usamos ahora filtra por prefijo y año y toma el número del final.")]

h += [P("Preguntas", h2)]
preg = [
    ("Tareas del solicitante después de la primera.",
     "«Selección de Modalidad de Pago» y «Comprobante de Pago» son del Notario y van con acceso público, como en su "
     "export. En el portal no le llegaron al ciudadano que inició: quedaron en la bolsa de pendientes del servidor "
     "público. ¿Cómo se asigna una tarea al mismo solicitante que inició el trámite?"),
    ("Grupo del Área.",
     "La plataforma descarta en silencio el grupo «Area De Avisos De Testamento» porque no existe. Para probar "
     "usamos un grupo de pruebas. ¿Qué grupo se va a usar en producción, o lo crean ustedes?"),
    ("Pendientes de la ronda anterior.",
     "Siguen abiertas la acción de cobro (carrito de la pasarela), un ejemplo exportado de «Rangos específicos» "
     "para fechas y uno de «Documento Dinámico»."),
]
for i, (t_, c_) in enumerate(preg, 1):
    h.append(P(f"<b>{i}. {t_}</b> {c_}", preg_s))


def pie(c, d):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(2 * cm, 1.2 * cm, "Alta de Avisos de Testamento · Alcance a la entrega del 17-nov")
    c.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm, f"Página {d.page}")


SimpleDocTemplate(
    sys.argv[1], pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    title="Alcance a la entrega del 17 de noviembre – GPM", author="Dirección de Gestión Tecnológica",
).build(h, onFirstPage=pie, onLaterPages=pie)
