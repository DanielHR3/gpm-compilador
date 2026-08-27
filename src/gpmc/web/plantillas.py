"""Plantillas del asistente. Sin build de frontend ni dependencias externas."""

import html as _h

from gpmc.nucleo.huecos import NIVELES

# Paleta muestreada de capturas reales de la plataforma de modelado.
ESTILO = """
:root{--guinda:#5e132c;--guinda2:#66132a;--tinta:#18181b;--gris:#71717a;
      --linea:#e2d5d8;--fondo:#fff9f9;--suave:#f0f0f0;--verde:#11453d;
      --alerta:#7f1d1d;--alerta-suave:#fef2f2;--ok:#166534}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
     font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.barra{background:var(--guinda);color:#fff;padding:.9rem 1.5rem;display:flex;
       justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.barra strong{font-size:1.05rem}
.barra em{font-style:normal;font-size:.78rem;opacity:.85}
.barra2{background:var(--guinda2);color:#fff;padding:.5rem 1.5rem;font-size:.8rem;opacity:.95}
.marco{max-width:56rem;margin:0 auto;padding:2.25rem 1.25rem}
h1{font-size:1.5rem;margin:0 0 .35rem}
.sub{color:var(--gris);margin:0 0 2rem;font-size:.95rem}
.pasos{display:flex;gap:.5rem;margin-bottom:2rem;flex-wrap:wrap;font-size:.8rem}
.pasos span{padding:.3rem .7rem;border:1px solid var(--linea);border-radius:2rem;color:var(--gris)}
.pasos span.act{background:var(--guinda);color:#fff;border-color:var(--guinda)}
.tarjeta{background:#fff;border:1px solid var(--linea);border-radius:.6rem;padding:1.5rem;margin-bottom:1.25rem}
.tarjeta h2{font-size:1rem;margin:0 0 1rem}
label{display:block;margin-bottom:1.1rem}
label b{display:block;font-weight:600;font-size:.9rem;margin-bottom:.15rem}
label em{display:block;font-style:normal;color:var(--gris);font-size:.82rem;margin-bottom:.4rem}
input[type=file]{width:100%;padding:.5rem;border:1px dashed var(--linea);border-radius:.35rem;
                 background:var(--suave);color:var(--tinta);font:inherit}
button{padding:.6rem 1.2rem;border-radius:.35rem;border:1px solid var(--guinda);
       background:var(--guinda);color:#fff;font:inherit;cursor:pointer}
a.btn{display:inline-block;padding:.55rem 1.1rem;border:1px solid var(--guinda);border-radius:.35rem;
      color:var(--guinda);text-decoration:none;font-size:.9rem;margin:0 .5rem .5rem 0}
a.btn.p{background:var(--guinda);color:#fff}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:.5rem}
th,td{text-align:left;padding:.4rem .6rem;border-bottom:1px solid var(--linea);vertical-align:top}
th{background:var(--suave);color:var(--gris);font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.huecos{background:var(--alerta-suave);border:1px solid var(--alerta);border-radius:.6rem;
        padding:1.25rem 1.5rem;margin-bottom:1.25rem}
.huecos h2{color:var(--alerta);font-size:.95rem;margin:0 0 .75rem}
.huecos li{font-size:.85rem;margin-bottom:.4rem}
details.huecos{padding:.85rem 1.25rem}
details.huecos summary{cursor:pointer;font-size:.95rem}
details.huecos ul{margin:.6rem 0 .2rem}
.cifras{display:flex;gap:1.5rem;flex-wrap:wrap;margin:.5rem 0 1rem}
.cifra b{display:block;font-size:1.6rem;line-height:1.1}
.cifra span{font-size:.78rem;color:var(--gris)}
.err{background:var(--alerta-suave);border:1px solid var(--alerta);color:var(--alerta);
     padding:1rem 1.25rem;border-radius:.5rem;margin-bottom:1.5rem;font-size:.9rem}
.nota{font-size:.82rem;color:var(--gris);margin-top:1.5rem;padding-top:1rem;
      border-top:1px solid var(--linea)}
"""


def _pasos(activo: int) -> str:
    nombres = ["1 Insumos", "2 Revisión", "3 Simulación", "4 Descarga"]
    return '<div class="pasos">' + "".join(
        f'<span class="{"act" if i + 1 == activo else ""}">{n}</span>'
        for i, n in enumerate(nombres)
    ) + "</div>"


def _envoltura(titulo: str, cuerpo: str, paso: int) -> str:
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_h.escape(titulo)}</title><style>{ESTILO}</style></head><body>
<div class="barra"><strong>Compilador GPM</strong>
<em>Dirección de Gestión Tecnológica</em></div>
<div class="barra2">Herramienta interna · genera el archivo, la importación a la plataforma es manual</div>
<div class="marco">
<p class="sub">De los insumos de reingeniería al archivo <code>.gpm</code></p>
{_pasos(paso)}{cuerpo}</div></body></html>"""


def portada(error: str = "") -> str:
    aviso = f'<div class="err">{_h.escape(error)}</div>' if error else ""
    return _envoltura("Compilador GPM", f"""{aviso}
