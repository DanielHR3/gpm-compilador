"""La comparativa como pagina suelta: se baja, se abre y se imprime a PDF.

Autocontenida a proposito: sin scripts, sin fuentes remotas y sin hojas de
estilo de fuera, porque el archivo viaja por correo y se abre sin red. Todo
dato del expediente entra por `_e()`: los catalogos reales traen `<br>` y un
nombre de requisito es texto que escribio una persona.
"""
from gpmc.comparativa.armar import Comparativa, texto_cambio
from gpmc.comparativa.estilo import e, pagina

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
             "convenio": "A futuro: requiere conectar un sistema de la dependencia o un convenio"}
# Las tres preguntas del metodo de Simplificacion (mismas palabras que la SPA).
_ACCION = {"eliminar": "Se puede eliminar", "automatizar": "Lo puede hacer el sistema",
           "a_distancia": "Se puede hacer a distancia"}
_FUENTE = {"as_is": "AS-IS", "to_be": "TO-BE"}
_DESTINO = {"conservado": "Se conserva", "eliminado": "Se elimina",
            "sin_destino": "Sin destino", "nuevo": "Nuevo en el TO-BE"}
_VEREDICTO = {"reduce": "Reduce", "mixto": "Mixto",
              "no_reduce": "No reduce", "sin_medida": "No se puede medir"}

_e = e


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
        accion = (f'<span class="origen">{_e(_ACCION[x["accion"]])}</span>'
                  if x.get("accion") in _ACCION else "")
        tarjetas.append(
            f'<article class="tarjeta"><h3>{_e(x["titulo"])}</h3>{accion}<p>{_e(x["propuesta"])}</p>'
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


_USO = "Comparativa de la reingeniería. Uso interno de Simplificación Administrativa."


def a_html(c: Comparativa) -> str:
    if not c.disponible:
        return pagina("Antes y después", c.tramite, "<h1>Antes y después</h1>"
                      f'<p class="veredicto">{_e(c.motivo)}</p>', _USO)
    tareas = [f"{t['nombre']} ({t['actor']})" if t["actor"] else t["nombre"]
              for t in c.tareas_despues]
    cuerpo = [
        f"<h1>Antes y después — {_e(c.tramite)}</h1>",
        '<p class="sub">Comparativa de la reingeniería. Cada cifra dice de dónde salió.</p>',
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
    return pagina("Antes y después", c.tramite, "".join(cuerpo), _USO)
