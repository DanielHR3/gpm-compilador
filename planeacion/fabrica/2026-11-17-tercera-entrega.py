"""Respuesta a la fabrica: tercera entrega de «Alta de Avisos de Testamento».

Genera el PDF que acompaña al .gpm de produccion del 2026-11-17. La fabrica contesto ese dia
las ocho preguntas de la segunda ronda (`~/Downloads/OBSERVACIONES TRÁMITE A. TESTAMENTO– GPM.pdf`).
Como el de la segunda ronda, describe ESE archivo (7 tareas, 41 campos) y no se recalcula. Lo
que aplica a todos los tramites quedo en `planeacion/pendientes.md` («Respuestas de la
fabrica (2026-11-17)») y en `CLAUDE.md` seccion 18.

Uso (necesita el extra `[guia]`, que trae reportlab):

    .venv/bin/python planeacion/fabrica/2026-11-17-tercera-entrega.py salida.pdf
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
    P("Atención a las respuestas de la fábrica – GPM", h1),
    P("<b>Trámite:</b> Alta de Avisos de Testamento &nbsp;·&nbsp; <b>Fecha:</b> 17 de noviembre de 2026"),
    P("<b>Archivo que se entrega:</b> Alta-de-Avisos-de-Testamento (produccion, 2026-11-17).gpm"),
    P("Gracias por las respuestas a las ocho preguntas. Este documento dice qué aplicamos de cada una en el "
      "archivo nuevo, qué no cambiamos y por qué, y qué sigue pendiente. El archivo pasó nuestra revisión "
      "automática sin hallazgos, pero <b>todavía no lo hemos importado a la plataforma</b>: si algo falla al "
      "importarlo, agradecemos el mensaje de error tal cual."),
    P("Resumen", h2),
]

filas = [
    ("#", "Pregunta", "Estado", "Qué cambió en el archivo"),
    ("1", "Condición de un paso", "Aplicada", "«Pago en Línea» pasa a ser un paso de «Selección de Modalidad de Pago», con regla. 8 tareas pasan a 7."),
    ("2", "Regla con selectores", "Sin cambio", "Los dos campos de las reglas devuelven un valor simple, no un objeto. Ver detalle."),
    ("3", "Acción de cobro", "En espera", "Queda pendiente del carrito de la pasarela, como indicaron."),
    ("4", "Documentos", "Diseño confirmado", "Falta la plantilla de cada documento para escribir su contenido."),
    ("5", "Dato de sesión", "Aplicada en parte", "«Nombre del Funcionario que Firma» toma las variables globales. «Pago en Línea Confirmado» depende del carrito."),
    ("6", "Fecha no futura", "Pendiente", "No conocemos cómo queda «Rangos específicos» dentro del archivo. Ver petición."),
    ("7", "Grupos de usuarios", "De nuestro lado", "Lo verificamos en la pestaña Usuarios al importar."),
    ("8", "Unir tareas", "Confirmado", "La ruta de banco o transferencia se queda en tres tareas."),
]
t = Table([[P(c, chicob if i == 0 else chico) for c in f] for i, f in enumerate(filas)],
          colWidths=[0.8 * cm, 4.0 * cm, 3.0 * cm, 9.2 * cm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), GUINDA), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F1F2")]),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
h += [t, P("El archivo en cifras: 7 tareas con 13 pasos (5 en modo visualización, 1 con condición), 9 vistas, "
           "41 campos, 8 conexiones (4 con condición), 3 acciones, 2 documentos y 3 eventos. Contra la entrega "
           "del 12 de noviembre: una tarea y una conexión menos; lo demás no cambia.", nota),
      P("Detalle por pregunta", h2)]


def obs(titulo, hecho, queda=None):
    b = [P(titulo, h3)]
    if hecho:
        b += [P("Qué se hizo", sub)] + L(hecho)
    if queda:
        b += [P("Qué queda", sub)] + L(queda)
    return b


h += obs("1. Condición de un paso (observación 3)", [
    "«Selección de Modalidad de Pago» y «Pago en Línea» son del Notario. Ahora son una sola tarea con dos pasos: "
    "el primero, en edición, donde elige la modalidad; el segundo, «Pago en Línea», en visualización y con la regla "
    + C % "@@modalidad_pago=='en_linea'" + ". Solo se muestra cuando el Notario elige pago en línea.",
    "La conexión «en línea» va ahora de esa tarea directo a «Importación a RENAT / Verificar Notario y Firmar». "
    "La de «banco o transferencia» no cambia.",
    "Lo aplicamos como regla general del compilador: una rama que atiende el mismo responsable y vuelve al flujo "
    "sin otra decisión pasa a ser un paso con condición. Si cambia el responsable, se queda como tarea.",
], [
    "Ninguno de los trámites publicados que tenemos de referencia trae un paso con regla, así que es la primera vez que "
    "la usamos. Lo comprobaremos al importar.",
])
h += obs("2. Regla con selectores (observación 7)", [
    "No cambiamos las reglas. Su recomendación aplica «si modalidad_pago es un selector con retorno estructurado», y en "
    "este archivo no lo es:",
    C % "modalidad_pago" + " es una lista con catálogo manual: cada opción tiene un valor simple ("
    + C % "en_linea" + ", " + C % "banco_o_transferencia" + ") y no devuelve un objeto. "
    + C % "tiene_observaciones" + " (conexiones 5191 y 5192) es un botón de opción con valores "
    + C % "si" + " y " + C % "no" + ".",
    "En una prueba nuestra en el portal, una regla " + C % "@@campo=='valor'" + " sobre una lista con valores simples "
    "hizo avanzar el flujo, y cuatro trámites publicados usan esa forma.",
    "La forma " + C % "->value" + " la reservamos para una lista con catálogo remoto que devuelve un objeto; este "
    "trámite no tiene ninguna.",
], [
    "Si al revisarlo ven que alguna de estas reglas falla al ejecutarse, nos ayudaría mucho saber en qué conexión "
    "y con qué dato.",
])
h += obs("3. Acción de cobro (observación 5)", None, [
    "«Monto a Pagar» sigue sin Acción. Esperamos a que el componente de carrito de la pasarela esté listo, como indicaron.",
])
h += obs("4. Documentos (observación 4)", [
    "Tomamos el diseño que confirman: una Acción de tipo variable arma el contenido, la plantilla cita esa variable y "
    "el evento se ejecuta después de capturar los datos y antes de mostrar el documento para firma, con el componente "
    "Documento Dinámico.",
], [
    "Los dos documentos («Archivo CSV» y «Oficio de contestación») siguen con contenido vacío ("
    + C % "return '';" + "). Nos falta la plantilla de cada uno con sus datos colocados; la estamos pidiendo al área de "
    "Simplificación. Cuando la tengamos movemos el evento a «Verificar Notario y Firmar» y agregamos el Documento "
    "Dinámico a esa vista.",
])
h += obs("5. Dato de sesión (observación 5)", [
    "«Nombre del Funcionario que Firma» lleva ahora como valor por defecto "
    + C % "@!nombres @!apellido_paterno @!apellido_materno" + ". Está en la vista «Verificar Notario y Firmar», que "
    "atiende el Área: la sesión es la del funcionario que firma.",
    "Lo aplicamos a cualquier trámite con un dato de solo lectura que sea el nombre del funcionario.",
], [
    "«Pago en Línea Confirmado» depende de la pasarela (pregunta 3).",
    "No sabemos todavía si la plataforma sustituye las variables " + C % "@!" + " en el valor por defecto de un "
    "campo o solo dentro de una Acción. Lo comprobaremos al importar; si lo saben, nos ahorra la prueba.",
])
h += obs("6. Fecha no futura", None, [
    "Las tres fechas («Fecha de expedición de testamento», «Fecha de Nacimiento», «Fecha de la Escritura») siguen solo "
    "con obligatoriedad.",
    "«Rangos específicos» se configura en el componente, pero ninguno de los trámites de referencia lo trae y no "
    "sabemos cómo queda escrito en el archivo. <b>Petición:</b> si tienen un trámite exportado con una fecha configurada "
    "así, con ese archivo lo resolvemos para todos los trámites. Si no, lo configuramos nosotros en la plataforma al "
    "importar y lo exportamos.",
])
h += obs("7. Grupos de usuarios", None, [
    "Al importar revisaremos en la pestaña Usuarios con qué nombre exacto existen «Notario» y «Area De Avisos De "
    "Testamento», y quiénes los integran.",
])
h += obs("8. Unir tareas (observación 2)", [
    "Se conserva la unión de «Importación a RENAT» con «Verificar Notario y Firmar».",
    "Las tres tareas de la ruta de banco o transferencia se quedan separadas porque cambia el responsable entre ellas.",
])

h += [P("Observaciones generales", h2)]
h += obs("Reglas de validación", [
    "13 de los 14 campos de texto de captura llevan regla de formato; la excepción es «Referencia de Pago». Las "
    "tres fechas dependen de la pregunta 6. Las listas, los botones de opción y los archivos llevan obligatoriedad: "
    "su valor ya lo limita la lista.",
], [
    "«Referencia de Pago» es alfanumérica pero el diseño no dice cuántos caracteres tiene. No le ponemos una longitud "
    "que no esté documentada; la pedimos a Simplificación.",
])
h += obs("Rutas cuando una validación no se aprueba", None, [
    "Siguen sin ruta para la respuesta «No» «¿Pago Validado?», «¿Importación validada en RENAT?», «Notario "
    "Verificado» y «Autoriza y Firma». El diseño del trámite no dice qué ocurre en esos casos y lo estamos "
    "consultando con Simplificación. No vamos a inventar esas rutas.",
])
h += obs("Información para validar", [
    "«Revisar la Solicitud» muestra primero la captura completa; «Validación Manual del Comprobante» muestra el "
    "comprobante; «Comprobante de Pago» muestra el formato generado.",
], [
    "«Importación a RENAT / Verificar Notario y Firmar» no muestra la captura del Notario: se apoya en el Archivo CSV, "
    "que aún sale vacío. Proponemos que abra con la captura en modo visualización y lo estamos confirmando con "
    "Simplificación.",
])

h += [P("Pendientes de nuestro lado", h2)]
h += L([
    "Importar el archivo a la plataforma y recorrerlo en el portal: el paso con condición, el nombre del funcionario y "
    "los grupos de usuarios.",
    "Conseguir de Simplificación las plantillas de los dos documentos, la longitud de «Referencia de Pago», las rutas "
    "del «No» y la vista para «Importación a RENAT».",
    "Confirmar con la dependencia el prefijo del folio (hoy «GPM», provisional).",
    "«Campos con Error» está descrito como una lista sin opciones definidas y sale como campo de texto.",
])


def pie(c, d):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(2 * cm, 1.2 * cm, "Alta de Avisos de Testamento · Respuesta a la fábrica · 2026-11-17")
    c.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm, f"Página {d.page}")


SimpleDocTemplate(
    sys.argv[1], pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    title="Atención a las respuestas de la fábrica – GPM", author="Dirección de Gestión Tecnológica",
).build(h, onFirstPage=pie, onLaterPages=pie)