<form class="tarjeta" method="post" action="/extraer" enctype="multipart/form-data">
  <h2>Insumos del expediente</h2>
  <label><b>Análisis AS-IS</b>
    <em>De ahí salen el nombre, la dependencia, la homoclave y la ficha RUTS.</em>
    <input type="file" name="as_is" accept=".md"></label>
  <label><b>Propuesta TO-BE</b>
    <em>De su diagrama Mermaid sale el flujo: tareas, compuertas y actores.</em>
    <input type="file" name="to_be" accept=".md"></label>
  <label><b>Diccionario de Datos</b> <span style="color:var(--alerta)">— obligatorio</span>
    <em>De ahí salen las pantallas y los campos. Sin él no hay nada que compilar.</em>
    <input type="file" name="diccionario" accept=".md" required></label>
  <button type="submit">Extraer manifiesto →</button>
</form>
<p class="nota">La herramienta <strong>propone</strong>; no adivina. Lo que no puede derivar de los
insumos lo reporta como hueco para que una persona lo resuelva antes de compilar.</p>""", 1)


def revision(m, huecos, problemas, estimacion, sid: str) -> str:
    e = _h.escape
    k = estimacion.metricas

    # Un bloque plegable por nivel, en el orden canónico de NIVELES: de lo que
    # impide compilar a lo que solo conviene revisar. 'por_confirmar' arranca
    # cerrado porque el extractor ya propuso un valor y no bloquea nada.
    _ROTULO = {
        "bloqueante": ("Bloqueante", "resolver antes de compilar", "#c0392b"),
        "falta_dato": ("Faltan datos", "un humano debe escribirlos", "#b9770e"),
        "por_confirmar": ("Por confirmar", "el extractor propuso un valor", "#6b7280"),
    }
    bloque_huecos = ""
    for nivel in NIVELES:
        grupo = [h for h in huecos if h.nivel == nivel]
        if not grupo:
            continue
        titulo, nota, color = _ROTULO[nivel]
        lis = "".join(
            f"<li><code>{e(h.codigo)}</code> "
            f"{(e(h.ubicacion) + ' ') if h.ubicacion else ''}{e(h.mensaje)}"
            f"{(' → <b>' + e(h.propuesta) + '</b>') if h.propuesta else ''}</li>"
            for h in grupo
        )
        abierto = " open" if nivel != "por_confirmar" else ""
        bloque_huecos += (
            f'<details class="huecos"{abierto} style="border-left:4px solid {color}">'
            f"<summary><b>{len(grupo)}</b> {titulo} — {nota}</summary>"
            f"<ul>{lis}</ul></details>"
        )

    bloque_problemas = ""
    if problemas:
        filas = "".join(f"<li>{e(p)}</li>" for p in problemas)
        bloque_problemas = (
            f'<div class="huecos"><h2>{len(problemas)} problema(s) de flujo</h2>'
            f"<ul>{filas}</ul></div>"
        )

    filas_p = "".join(
        f"<tr><td>{e(p.nombre)}</td><td>{e(p.actor)}</td>"
        f"<td>{p.paso_ciudadano or '—'}</td><td>{len(p.campos)}</td></tr>"
        for p in m.pantallas
    )

    motivos = "".join(f"<li>{e(x)}</li>" for x in estimacion.motivos)

    return _envoltura(f"Revisión — {m.tramite.nombre}", f"""
<div class="tarjeta">
  <h2>{e(m.tramite.nombre)}</h2>
  <div class="cifras">
    <div class="cifra"><b>{k.vistas}</b><span>pantallas</span></div>
    <div class="cifra"><b>{k.campos}</b><span>campos</span></div>
    <div class="cifra"><b>{k.tareas}</b><span>tareas</span></div>
    <div class="cifra"><b>{k.bifurcaciones}</b><span>bifurcaciones</span></div>
    <div class="cifra"><b>{len(m.actores)}</b><span>actores</span></div>
  </div>
  <p style="font-size:.9rem;margin:0">Dependencia: {e(m.tramite.dependencia)}
  {(" · Homoclave: " + e(m.tramite.homoclave)) if m.tramite.homoclave else ""}</p>
</div>

{bloque_huecos}{bloque_problemas}

<div class="tarjeta">
  <h2>Pantallas extraídas</h2>
  <table><tr><th>Pantalla</th><th>Actor</th><th>Paso</th><th>Campos</th></tr>{filas_p}</table>
</div>

<div class="tarjeta">
  <h2>Complejidad estimada: {e(estimacion.nivel)} — {e(estimacion.dias)}</h2>
  <ul style="font-size:.85rem;margin:.5rem 0">{motivos}</ul>
  <p style="font-size:.8rem;color:var(--gris);margin:.75rem 0 0">{e(estimacion.advertencia)}</p>
</div>

<div class="tarjeta">
  <h2>Salidas</h2>
  <a class="btn" href="/aprobacion/{e(sid)}" target="_blank">Documento de aprobación ↗</a><br>
  <a class="btn" href="/simulador/{e(sid)}" target="_blank">Recorrer el trámite ↗</a>
  <a class="btn" href="/descargar/{e(sid)}/manifiesto">Manifiesto YAML</a>
  <a class="btn p" href="/descargar/{e(sid)}/gpm">Archivo .gpm</a>
</div>

<p class="nota">El flujo propuesto es <strong>lineal</strong>, una tarea por pantalla. Las
compuertas del diagrama TO-BE se cuentan y se reportan arriba, pero no se reproducen: hay que
ramificarlas a mano en el manifiesto. La importación a la plataforma también es manual.</p>""", 2)
