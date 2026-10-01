"""La comparativa como pagina suelta: se baja, se abre y se imprime a PDF.

Autocontenida a proposito: sin scripts, sin fuentes remotas y sin hojas de
estilo de fuera, porque el archivo viaja por correo y se abre sin red. Todo
dato del expediente entra por `_e()`: los catalogos reales traen `<br>` y un
nombre de requisito es texto que escribio una persona.
"""
from html import escape

from gpmc.comparativa.armar import Comparativa, texto_cambio

# `--viz-2` y `--viz-4` del tema claro (`frontend/src/index.css`): el documento
# se imprime sobre blanco, asi que no hay tema oscuro que atender. No son los
# extremos de la rampa: el validador de la guia `dataviz` rechazo `--viz-1` y
# `--viz-5` por luminosidad y croma (2026-09-28). El contraste del claro queda
# bajo 3:1, y por eso cada barra lleva su valor escrito.
COLOR_ANTES = "#CF7A95"
COLOR_DESPUES = "#A22D4E"

_ORIGEN = {"contado": "contado", "leido": "leído", "revisado": "revisado",
           "declarado": "declarado", "propuesto": "propuesto por el agente",
           "sin_dato": "sin dato"}
# Como responde el equipo en la tabla de eliminacion, dicho en una palabra.
_CLASE_ELEMENTO = {"elimina": "Se elimina", "cambia": "Cambia", "conserva": "Se conserva",
                   "sin_decision": "Sin decisión", "otro": "Otra respuesta"}
_ORDEN_ELEMENTOS = ("elimina", "cambia", "conserva", "sin_decision", "otro")
_REQUIERE = {"servicio_publico": "Se puede hacer hoy con un servicio público en línea",
             "convenio": "Requiere un convenio o un sistema de la dependencia"}
_FUENTE = {"as_is": "AS-IS", "to_be": "TO-BE"}
_DESTINO = {"conservado": "Se conserva", "eliminado": "Se elimina",
            "sin_destino": "Sin destino", "nuevo": "Nuevo en el TO-BE"}
_VEREDICTO = {"reduce": "Reduce", "mixto": "Mixto",
              "no_reduce": "No reduce", "sin_medida": "No se puede medir"}

