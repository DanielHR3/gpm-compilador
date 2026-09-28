"""«Documentos del tramite» como pagina suelta: se baja, se abre y se imprime.

Autocontenida, sin scripts ni recursos de fuera, como `documento.py`. Todo
dato del expediente entra por `_e()`.
"""
from html import escape

from gpmc.comparativa.documentos import DESTINOS, SIN_DESTINO

NOMBRE = {"elimina": "Se elimina", "consulta": "Se sustituye por consulta en línea",
          "sistema": "Lo genera el sistema", "conserva": "Se conserva",
          SIN_DESTINO: "Sin destino"}
# Orden de lectura: primero lo que el ciudadano dejo de traer.
ORDEN = ("elimina", "consulta", "sistema", "conserva", SIN_DESTINO)
# Paleta categorica validada con la guia `dataviz` (tema claro): ver el Step 3.
COLOR = {"elimina": "#2a78d6", "consulta": "#eb6834", "sistema": "#1baf7a",
         "conserva": "#eda100", SIN_DESTINO: "#8A8A8A"}
_ESTADO = {"propuesto": "Propuesto, sin revisar", "aceptado": "Aceptado",
           "corregido": "Corregido por una persona"}

_CSS = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#1f1f1f;
margin:2rem auto;max-width:60rem;padding:0 1.25rem;line-height:1.45}
h1{font-size:1.5rem;margin:0 0 .25rem}h2{font-size:1.05rem;margin:2rem 0 .75rem;
border-bottom:1px solid #ddd;padding-bottom:.25rem}
.sub{color:#666;font-size:.875rem;margin:0}
.titular{font-size:1.35rem;font-weight:700;margin:1.25rem 0}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(17rem,1fr));gap:.75rem}
.tarjeta{border:1px solid #ddd;border-left-width:5px;border-radius:.5rem;padding:.75rem;
break-inside:avoid}
.tarjeta h3{font-size:.9375rem;margin:0 0 .25rem}
.rotulo{color:#666;font-size:.6875rem;text-transform:uppercase;letter-spacing:.05em}
blockquote{margin:.5rem 0;padding-left:.6rem;border-left:2px solid #ccc;font-size:.8125rem}
.nota{color:#666;font-size:.8125rem;margin:.35rem 0 0}
ul{padding-left:1.25rem;margin:0}li{font-size:.875rem;margin:.25rem 0}
@media print{body{margin:0}h2{break-after:avoid}}
"""


def _e(texto) -> str:
    return escape(str(texto if texto is not None else ""), quote=True)


def barra_svg(por_destino: dict) -> str:
    total = sum(por_destino.get(k, 0) for k in ORDEN)
    if total == 0:
        return ""
    ancho, x, tramos, leyenda = 720, 0.0, [], []
    for k in ORDEN:
        n = por_destino.get(k, 0)
        if n == 0:
            continue
        w = ancho * n / total
        # 2 px de superficie entre tramos: el borde no depende del color.
        tramos.append(f'<rect x="{x + 1:.1f}" y="0" width="{max(w - 2, 1):.1f}" height="28" '
                      f'rx="4" fill="{COLOR[k]}"/>')
        leyenda.append(f'<circle cx="{8 + len(leyenda) * 180}" cy="52" r="6" fill="{COLOR[k]}"/>'
                       f'<text x="{20 + len(leyenda) * 180}" y="56">{_e(NOMBRE[k])} · {n}</text>')
        x += w
    alto = 68
    return (f'<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 {ancho} {alto}" '
            f'width="100%" font-family="system-ui,sans-serif" font-size="11">'
            f"<title>Documentos del trámite por destino</title>"
            f"{''.join(tramos)}{''.join(leyenda)}</svg>")


def _tarjeta(d) -> str:
    partes = [f'<article class="tarjeta" style="border-left-color:{COLOR.get(d.destino, COLOR[SIN_DESTINO])}">',
              f"<h3>{_e(d.nombre)}</h3>",
              f'<span class="rotulo">{_e(NOMBRE.get(d.destino, NOMBRE[SIN_DESTINO]))} · '
              f"{_e(_ESTADO.get(d.estado, d.estado))}</span>",
              (f'<p class="nota">En el AS-IS:</p><blockquote>{_e(d.cita_as_is)}</blockquote>'
               if d.cita_as_is else
               '<p class="nota">El AS-IS no lo nombra; lo dice el TO-BE.</p>')]
    if d.cita_to_be:
        partes.append(f'<p class="nota">En el TO-BE:</p><blockquote>{_e(d.cita_to_be)}</blockquote>')
    if d.campo:
        partes.append(f'<p class="nota">Campo del trámite: <code>@@{_e(d.campo)}</code></p>')
    if d.destino == "elimina" and not d.cita_to_be and d.estado != "propuesto":
        partes.append('<p class="nota"><strong>Eliminado sin fundamento:</strong> el TO-BE no dice '
                      "por qué dejó de pedirse.</p>")
    if d.motivo:
        quien = "Redacción de la IA" if d.motivo_de == "ia" else "Motivo que escribió el analista"
        partes.append(f'<p class="nota">{quien}: {_e(d.motivo)}</p>')
    partes.append("</article>")
    return "".join(partes)


def a_html(tramite: str, resumen: dict, docs: list) -> str:
    orden = {k: i for i, k in enumerate(ORDEN)}
    docs = sorted(docs, key=lambda d: orden.get(d.destino, len(ORDEN)))
    cuerpo = [
        '<!doctype html><html lang="es"><head><meta charset="utf-8">',
        f"<title>Documentos del trámite — {_e(tramite)}</title><style>{_CSS}</style></head><body>",
        f"<h1>Documentos del trámite — {_e(tramite)}</h1>",
        '<p class="sub">Qué documentos pedía el trámite y qué pasó con cada uno. Uso interno de '
        "Simplificación Administrativa.</p>",
        f'<p class="titular">{_e(resumen["titular"])}</p>',
        barra_svg(resumen["por_destino"]),
    ]
    if resumen.get("simplificacion"):
        cuerpo += ["<h2>Cómo se simplificó el trámite</h2><ul>",
                   "".join(f"<li><strong>{_e(x['frase'])}:</strong> "
                           f"{_e(', '.join(x['documentos']))}</li>"
                           for x in resumen["simplificacion"]),
                   "</ul>"]
    if docs:
        cuerpo += ['<h2>Documento por documento</h2><div class="rejilla">',
                   "".join(_tarjeta(d) for d in docs), "</div>"]
    if resumen["agregados"]:
        cuerpo += ["<h2>Documentos que el TO-BE agrega</h2>",
                   '<p class="nota">El trámite rediseñado los pide y el AS-IS no los nombraba.</p><ul>',
                   "".join(f"<li>{_e(a)}</li>" for a in resumen["agregados"]), "</ul>"]
    return "".join(cuerpo) + "</body></html>"


# Un destino nuevo en `documentos.py` tiene que romper aqui, no pasar en silencio.
assert set(DESTINOS) <= set(ORDEN)
