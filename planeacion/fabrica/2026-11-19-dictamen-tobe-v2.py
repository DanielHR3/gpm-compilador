"""Propuesta TO-BE del Dictamen de Impacto en la Movilidad, segunda forma (2026-11-19).

Gis (fábrica) pidió el TO-BE. La primera versión (`2026-11-19-dictamen-contexto.py`) se veía
generada: tabla de «sigue», colores de marca, diagrama vertical. Esta es la misma lógica con
forma de documento de analista: pasos narrados, diagrama por carriles en horizontal, tareas
con verbo. Contenido fijo (no se lee del expediente).

Uso (extra `[guia]`, requiere `dot`):

    .venv/bin/python planeacion/fabrica/2026-11-19-dictamen-tobe-v2.py salida.pdf
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer)

NEGRO = colors.HexColor("#222222")
base = ParagraphStyle("b", fontName="Helvetica", fontSize=10.5, leading=15, spaceAfter=7, textColor=NEGRO)
titulo = ParagraphStyle("t", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=2)
subt = ParagraphStyle("st", parent=base, fontSize=10, textColor=colors.HexColor("#555555"), spaceAfter=14)
h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=11, spaceBefore=10, spaceAfter=5, keepWithNext=1)
paso = ParagraphStyle("p", parent=base, leftIndent=18, firstLineIndent=-18)
nota = ParagraphStyle("n", parent=base, fontSize=9.5, leading=13, leftIndent=12, bulletIndent=0)


def P(t, s=base, **kw):
    return Paragraph(t, s, **kw)


# --- Diagrama por carriles ---------------------------------------------------

CARRILES = [
    ("sol", "Persona solicitante", [
        ("ini", "inicio", ""),
        ("a1", "tarea", "Selecciona tipo y\\ntamaño del proyecto"),
        ("a2", "tarea", "Genera referencia\\ny realiza el pago"),
        ("a3", "tarea", "Captura datos generales\\n(física o moral)"),
        ("a4", "tarea", "Anexa documentación"),
        ("a11", "tarea", "Atiende la prevención\\ny anexa lo faltante"),
        ("a17", "tarea", "Consulta y descarga\\nla resolución"),
        ("a18", "tarea", "Consulta el acuerdo\\nde cancelación"),
        ("fin", "fin", ""),
    ]),
    ("dgms", "Dirección General de\\nMovilidad Sustentable", [
        ("a5", "tarea", "Valida el pago"),
        ("g1", "dec", "¿Pagó en\\n5 días\\nhábiles?"),
        ("a6", "tarea", "Revisa requisitos"),
        ("g2", "dec", "¿Cumple?"),
        ("a7", "tarea", "Elabora acuerdo\\ncon prevención"),
        ("a8", "tarea", "Elabora acuerdo\\ninicial"),
        ("a12", "tarea", "Revisa la\\nsolventación"),
        ("g5", "dec", "¿Solventó?"),
        ("a13", "tarea", "Analiza el estudio y\\nemite la resolución"),
        ("a15", "tarea", "Elabora acuerdo\\nde cancelación"),
    ]),
    ("dgn", "Dirección General\\nde Normatividad", [
        ("a9", "tarea", "Valida fundamento\\n(acuerdo con prevención)"),
        ("g3", "dec", "¿Correcto?"),
        ("a10", "tarea", "Valida fundamento\\n(acuerdo inicial)"),
        ("g4", "dec", "¿Correcto?"),
        ("a14", "tarea", "Valida fundamento\\n(resolución)"),
        ("g6", "dec", "¿Correcto?"),
        ("a16", "tarea", "Valida fundamento\\n(cancelación)"),
        ("g7", "dec", "¿Correcto?"),
    ]),
]

FLUJOS = [
    ("ini", "a1", ""), ("a1", "a2", ""), ("a2", "a3", ""), ("a3", "a4", ""), ("a4", "a5", ""),
    ("a5", "g1", ""), ("g1", "a6", "Sí"), ("g1", "a15", "No"),
    ("a6", "g2", ""), ("g2", "a8", "Sí"), ("g2", "a7", "No"),
    ("a7", "a9", ""), ("a9", "g3", ""), ("g3", "a11", "Sí"), ("g3", "a7", "No"),
    ("a8", "a10", ""), ("a10", "g4", ""), ("g4", "a13", "Sí"), ("g4", "a8", "No"),
    ("a11", "a12", ""), ("a12", "g5", ""), ("g5", "a13", "Sí"), ("g5", "a15", "No"),
    ("a13", "a14", ""), ("a14", "g6", ""), ("g6", "a17", "Sí"), ("g6", "a13", "No"),
    ("a15", "a16", ""), ("a16", "g7", ""), ("g7", "a18", "Sí"), ("g7", "a15", "No"),
    ("a17", "fin", ""), ("a18", "fin", ""),
]


# Posición fija (columna, fila); fila 0-1 solicitante, 2-3 DGMS, 4-5 DGN.
POS = {
    "ini": (0, 0), "a1": (1, 0), "a2": (2, 0), "a3": (3, 0), "a4": (4, 0),
    "a5": (5, 2), "g1": (6, 2), "a6": (7, 2), "g2": (8, 2), "a8": (9, 2), "a7": (9, 3),
    "a10": (10, 4), "g4": (11, 4), "a9": (10, 5), "g3": (11, 5),
    "a11": (12, 0), "a12": (13, 3), "g5": (14, 3), "a13": (15, 2), "a15": (15, 3),
    "a14": (16, 4), "g6": (17, 4), "a16": (16, 5), "g7": (17, 5),
    "a17": (18, 0), "a18": (18, 1), "fin": (19, 0.5),
}
COL, X0, FILA, ALTO_CARRIL = 128, 150, 66, 156
ANCHO = X0 + 19 * COL + 70
ALTO = 3 * ALTO_CARRIL


def _y(fila):
    carril, sub = divmod(fila, 2) if fila != 0.5 else (0, 0.5)
    return ALTO - (carril * ALTO_CARRIL + 45 + sub * FILA)


def diagrama(png):
    """PNG transparente del flujo; los carriles los pinta `Carriles` debajo."""
    g = ['digraph G { splines=ortho; bgcolor=transparent; pad=0; dpi=300; outputorder=edgesfirst;',
         'node [fontname="Helvetica", fontsize=9, color="#3a3a3a", penwidth=0.9, fixedsize=true];',
         'edge [fontname="Helvetica", fontsize=8, color="#3a3a3a", arrowsize=0.55, penwidth=0.8];',
         f'c0 [pos="0,0!", style=invis, label="", width=0.01, height=0.01]; c1 [pos="{ANCHO},{ALTO}!", style=invis, label="", width=0.01, height=0.01];']
    for _, _, nodos in CARRILES:
        for nid, tipo, etq in nodos:
            col, fila = POS[nid]
            xy = f'pos="{X0 + col * COL},{_y(fila)}!"'
            if tipo == "tarea":
                g.append(f'{nid} [{xy}, label="{etq}", shape=box, style="rounded,filled", fillcolor="#FFFFFF", '
                         'width=1.62, height=0.62];')
            elif tipo == "dec":
                g.append(f'{nid} [{xy}, label="{etq}", shape=diamond, style=filled, fillcolor="#FFF6D6", '
                         'fontsize=7.5, width=0.95, height=0.72];')
            elif tipo == "inicio":
                g.append(f'{nid} [{xy}, label="", shape=circle, width=0.28, style=filled, fillcolor="#DDEFD9"];')
            else:
                g.append(f'{nid} [{xy}, label="", shape=doublecircle, width=0.26, style=filled, fillcolor="#F2D6D6"];')
    for a, b, etq in FLUJOS:
        g.append(f'{a} -> {b} [xlabel="{etq}"];' if etq else f"{a} -> {b};")
    g.append("}")
    subprocess.run(["neato", "-n2", "-Tpng", "-o", str(png)], input="\n".join(g).encode(), check=True)


class Carriles(Flowable):
    """Carriles de borde a borde con el nombre a la izquierda, y el flujo encima."""

    def __init__(self, png, ancho):
        super().__init__()
        self.png, self.width = png, ancho
        self.height = ancho * ALTO / ANCHO

    def draw(self):
        c, f = self.canv, self.width / ANCHO
        for i, (_, nombre, _) in enumerate(CARRILES):
            y = self.height - (i + 1) * ALTO_CARRIL * f
            c.setStrokeColor(colors.HexColor("#8a8a8a"))
            c.setLineWidth(0.6)
            c.setFillColor(colors.HexColor("#FAFAFA") if i % 2 == 0 else colors.white)
            c.rect(0, y, self.width, ALTO_CARRIL * f, fill=1)
            c.setFillColor(colors.HexColor("#EFEFEF"))
            c.rect(0, y, 70 * f, ALTO_CARRIL * f, fill=1)
            c.saveState()
            c.translate(40 * f, y + ALTO_CARRIL * f / 2)
            c.rotate(90)
            c.setFillColor(NEGRO)
            c.setFont("Helvetica-Bold", 8)
            lineas = nombre.split("\\n")
            for k, t in enumerate(lineas):
                c.drawCentredString(0, (len(lineas) - 1) * 5 - k * 10, t)
            c.restoreState()
        c.drawImage(str(self.png), 0, 0, self.width, self.height, mask="auto")


# --- Texto -------------------------------------------------------------------

PASOS = [
    "La persona solicitante entra a la plataforma, elige el trámite e indica el tipo de proyecto. "
    "El rango de viviendas fija el costo: 35 UMA de 11 a 100 viviendas, 70 UMA de 101 a 500, "
    "105 UMA de 501 a 1,000 y 125 UMA para más de 1,000.",
    "Con ese monto genera su referencia y paga. Tiene 5 días hábiles para hacerlo.",
    "Captura sus datos. Si es persona física se le piden nombre, CURP y contacto; si es persona moral, "
    "los datos de la empresa y de su representante legal. En los dos casos se pide la ubicación del proyecto.",
    "Anexa la identificación oficial, el título de propiedad o posesión del predio y el Estudio de "
    "Impacto en la Movilidad firmado por profesionista acreditado. El comprobante de pago es opcional.",
    "La DGMS confirma que el pago entró a tiempo. Si no, se elabora el acuerdo de cancelación (paso 11).",
    "Si el pago está bien, revisa los requisitos publicados en el RUTS y elabora el acuerdo inicial. "
    "Cuando falta algo, el acuerdo sale con prevención y lista los puntos faltantes.",
    "La DGN revisa el fundamento legal del acuerdo. Si tiene observaciones, el acuerdo regresa a la "
    "DGMS para corregirlo; no avanza hasta que la DGN lo valida.",
    "Con prevención, la persona solicitante recibe el acuerdo y anexa lo que le faltó dentro del plazo "
    "que se le da (3 días hábiles).",
    "La DGMS revisa lo que se anexó. Si quedó solventado, sigue al análisis; si no, se cancela.",
    "La DGMS analiza el estudio y emite la resolución: aprobado, aprobado condicionado o negado. "
    "La DGN valida el fundamento antes de que se notifique.",
    "El acuerdo de cancelación también pasa por la DGN antes de notificarse.",
    "Al final la persona consulta y descarga la resolución o, en su caso, el acuerdo de cancelación.",
]


def construir(salida):
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "tobe.png"
        diagrama(png)
        ancho_d = ANCHO * 0.7
        img = Carriles(png, ancho_d)
        hoja = (ancho_d + 3 * cm, img.height + 4.6 * cm)

        h = [P("Dictamen de Impacto en la Movilidad", titulo),
             P("Propuesta de proceso (TO-BE) · noviembre 2026", subt),
             P("Objetivo", h2),
             P("Que la solicitud, el pago, la revisión y la entrega del dictamen se hagan completos en línea. "
               "La persona solicitante ya no lleva documentos a ventanilla y la DGN valida cada acuerdo antes "
               "de notificarlo, sin que el expediente vaya y venga en papel."),
             P("Participan", h2),
             P("La persona solicitante (física o moral, normalmente el desarrollador), la Dirección General de "
               "Movilidad Sustentable (DGMS), que revisa y resuelve, y la Dirección General de Normatividad "
               "(DGN), que valida el fundamento legal de lo que firma la DGMS."),
             P("Cómo queda el proceso", h2)]
        h += [P(f"{i}.&nbsp;&nbsp;{t}", paso) for i, t in enumerate(PASOS, 1)]
        h += [P("Consideraciones", h2),
              P("La firma electrónica, la cédula de notificación y el aviso por correo los hace la plataforma "
                "al cerrar cada acuerdo; por eso no aparecen como actividades en el diagrama.", nota,
                bulletText="•"),
              P("Falta que la dependencia confirme la clasificación del proyecto y los métodos y proveedores "
                "de pago.", nota, bulletText="•"),
              NextPageTemplate("horizontal"), PageBreak(),
              P("Diagrama", h2), Spacer(1, 4), img]

        def pie(c, d):
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor("#777777"))
            w = c._pagesize[0]
            c.drawRightString(w - 2 * cm, 1.1 * cm, str(d.page))

        doc = BaseDocTemplate(str(salida), title="Dictamen de Impacto en la Movilidad - Propuesta TO-BE",
                              author="", creator="")
        v = Frame(2.2 * cm, 2 * cm, LETTER[0] - 4.4 * cm, LETTER[1] - 4.2 * cm, id="v")
        hz = Frame(1.5 * cm, 1.6 * cm, hoja[0] - 3 * cm, hoja[1] - 3 * cm, id="h")
        doc.addPageTemplates([PageTemplate("vertical", [v], onPage=pie, pagesize=LETTER),
                              PageTemplate("horizontal", [hz], onPage=pie, pagesize=hoja)])
        doc.build(h)


if __name__ == "__main__":
    construir(Path(sys.argv[1]))
    print("listo")