_CSS = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#1f1f1f;
margin:2rem auto;max-width:60rem;padding:0 1.25rem;line-height:1.45}
h1{font-size:1.5rem;margin:0 0 .25rem}h2{font-size:1.05rem;margin:2rem 0 .75rem;
border-bottom:1px solid #ddd;padding-bottom:.25rem}
.sub{color:#666;font-size:.875rem;margin:0}
.veredicto{border-left:4px solid #A22D4E;background:#f7f0f2;padding:.75rem 1rem;margin:1rem 0}
.veredicto strong{display:block;font-size:1.1rem}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:.75rem}
.tarjeta{border:1px solid #ddd;border-radius:.5rem;padding:.75rem;break-inside:avoid}
.tarjeta h3{font-size:.875rem;margin:0 0 .5rem}
.par{display:flex;gap:1rem;font-size:.8125rem}.par div{flex:1}
.cifra{font-size:1.25rem;font-weight:700;display:block}
.origen{color:#666;font-size:.6875rem;text-transform:uppercase;letter-spacing:.05em}
.cambio{font-weight:700;margin-top:.5rem;font-size:.875rem}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}
ol,ul{padding-left:1.25rem;margin:0}li{margin:.25rem 0;font-size:.875rem}
.nota{color:#666;font-size:.8125rem}
.resumen{padding-left:1.25rem;margin:.5rem 0 1rem}.resumen li{font-size:.9375rem}
.evidencia{margin:.5rem 0 0;padding-left:1rem;border-left:2px solid #ddd}
.evidencia li{list-style:none;font-size:.75rem;color:#444;margin:.2rem 0}
.motivo{font-size:.8125rem;margin:.5rem 0 0}
.tarjeta p{margin:.35rem 0;font-size:.8125rem}
@media print{body{margin:0}h2{break-after:avoid}}
"""


def _e(texto) -> str:
    return escape(str(texto if texto is not None else ""), quote=True)


def grafica_svg(metricas: list) -> str:
    comparables = [m for m in metricas if m.porcentaje is not None]
    if not comparables:
        return ""
    ancho, x0, util, alto_fila = 720, 230, 330, 58
    alto = alto_fila * len(comparables) + 34
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 {ancho} {alto}" '
        f'width="100%" font-family="system-ui,sans-serif" font-size="12">',
        "<title>Antes y después por métrica, con el porcentaje de cambio</title>",
        f'<circle cx="{x0 + 6}" cy="10" r="6" fill="{COLOR_ANTES}"/>'
        f'<text x="{x0 + 18}" y="14">Antes</text>'
        f'<circle cx="{x0 + 86}" cy="10" r="6" fill="{COLOR_DESPUES}"/>'
        f'<text x="{x0 + 98}" y="14">Después</text>',
    ]
    for i, m in enumerate(comparables):
        y = 34 + i * alto_fila
        tope = max(m.antes.numero, m.despues.numero) or 1
        # Minimo 2 px: una barra de valor 0 tiene que seguir viendose como barra.
        a = max(2, round(util * m.antes.numero / tope))
        d = max(2, round(util * m.despues.numero / tope))
        partes.append(
            f'<text x="0" y="{y + 22}" font-weight="600">{_e(m.nombre)}</text>'
            f'<rect x="{x0}" y="{y}" width="{a}" height="16" rx="3" fill="{COLOR_ANTES}"/>'
            f'<text x="{x0 + a + 6}" y="{y + 12}">{_e(m.antes.texto)}</text>'
            f'<rect x="{x0}" y="{y + 20}" width="{d}" height="16" rx="3" fill="{COLOR_DESPUES}"/>'
            f'<text x="{x0 + d + 6}" y="{y + 32}">{_e(m.despues.texto)}</text>'
            f'<text x="{ancho}" y="{y + 22}" text-anchor="end" font-weight="700">'
            f'{_e(texto_cambio(m.porcentaje))}</text>'
        )
    partes.append("</svg>")
    return "".join(partes)


def _lado(rotulo: str, v) -> str:
    cifra = _e(v.texto) if v.origen != "sin_dato" else "—"
    return (f'<div><span class="origen">{rotulo}</span>'
            f'<span class="cifra">{cifra}</span>'
            f'<span class="origen">{_e(_ORIGEN.get(v.origen, v.origen))}</span></div>')


def _evidencia(rotulo: str, p) -> str:
    """Las frases del expediente en que se apoya una cifra propuesta. Van en el
    documento porque quien lo recibe no tiene la pantalla para abrirlas."""
    if not p:
        return ""
    motivo = f'<p class="motivo">{_e(p["motivo"])}</p>' if p.get("motivo") else ""
    frases = "".join(f"<li><strong>{_e(x['nombre'])}</strong> — «{_e(x['cita'])}»</li>"
                     for x in p["evidencia"])
    return (f'{motivo}<p class="origen">Evidencia de «{rotulo}»</p>'
            f'<ul class="evidencia">{frases}</ul>')


def _tarjeta_metrica(m) -> str:
    cambio = (f'<p class="cambio">{_e(texto_cambio(m.porcentaje))}</p>'
              if m.porcentaje is not None else "")
    return (f'<article class="tarjeta"><h3>{_e(m.nombre)}</h3><div class="par">'
            f'{_lado("Antes", m.antes)}{_lado("Después", m.despues)}</div>{cambio}'
            f'{_evidencia("antes", m.propuesta_antes)}'
            f'{_evidencia("después", m.propuesta_despues)}</article>')


def _elementos(c: Comparativa) -> str:
    if not c.elementos:
        return ""
    tarjetas = []
    for clase in _ORDEN_ELEMENTOS:
        for x in (e for e in c.elementos if e["clase"] == clase):
            fundamento = f"<p>{_e(x['fundamento'])}</p>" if x["fundamento"] else ""
            tarjetas.append(
                f'<article class="tarjeta"><h3>{_e(x["nombre"])}</h3>'
                f'<span class="origen">{_e(_CLASE_ELEMENTO[clase])}</span>'
                f'<p><strong>{_e(x["decision"])}</strong></p>{fundamento}</article>')
    return ("<h2>Qué pasó con cada elemento del trámite</h2>"
            '<p class="nota">Tabla «Análisis de eliminación» del TO-BE, tal como la '
            "escribió el equipo.</p>"
            f'<div class="rejilla">{"".join(tarjetas)}</div>')


def _mejoras(c: Comparativa) -> str:
    vivas = [x for x in c.mejoras if not x["descartada"]]
    if not vivas:
        return ""
    tarjetas = []
    for x in vivas:
        apoyo = []
        if x["etiqueta_campo"]:
            apoyo.append(f"Documento que se sigue pidiendo: {_e(x['etiqueta_campo'])}.")
        if x["cita"]:
            apoyo.append(f"{_FUENTE.get(x['fuente'], 'Expediente')}: «{_e(x['cita'])}»")
        requiere = (f'<p class="origen">{_e(_REQUIERE[x["requiere"]])}</p>'
                    if x["requiere"] in _REQUIERE else "")
        beneficio = f"<p><strong>Qué se gana:</strong> {_e(x['beneficio'])}</p>" \
            if x["beneficio"] else ""
        tarjetas.append(
            f'<article class="tarjeta"><h3>{_e(x["titulo"])}</h3><p>{_e(x["propuesta"])}</p>'
            f'{beneficio}<p class="nota">{" ".join(apoyo)}</p>{requiere}</article>')
    return ("<h2>Qué más se puede simplificar</h2>"
            '<p class="nota">Propuestas del agente sobre el trámite ya rediseñado. Cada una '
            "se apoya en una frase del expediente o en un documento que se sigue pidiendo; "
            "decide el equipo.</p>"
            f'<div class="rejilla">{"".join(tarjetas)}</div>')


def _tarjeta_requisito(r) -> str:
    fundamento = f'<p class="nota">{_e(r.fundamento)}</p>' if r.fundamento else ""
    return (f'<article class="tarjeta"><h3>{_e(r.nombre)}</h3>'
            f'<span class="origen">{_e(_DESTINO[r.destino])}</span>{fundamento}</article>')


def _lista(titulo: str, puntos: list, ordenada: bool = False, nota: str = "") -> str:
    if not puntos:
        return ""
    etiqueta = "ol" if ordenada else "ul"
    items = "".join(f"<li>{_e(p)}</li>" for p in puntos)
    aviso = f'<p class="nota">{_e(nota)}</p>' if nota else ""
    return f"<h2>{_e(titulo)}</h2>{aviso}<{etiqueta}>{items}</{etiqueta}>"


def a_html(c: Comparativa) -> str:
    cabeza = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
              f"<title>Antes y después — {_e(c.tramite)}</title>"
              f"<style>{_CSS}</style></head><body>")
    if not c.disponible:
        return (f"{cabeza}<h1>Antes y después</h1>"
                f'<p class="veredicto">{_e(c.motivo)}</p></body></html>')
    tareas = [f"{t['nombre']} ({t['actor']})" if t["actor"] else t["nombre"]
              for t in c.tareas_despues]
    cuerpo = [
        f"<h1>Antes y después — {_e(c.tramite)}</h1>",
        '<p class="sub">Comparativa de la reingeniería. Uso interno de Simplificación '
        "Administrativa. Cada cifra dice de dónde salió.</p>",
        f'<div class="veredicto"><strong>{_e(_VEREDICTO[c.veredicto])}</strong>'
        f"{_e(c.frase)}</div>",
        ('<ul class="resumen">' + "".join(f"<li>{_e(x['texto'])}</li>" for x in c.resumen)
         + "</ul>") if c.resumen else "",
        grafica_svg(c.metricas),
        '<h2>Métricas</h2><div class="rejilla">',
        "".join(_tarjeta_metrica(m) for m in c.metricas),
        "</div>",
        f'<p class="nota">Campos que se llenan solos por consulta en línea: '
        f"{c.autollenados}.</p>",
    ]
    cuerpo.append(_elementos(c))
    if c.documentos:
        cuerpo.append("<h2>Documentos del trámite</h2>"
                      f"<p>{_e(c.documentos['titular'])}</p>")
        if c.documentos.get("simplificacion"):
            cuerpo += ["<ul>",
                       "".join(f"<li><strong>{_e(x['frase'])}:</strong> "
                               f"{_e(', '.join(x['documentos']))}</li>"
                               for x in c.documentos["simplificacion"]),
                       "</ul>"]
    if c.requisitos:
        cuerpo += ['<h2>Requisitos, uno por uno</h2><div class="rejilla">',
                   "".join(_tarjeta_requisito(r) for r in c.requisitos), "</div>"]
    cuerpo.append('<div class="dos"><div>')
    cuerpo.append(_lista("Pasos de antes", c.pasos_antes, ordenada=True)
                  or "<h2>Pasos de antes</h2><p class=\"nota\">El AS-IS no trae pasos legibles.</p>")
    cuerpo.append("</div><div>")
    cuerpo.append(_lista("Tareas de después", tareas, ordenada=True))
    cuerpo.append("</div></div>")
    cuerpo.append(_lista("Fricciones del proceso actual", c.fricciones))
    cuerpo.append(_lista("Cambios concretos frente al AS-IS", c.cambios))
    cuerpo.append(_lista("Lo que se eliminó", c.eliminaciones))
    cuerpo.append(_lista("Impacto estimado", c.impacto,
                         nota="Estimación cualitativa del equipo, no un dato medido."))
    cuerpo.append(_mejoras(c))
    cuerpo.append(_lista("Por confirmar", [h.mensaje for h in c.huecos]))
    return cabeza + "".join(cuerpo) + "</body></html>"
