#!/usr/bin/env python3
"""Genera la guia de instalacion en el equipo propio.

Camino alterno: se usa solo cuando NO hay un servidor con la herramienta
hospedada. Lo normal es que el equipo abra una liga y no instale nada.
"""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

# Paleta muestreada de capturas reales de la plataforma de modelado.
GUINDA = colors.HexColor("#5e132c")
GUINDA2 = colors.HexColor("#66132a")
TINTA = colors.HexColor("#1a1a1a")
GRIS = colors.HexColor("#6b7280")
LINEA = colors.HexColor("#e2d5d8")
FONDO = colors.HexColor("#fff9f9")

BASE = "Helvetica"
NEG = "Helvetica-Bold"


def _estilos():
    return {
        "titulo": ParagraphStyle("t", fontName=NEG, fontSize=19, leading=23,
                                 textColor=colors.white, spaceAfter=2),
        "subtitulo": ParagraphStyle("s", fontName=BASE, fontSize=9.5, leading=12,
                                    textColor=colors.white, spaceAfter=0),
        "h2": ParagraphStyle("h2", fontName=NEG, fontSize=12.5, leading=15,
                             textColor=GUINDA, spaceBefore=15, spaceAfter=6),
        "p": ParagraphStyle("p", fontName=BASE, fontSize=10, leading=14.5,
                            textColor=TINTA, alignment=TA_LEFT, spaceAfter=7),
        "chico": ParagraphStyle("c", fontName=BASE, fontSize=8.6, leading=12,
                                textColor=GRIS, spaceAfter=5),
        "liga": ParagraphStyle("l", fontName=NEG, fontSize=15, leading=19,
                               textColor=GUINDA, spaceAfter=3),
        "celda": ParagraphStyle("cel", fontName=BASE, fontSize=9.4, leading=13,
                                textColor=TINTA),
        "celdaNeg": ParagraphStyle("cn", fontName=NEG, fontSize=9.4, leading=13,
                                   textColor=GUINDA),
    }


def _encabezado(canvas, doc, titulo, subtitulo):
    canvas.saveState()
    canvas.setFillColor(FONDO)
    canvas.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)
    if doc.page == 1:
        canvas.setFillColor(GUINDA)
        canvas.rect(0, letter[1] - 3.4 * cm, letter[0], 3.4 * cm, stroke=0, fill=1)
        canvas.setFillColor(GUINDA2)
        canvas.rect(0, letter[1] - 4.0 * cm, letter[0], 0.6 * cm, stroke=0, fill=1)
        canvas.setFont(NEG, 19)
        canvas.setFillColor(colors.white)
        canvas.drawString(2 * cm, letter[1] - 2.0 * cm, titulo)
        canvas.setFont(BASE, 9.5)
        canvas.drawString(2 * cm, letter[1] - 2.7 * cm, subtitulo)
        canvas.setFont(BASE, 8.2)
        canvas.drawString(2 * cm, letter[1] - 3.75 * cm,
                          "Dirección de Gestión Tecnológica · Guía para el equipo de Simplificación")
    canvas.setFont(BASE, 7.6)
    canvas.setFillColor(GRIS)
    canvas.drawRightString(letter[0] - 2 * cm, 1.3 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _caja(texto, estilos, color=GUINDA, relleno=colors.white):
    t = Table([[Paragraph(texto, estilos["p"])]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, color),
        ("LINEBEFORE", (0, 0), (0, -1), 3.2, color),
        ("BACKGROUND", (0, 0), (-1, -1), relleno),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _pasos(filas, estilos):
    datos = []
    for n, (tit, desc) in enumerate(filas, 1):
        datos.append([
            Paragraph(f"<b>{n}</b>", ParagraphStyle(
                "n", fontName=NEG, fontSize=13, textColor=colors.white, alignment=1)),
            Paragraph(f"<b>{tit}</b><br/>{desc}", estilos["celda"]),
        ])
    t = Table(datos, colWidths=[1.1 * cm, 15.3 * cm])
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), GUINDA),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("BOX", (1, 0), (1, -1), 0.6, LINEA),
        ("LEFTPADDING", (1, 0), (1, -1), 11),
        ("RIGHTPADDING", (1, 0), (1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, -2), 3, FONDO),
    ]
    t.setStyle(TableStyle(estilo))
    return t


