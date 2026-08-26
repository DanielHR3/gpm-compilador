#!/usr/bin/env python3
"""Genera la guia en PDF que se le manda al equipo de Simplificacion.

Uso:
    python scripts/generar_guia_equipo.py http://compilador.dgt.local:8000

La liga se pasa como argumento porque cambia: mientras el servicio viva en una
laptop depende de su IP, y esa IP se mueve. Regenerar la guia cuando cambie.
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


def generar(url: str, destino: Path):
    e = _estilos()
    doc = BaseDocTemplate(
        str(destino), pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=4.8 * cm, bottomMargin=2 * cm,
        title="Compilador GPM — Guía para el equipo de Simplificación",
        author="Dirección de Gestión Tecnológica",
    )
    marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    marco2 = Frame(doc.leftMargin, doc.bottomMargin, doc.width,
                   doc.height + 2.9 * cm, id="n2")
    doc.addPageTemplates([
        PageTemplate(id="p1", frames=[marco], onPage=lambda c, d: _encabezado(
            c, d, "Compilador GPM", "De tus documentos al archivo que se importa")),
        PageTemplate(id="pn", frames=[marco2], onPage=lambda c, d: _encabezado(c, d, "", "")),
    ])

    h = []
    h.append(Paragraph(
        "Esta herramienta toma los tres documentos que ya haces —<b>Análisis AS-IS</b>, "
        "<b>Propuesta TO-BE</b> y <b>Diccionario de Datos</b>— y genera el archivo que la DGT "
        "importa a la plataforma de modelado. Antes ese paso se hacía a mano.", e["p"]))

    h.append(Paragraph("Cómo entrar", e["h2"]))
    h.append(_caja(
        f'<font size="15"><b>{url}</b></font><br/><br/>'
        "Ábrela en tu navegador. No instalas nada, no descargas nada, no necesitas contraseña.",
        e))
    h.append(Spacer(1, 4))
    h.append(Paragraph(
        "Si la liga no abre, avisa a la DGT. No es algo que puedas arreglar desde tu equipo.",
        e["chico"]))

    h.append(Paragraph("Qué vas a hacer", e["h2"]))
    h.append(_pasos([
        ("Subir tus tres archivos",
         "El Diccionario de Datos es obligatorio: sin él no hay pantallas que generar. "
         "Los otros dos ayudan pero no detienen el proceso."),
        ("Revisar lo que entendió",
         "Verás las pantallas que encontró, cuántos campos tiene cada una, y una estimación "
         "de complejidad del trámite."),
        ("Resolver los huecos",
         "Es el paso importante. Abajo se explica qué son."),
        ("Recorrer el trámite",
         "El simulador te deja avanzar pantalla por pantalla, como lo vería el ciudadano. "
         "Sirve para detectar que algo no cuadra antes de que se construya."),
        ("Descargar el archivo",
         "Bajas el <b>.gpm</b> y se lo pasas a la DGT. Ellos lo importan a la plataforma."),
    ], e))

    h.append(Paragraph("Los huecos: lo más importante de entender", e["h2"]))
    h.append(Paragraph(
        "Un <b>hueco</b> es algo que la herramienta no pudo deducir de tus documentos y que "
        "decidió <b>no inventar</b>.", e["p"]))
    h.append(_caja(
        "Si te reporta 50 huecos <b>no está fallando</b>. Te está diciendo qué no puede saber "
        "por sí sola. Una herramienta que reportara cero huecos sobre documentos reales estaría "
        "adivinando, y esos errores no se notan hasta que el trámite ya está en producción.", e))

    h.append(Paragraph("Cómo lograr menos huecos", e["h2"]))
    h.append(Paragraph(
        "Entre más completo el Diccionario de Datos, menos huecos. Tres cosas ayudan mucho:",
        e["p"]))
    t = Table([
        [Paragraph("<b>En vez de esto</b>", e["celdaNeg"]),
         Paragraph("<b>Escribe esto</b>", e["celdaNeg"])],
        [Paragraph("La descripción del campo sin más", e["celda"]),
         Paragraph("La descripción y el nombre técnico:<br/>"
                   "<font face='Courier'>[Captura] Campo @@curp_solicitante</font>", e["celda"])],
        [Paragraph('Catálogo: "pendiente de confirmar"', e["celda"]),
         Paragraph("Catálogo con sus valores:<br/>"
                   "<font face='Courier'>Hombre · Mujer</font>", e["celda"])],
        [Paragraph("Encabezados de pantalla libres", e["celda"]),
         Paragraph("El formato de siempre:<br/>"
                   "<font face='Courier'>### Pantalla 3 — NOTARIO — Captura</font>", e["celda"])],
    ], colWidths=[6.4 * cm, 10.0 * cm])
    t.setStyle(TableStyle([
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
    h.append(t)

    h.append(Paragraph("Dos cosas que conviene saber", e["h2"]))
    h.append(KeepTogether([_caja(
        "<b>El flujo sale en línea recta.</b> Una pantalla tras otra, en orden. Las compuertas "
        "de tu diagrama TO-BE —los rombos de «si procede / si no procede»— se cuentan y se te "
        "reportan, pero <b>no se reproducen</b>. Hay que agregarlas a mano después.<br/><br/>"
        "Traducir sola una etiqueta como «si procede» a una condición sería justo el tipo de "
        "error que nadie nota hasta que ya está en producción.", e)]))
    h.append(Spacer(1, 7))
    h.append(_caja(
        "<b>La herramienta no toca tus archivos.</b> Los lee y nada más. No los modifica, no "
        "los borra, no los mueve. Puedes usarla las veces que quieras sin riesgo.", e))

    h.append(Paragraph("Si algo sale mal", e["h2"]))
    h.append(Paragraph(
        "Manda a la DGT el <b>mensaje de error completo</b> y el <b>nombre del expediente</b>. "
        "Con eso basta para diagnosticar. No hace falta que investigues nada.", e["p"]))
    h.append(Spacer(1, 10))
    h.append(Paragraph(
        "Esta herramienta va a cambiar conforme la usen. Si algo te resulta confuso, si un hueco "
        "no se entiende, o si el resultado no corresponde a tu trámite, dilo: eso es exactamente "
        "lo que sirve para mejorarla.", e["chico"]))

    doc.build(h)
    return destino


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    salida = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        "Guía — Compilador GPM (equipo de Simplificación).pdf")
    print("Generada:", generar(url, salida))
