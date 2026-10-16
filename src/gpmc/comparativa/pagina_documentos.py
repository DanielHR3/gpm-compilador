"""«Documentos del tramite» como pagina suelta: se baja, se abre y se imprime.

Autocontenida, sin scripts ni recursos de fuera, como `documento.py`. Todo
dato del expediente entra por `_e()`.
"""
from gpmc.comparativa.documentos import DESTINOS, SIN_DESTINO
from gpmc.comparativa.estilo import e, pagina

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

_e = e


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
        # En la barra, lo que no tiene decision esta «por revisar»: en una
        # tarjeta, «sin destino» es que nadie le ha propuesto uno.
        rotulo = "Por revisar" if k == SIN_DESTINO else NOMBRE[k]
        leyenda.append(f'<circle cx="{8 + len(leyenda) * 180}" cy="52" r="6" fill="{COLOR[k]}"/>'
                       f'<text x="{20 + len(leyenda) * 180}" y="56">{_e(rotulo)} · {n}</text>')
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
        f"<h1>Documentos del trámite — {_e(tramite)}</h1>",
        '<p class="sub">Qué documentos pedía el trámite y qué pasó con cada uno.</p>',
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
    return pagina("Documentos del trámite", tramite, "".join(cuerpo),
                  "Uso interno de Simplificación Administrativa.")


# Un destino nuevo en `documentos.py` tiene que romper aqui, no pasar en silencio.
assert set(DESTINOS) <= set(ORDEN)
