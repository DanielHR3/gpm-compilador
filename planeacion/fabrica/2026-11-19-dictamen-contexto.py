"""Contexto del `.gpm` de «Dictamen de Impacto en la Movilidad» para la fábrica (2026-11-19).

El `.gpm` se envió sin documentos (P-28). Este guion arma dos PDF a partir del expediente
reescrito el 2026-11-18: la Propuesta TO-BE (texto + diagrama) y el Diccionario de Datos.
Sin rastro del compilador: no salen `@@`, etiquetas `[Captura]`/`[Solo lectura]` ni la
columna «Componente Sugerido (GPM)» tal cual; el nombre de la variable sí sale (es el del
`.gpm`, y les sirve para cruzarlo).

Uso (extra `[guia]`, requiere `dot` de Graphviz):

    .venv/bin/python planeacion/fabrica/2026-11-19-dictamen-contexto.py \\
        "<carpeta de insumos>" "<carpeta de salida>"
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (CondPageBreak, Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Table, TableStyle)

TRAMITE = "Dictamen de Impacto en la Movilidad"
FECHA = "19 de noviembre de 2026"
GUINDA = colors.HexColor("#691C32")
base = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
h1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=GUINDA, spaceAfter=4)
h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=GUINDA, spaceBefore=12, spaceAfter=6, keepWithNext=1)
h3 = ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=10, spaceAfter=4)
chico = ParagraphStyle("c", parent=base, fontSize=8, leading=10, spaceAfter=0)
chicob = ParagraphStyle("cb", parent=chico, fontName="Helvetica-Bold", textColor=colors.white)
vin = ParagraphStyle("v", parent=base, leftIndent=14, bulletIndent=4, spaceAfter=3)
ESTILO_TABLA = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), GUINDA), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F1F2")]),
    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])
ACTORES = {
    "solicitante": ("Persona solicitante", "#E4EFEA", "#4C8C6B"),
    "dgms": ("Dirección General de Movilidad Sustentable (DGMS)", "#F5E6DF", "#B97A56"),
    "dgn": ("Dirección General de Normatividad (DGN)", "#E6E4F2", "#6B5FA6"),
}


def P(t, s=base):
    return Paragraph(t, s)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- Diccionario -------------------------------------------------------------

def leer_diccionario(ruta):
    """[(numero, actor, nombre, [fila dict])] de las pantallas del Diccionario."""
    pantallas, actual, cols = [], None, None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        m = re.match(r"### Pantalla (\d+) — (.+?) — (.+)", linea)
        if m:
            actual = (int(m[1]), m[2].strip(), m[3].strip(), [])
            pantallas.append(actual)
            cols = None
            continue
        if actual and linea.startswith("|"):
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if cols is None:
                cols = celdas
            elif not set("".join(celdas)) <= set("- "):
                actual[3].append(dict(zip(cols, celdas)))
    return pantallas


def limpiar_descripcion(desc):
    """(uso, variable, texto) sin etiqueta inicial ni «Campo `@@x`.»."""
    uso = "Captura"
    m = re.match(r"\[([^\]]+)\]\s*", desc)
    if m:
        etiqueta = m[1].lower()
        uso = "Generado por el sistema" if "generado" in etiqueta else (
            "Solo lectura" if "lectura" in etiqueta else "Captura")
        desc = desc[m.end():]
    var = ""
    m = re.match(r"Campo `@@([a-z0-9_]+)`\.\s*", desc)
    if m:
        var, desc = m[1], desc[m.end():]
    return uso, var, desc.strip()


def visibilidad(t):
    t = t.replace("Visible y obligatorio solo si", "Solo si")
    return t.replace('"', "«", 1).replace('"', "»", 1)


def pdf_diccionario(pantallas, salida):
    ancho = landscape(LETTER)[0] - 3 * cm
    h = [P(f"Diccionario de Datos – {TRAMITE}", h1),
         P(f"<b>Fecha:</b> {FECHA} &nbsp;·&nbsp; Acompaña al archivo «{TRAMITE}.gpm»"),
         P("Cada pantalla corresponde a un paso del trámite; el actor es quien la atiende. La columna "
           "<b>Variable</b> es el nombre del campo en el archivo .gpm. Los campos <b>generados por el "
           "sistema</b> son de solo lectura y los llena una acción de la plataforma."),
         P("Pendiente de definir", h2)]
    h += [Paragraph(t, vin, bulletText="•") for t in [
        "Catálogos que el entregable no define: <b>Clasificación del proyecto</b> (pantalla 1), "
        "<b>Método de pago</b> y <b>Proveedor de pago</b> (pantalla 2).",
        "Cálculo de <b>Monto en UMA</b>, <b>Referencia de pago</b>, <b>Vigencia de la referencia</b> y "
        "<b>Total a pagar</b>: dependen de la pasarela de pago.",
        "Plantillas de los oficios (acuerdos y resolución): el contenido se captura en cada pantalla, "
        "falta el formato del documento que se firma.",
        "Grupos de la plataforma para la DGMS y la DGN.",
    ]]
    cab = ["Campo", "Variable", "Uso", "Componente", "Oblig.", "Visibilidad", "Límite", "Catálogo", "Ejemplo", "Descripción"]
    pesos = [2.3, 2.2, 1.4, 1.9, 1.1, 2.2, 1.6, 2.6, 2.0, 3.4]
    anchos = [ancho * p / sum(pesos) for p in pesos]
    for num, actor, nombre, filas in pantallas:
        datos = [[P(c, chicob) for c in cab]]
        for f in filas:
            uso, var, desc = limpiar_descripcion(f["Descripción"])
            comp = re.sub(r"\s*\((select|input|radio|textarea|uploader|calendario)\)", "", f["Componente Sugerido (GPM)"])
            na = lambda v: "" if v == "N/A" else v  # noqa: E731
            datos.append([P(esc(x), chico) for x in [
                f["Nombre del Campo"], var, uso, comp, f["Obligatorio"],
                visibilidad(f["Condición de Visibilidad"]), na(f["Límite/Especificaciones"]),
                na(f["Catálogo de Valores"]), na(f["Ejemplo Real"]), desc]])
        t = Table(datos, colWidths=anchos, repeatRows=1)
        t.setStyle(ESTILO_TABLA)
        actor = {"PERSONA SOLICITANTE": "Persona solicitante"}.get(actor, actor.title().replace(" De ", " de "))
        h += [CondPageBreak(4 * cm), P(f"Pantalla {num} · {nombre} <font color='#666666'>— {actor}</font>", h3), t]

    def pie(c, d):
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(1.5 * cm, 1 * cm, f"{TRAMITE} · Diccionario de Datos")
        c.drawRightString(landscape(LETTER)[0] - 1.5 * cm, 1 * cm, f"Página {d.page}")

    SimpleDocTemplate(str(salida), pagesize=landscape(LETTER), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                      topMargin=1.5 * cm, bottomMargin=1.6 * cm, title=f"Diccionario de Datos – {TRAMITE}",
                      author="Dirección de Gestión Tecnológica").build(h, onFirstPage=pie, onLaterPages=pie)


# --- TO-BE -------------------------------------------------------------------

def leer_tobe(ruta, preguntas):
    texto = ruta.read_text(encoding="utf-8")
    resumen = texto.split("```mermaid")[0].split("\n", 1)[1].strip()
    mmd = texto.split("```mermaid")[1].split("```")[0]
    nodos, aristas = {}, []
    for linea in mmd.splitlines():
        for nid, forma, etiqueta, clase in re.findall(
                r"(\w+)(\(\[|\[|\{)\"?(.+?)\"?(?:\]\)|\]|\}):::(\w+)", linea):
            if forma == "{":
                var = re.search(r"@@(\w+)", etiqueta)[1]
                etiqueta = preguntas.get(var, var)
            elif ":" in etiqueta:
                etiqueta = etiqueta.split(":", 1)[1].strip()
            nodos[nid] = (forma, etiqueta, clase)
        m = re.match(r"\s*(\w+)(?:\W.*?)?\s*-->(?:\|([^|]+)\|)?\s*(\w+)", linea)
        if m and "-->" in linea:
            origen = linea.split("-->")[0].strip()
            origen = re.match(r"\w+", origen)[0]
            aristas.append((origen, m[2] or "", m[3]))
    return resumen, nodos, aristas


def diagrama(nodos, aristas, png):
    g = ['digraph G { rankdir=TB; nodesep=0.35; ranksep=0.4; dpi=200;',
         'node [fontname="Helvetica", fontsize=11, style="filled,rounded", shape=box, margin="0.15,0.06"];',
         'edge [fontname="Helvetica", fontsize=10, color="#555555"];']
    for nid, (forma, etq, clase) in nodos.items():
        _, relleno, borde = ACTORES[clase]
        shape = {"{": "diamond", "([": "oval"}.get(forma, "box")
        extra = ', style="filled", fontsize=10' if shape == "diamond" else ""
        g.append(f'{nid} [label="{etq}", shape={shape}, fillcolor="{relleno}", color="{borde}"{extra}];')
    for a, etq, b in aristas:
        g.append(f'{a} -> {b} [label="{etq}"];' if etq else f"{a} -> {b};")
    g.append("}")
    subprocess.run(["dot", "-Tpng", "-o", str(png)], input="\n".join(g).encode(), check=True)


def pdf_tobe(resumen, nodos, aristas, salida, tmp):
    png = Path(tmp) / "tobe.png"
    diagrama(nodos, aristas, png)
    img = Image(str(png))
    alto_max, ancho_max = 22 * cm, LETTER[0] - 4 * cm
    esc_ = min(alto_max / img.imageHeight, ancho_max / img.imageWidth)
    img.drawWidth, img.drawHeight = img.imageWidth * esc_, img.imageHeight * esc_

    tareas = [(nid, e, c) for nid, (f, e, c) in nodos.items() if f == "["]
    filas = [["#", "Tarea", "Responsable", "Sigue"]]
    for i, (nid, etq, clase) in enumerate(sorted(tareas, key=lambda x: int(x[0][1:])), 1):
        sig = []
        for a, cond, b in aristas:
            if a != nid:
                continue
            if nodos[b][0] == "{":
                for a2, c2, b2 in aristas:
                    if a2 == b:
                        sig.append(f"{c2}: {nodos[b2][1]}" if nodos[b2][0] != "([" else f"{c2}: fin")
            else:
                sig.append(nodos[b][1] if nodos[b][0] != "([" else "Fin del trámite")
        filas.append([str(i), etq, ACTORES[clase][0].split(" (")[0], "<br/>".join(esc(s) for s in sig)])
    filas = [[P(c, chicob if r == 0 else chico) for c in f] for r, f in enumerate(filas)]
    t = Table(filas, colWidths=[0.9 * cm, 5 * cm, 4.5 * cm, 7.1 * cm], repeatRows=1)
    t.setStyle(ESTILO_TABLA)

    h = [P(f"Propuesta TO-BE – {TRAMITE}", h1),
         P(f"<b>Fecha:</b> {FECHA} &nbsp;·&nbsp; Acompaña al archivo «{TRAMITE}.gpm»"),
         P("Descripción", h2), P(esc(" ".join(resumen.split()))),
         P("Actores", h2)]
    h += [Paragraph(f"<font color='{b}'>■</font> {n}", vin) for n, _, b in ACTORES.values()]
    h += [PageBreak(), P("Diagrama del flujo", h2), img,
          PageBreak(), P("Tareas y conexiones", h2),
          P("Cada decisión se toma con el campo de la tarea anterior (ver el Diccionario de Datos). "
            "Cuando la DGN no valida el fundamento legal, el documento regresa a quien lo emitió."), t]

    def pie(c, d):
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(2 * cm, 1.2 * cm, f"{TRAMITE} · Propuesta TO-BE")
        c.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm, f"Página {d.page}")

    SimpleDocTemplate(str(salida), pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                      bottomMargin=2 * cm, title=f"Propuesta TO-BE – {TRAMITE}",
                      author="Dirección de Gestión Tecnológica").build(h, onFirstPage=pie, onLaterPages=pie)


if __name__ == "__main__":
    insumos, salida = Path(sys.argv[1]), Path(sys.argv[2])
    pantallas = leer_diccionario(insumos / "5.-Diccionario de Datos.md")
    preguntas = {}
    for *_, filas in pantallas:
        for f in filas:
            _, var, _ = limpiar_descripcion(f["Descripción"])
            preguntas[var] = f["Nombre del Campo"]
    resumen, nodos, aristas = leer_tobe(insumos / "3.-Propuesta TO-BE.md", preguntas)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_tobe(resumen, nodos, aristas, salida / f"Propuesta TO-BE – {TRAMITE}.pdf", tmp)
    pdf_diccionario(pantallas, salida / f"Diccionario de Datos – {TRAMITE}.pdf")
    print("listo")