def generar(destino: Path):
    e = _estilos()
    doc = BaseDocTemplate(
        str(destino), pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=4.8 * cm, bottomMargin=2 * cm,
        title="Compilador GPM — Instalación en tu equipo",
        author="Dirección de Gestión Tecnológica",
    )
    marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    marco2 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height + 2.9 * cm, id="n2")
    doc.addPageTemplates([
        PageTemplate(id="p1", frames=[marco], onPage=lambda c, d: _encabezado(
            c, d, "Instalarlo en tu equipo", "Solo si la DGT te lo indicó")),
        PageTemplate(id="pn", frames=[marco2], onPage=lambda c, d: _encabezado(c, d, "", "")),
    ])

    h = []
    h.append(_caja(
        "<b>Antes de seguir: pregunta si hay una liga.</b> Lo normal es que la herramienta esté "
        "instalada en un servidor y solo tengas que abrir una dirección en el navegador, sin "
        "instalar nada.<br/><br/>"
        "Estas instrucciones son para cuando la DGT te dice que no hay liga disponible, o cuando "
        "necesitas usarla sin conexión a la red de la oficina.", e))

    h.append(Paragraph("Lo que vas a hacer", e["h2"]))
    h.append(Paragraph(
        "Copiar una carpeta a tu computadora y darle doble clic a un archivo. Nada más. "
        "No necesitas instalar programas ni saber programar.", e["p"]))

    h.append(Paragraph("Paso a paso", e["h2"]))
    h.append(_pasos([
        ("Guarda la carpeta que te enviaron",
         "Te llega comprimida, como <b>gpm-compilador.zip</b>. Guárdala en <b>Documentos</b> y "
         "dale doble clic para descomprimirla. Queda una carpeta con el mismo nombre."),
        ("Entra a la carpeta y busca el archivo de arranque",
         "Se llama <b>Abrir Compilador GPM.command</b>. Es el único que necesitas."),
        ("Dale clic derecho, no doble clic",
         "Clic derecho sobre el archivo, y elige <b>Abrir</b>. Aparecerá un aviso; presiona "
         "<b>Abrir</b> otra vez.<br/>"
         "<i>Esto solo pasa la primera vez.</i> Es una protección de la Mac para archivos que no "
         "vienen de la App Store. Después bastará el doble clic."),
        ("Espera un minuto la primera vez",
         "Se abre una ventana negra con texto. Es normal: está preparando todo. Tarda alrededor "
         "de un minuto <b>solo la primera vez</b>; después abre en segundos."),
        ("Se abre solo en tu navegador",
         "Cuando termine, tu navegador abre la herramienta. Ya puedes usarla igual que si fuera "
         "una página de internet."),
    ], e))

    h.append(Paragraph("Cómo cerrarla", e["h2"]))
    h.append(Paragraph(
        "Cierra la ventana negra. Si te pide confirmación, acepta. Cerrar solo la pestaña del "
        "navegador no la apaga.", e["p"]))

    tabla_problemas = Table([
        [Paragraph("<b>Lo que ves</b>", e["celdaNeg"]),
         Paragraph("<b>Qué hacer</b>", e["celdaNeg"])],
        [Paragraph('"No se puede abrir porque proviene de un desarrollador no identificado"',
                   e["celda"]),
         Paragraph("Clic derecho sobre el archivo, <b>Abrir</b>, y <b>Abrir</b> de nuevo en el "
                   "aviso. Es lo del paso 3.", e["celda"])],
        [Paragraph("La ventana negra se cierra sola de inmediato", e["celda"]),
         Paragraph("Avisa a la DGT. Mándales una foto de la ventana antes de que se cierre, si "
                   "alcanzas.", e["celda"])],
        [Paragraph('Dice "Operation not permitted" al subir tus archivos', e["celda"]),
         Paragraph("La Mac está bloqueando el acceso a tus carpetas. Mueve el expediente a una "
                   "carpeta fuera de <b>Documentos</b>, <b>Escritorio</b> y <b>Descargas</b>, "
                   "e inténtalo otra vez.", e["celda"])],
        [Paragraph("El navegador no abre solo", e["celda"]),
         Paragraph("Abre tu navegador y escribe: <font face='Courier'>127.0.0.1:8000</font>",
                   e["celda"])],
    ], colWidths=[7.0 * cm, 9.4 * cm])
    tabla_problemas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINEA),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    # Sin esto el encabezado queda huerfano al pie de una pagina y su tabla en la siguiente.
    h.append(KeepTogether([Paragraph("Si algo no sale", e["h2"]), tabla_problemas]))

    h.append(Paragraph("Una desventaja de instalarlo", e["h2"]))
    h.append(_caja(
        "Cada quien tendrá su propia copia, y no se actualizan solas. Cuando la DGT mejore la "
        "herramienta, tendrán que enviarte la carpeta otra vez.<br/><br/>"
        "Por eso la liga compartida es mejor cuando esté disponible: ahí todos usan siempre la "
        "última versión sin hacer nada.", e))

    h.append(Spacer(1, 10))
    h.append(Paragraph(
        "Para saber cómo usarla una vez abierta, consulta la otra guía: "
        "<b>«Compilador GPM — De tus documentos al archivo que se importa»</b>.", e["chico"]))

    doc.build(h)
    return destino


if __name__ == "__main__":
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "Guía — Instalación en tu equipo.pdf")
    print("Generada:", generar(salida))
