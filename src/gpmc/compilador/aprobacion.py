"""Generador del HTML de aprobacion para la firma de la dependencia.

A diferencia del simulador, este documento no tiene JavaScript ni es interactivo:
su destino principal es imprimirse a PDF (Ctrl+P) para recabar la firma fisica.
"""

import html as _html
import json

from gpmc.nucleo.manifiesto import Manifiesto


_ESTILO = """
:root {
  --guinda: #5e132c; --guinda2: #66132a; --tinta: #1a1a1a; --gris: #6b7280;
  --linea: #e2d5d8; --fondo: #fff9f9; --suave: #f0f0f0;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--fondo); color: var(--tinta);
  font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, sans-serif;
}
.marca-agua {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg);
  font-size: 8rem; color: rgba(0, 0, 0, 0.04); white-space: nowrap;
  pointer-events: none; z-index: -1; font-weight: bold; letter-spacing: 0.1em;
}
.barra {
  background: var(--guinda); color: #fff; padding: 1rem 1.5rem;
  display: flex; justify-content: space-between; align-items: center;
}
.barra strong { font-size: 1.1rem; }
.barra em { font-style: normal; font-size: 0.85rem; opacity: 0.9; }
.marco { max-width: 52rem; margin: 0 auto; padding: 2rem 1.5rem; }
.ficha {
  background: #fff; border: 1px solid var(--linea); border-radius: 0.5rem;
  padding: 1.5rem; margin-bottom: 2rem;
}
.ficha h1 { margin: 0 0 0.5rem; font-size: 1.5rem; color: var(--guinda); }
.ficha p { margin: 0; color: var(--gris); font-size: 0.95rem; }
h2 { font-size: 1.1rem; border-bottom: 2px solid var(--guinda); padding-bottom: 0.25rem; margin: 2rem 0 1rem; color: var(--guinda); }
.pantalla { background: #fff; border: 1px solid var(--linea); border-radius: 0.5rem; margin-bottom: 1.5rem; overflow: hidden; }
.pantalla-header { background: var(--suave); padding: 0.75rem 1rem; border-bottom: 1px solid var(--linea); display: flex; justify-content: space-between; align-items: baseline; }
.pantalla-header strong { font-size: 1rem; }
.pantalla-header span { font-size: 0.8rem; color: var(--gris); text-transform: uppercase; letter-spacing: 0.05em; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { text-align: left; padding: 0.5rem 1rem; border-bottom: 1px solid var(--linea); }
th { background: #fafafa; color: var(--gris); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
tr:last-child td { border-bottom: none; }
.req { color: #b91c1c; font-weight: bold; }
.cat { font-size: 0.8rem; color: var(--gris); margin-top: 0.25rem; }
.flujo {
  display: flex; flex-direction: column; gap: 1rem; margin-bottom: 2rem;
  background: #fff; padding: 1.5rem; border: 1px solid var(--linea); border-radius: 0.5rem;
}
.tarea { padding: 0.75rem 1rem; border: 1px solid var(--guinda); border-radius: 0.35rem; background: #fdf8f9; }
.tarea-nombre { font-weight: 600; color: var(--guinda); }
.tarea-actor { font-size: 0.8rem; color: var(--gris); margin-top: 0.25rem; }
.conexion { padding-left: 2rem; border-left: 2px solid var(--linea); margin-left: 1rem; color: var(--gris); font-size: 0.85rem; }
.firmas { margin-top: 4rem; display: flex; justify-content: space-around; gap: 2rem; page-break-inside: avoid; }
.firma { text-align: center; flex: 1; }
.firma-linea { border-top: 1px solid var(--tinta); margin-bottom: 0.5rem; padding-top: 0.5rem; }
.firma-nombre { font-weight: 600; }
.firma-cargo { font-size: 0.85rem; color: var(--gris); }

.pantalla-body { padding: 1.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.m-field { display: flex; flex-direction: column; }
.m-label { font-size: 0.85rem; font-weight: 600; color: var(--tinta); margin-bottom: 0.5rem; }
.m-readonly { font-weight: normal; color: var(--gris); font-size: 0.75rem; margin-left: 0.5rem; }
.m-input { padding: 0.5rem 0.75rem; border: 1px solid var(--linea); border-radius: 0.25rem; background: #f9fafb; font-family: monospace; font-size: 0.85rem; color: var(--gris); }
.m-textarea { resize: none; height: 3rem; }
.m-file { padding: 0.75rem; border: 1px dashed var(--gris); border-radius: 0.25rem; background: #f9fafb; color: var(--gris); font-size: 0.85rem; text-align: center; }
.m-radio-group { display: flex; flex-direction: column; gap: 0.35rem; }
.m-radio { font-size: 0.85rem; color: var(--tinta); display: flex; align-items: center; gap: 0.5rem; }
.m-ayuda { font-size: 0.75rem; color: var(--gris); margin-top: 0.35rem; }

@media print {
  body { background: #fff; font-size: 12px; }
  .barra { display: none; }
  .marco { max-width: 100%; padding: 0; }
  .ficha { border: none; padding: 0; margin-bottom: 1.5rem; }
  .pantalla, .flujo { border: 1px solid #ccc; page-break-inside: avoid; }
  .marca-agua { color: rgba(0, 0, 0, 0.03); }
}
"""


def _flujo(m: Manifiesto, e) -> str:
    tareas_d = {t.id: t for t in m.flujo.tareas}
    actores_d = {a.id: a.nombre for a in m.actores}
    conexiones_d = {}
    for c in m.flujo.conexiones:
        conexiones_d.setdefault(c.de, []).append(c)

    html = '<div class="flujo">'
    for t in m.flujo.tareas:
        actor = actores_d.get(t.actor, "(sin actor)") if t.actor else "(sistema)"
        html += f'<div class="tarea"><div class="tarea-nombre">{e(t.nombre)}</div><div class="tarea-actor">{e(actor)}</div></div>'
        salidas = conexiones_d.get(t.id, [])
        for c in salidas:
            cond = f" (Si {e(c.cuando.campo)} = {e(c.cuando.igual)})" if c.cuando else ""
            destino = tareas_d.get(c.a)
            nom_destino = e(destino.nombre) if destino else e(c.a)
            html += f'<div class="conexion">↳ Hacia: <strong>{nom_destino}</strong>{cond}</div>'
    html += '</div>'
    return html


def generar_aprobacion(m: Manifiesto) -> str:
    e = _html.escape
    actores = {x.id: x.nombre for x in m.actores}

    pantallas_html = ""
    for p in m.pantallas:
        actor = e(actores.get(p.actor, p.actor))
        campos_html = ""
        for c in p.campos:
            req = '<span class="req" title="Obligatorio">*</span>' if c.obligatorio else ""
            
            input_html = ""
            if c.tipo in ['text', 'textbox']:
                input_html = f'<input type="text" class="m-input" value="[ {e(c.nombre)} ]" disabled>'
            elif c.tipo == 'textarea':
                input_html = f'<textarea class="m-input m-textarea" disabled>[ {e(c.nombre)} ]</textarea>'
            elif c.tipo == 'select':
                opts = '<option value="">— Seleccione una opción —</option>'
                if c.catalogo:
                    for op in c.catalogo[:3]:
                        opts += f'<option>{e(op.etiqueta or op.valor)}</option>'
                    if len(c.catalogo) > 3:
                        opts += f'<option disabled>... y {len(c.catalogo)-3} opciones más</option>'
                input_html = f'<select class="m-input" disabled>{opts}</select>'
            elif c.tipo in ['file', 'archivo']:
                input_html = '<div class="m-file">📎 Adjuntar archivo (PDF, imagen)</div>'
            elif c.tipo == 'date':
                input_html = '<input type="date" class="m-input" disabled>'
            elif c.tipo == 'radio':
                radios = ""
                if c.catalogo:
                    for op in c.catalogo:
                        lbl = e(op.etiqueta or op.valor)
                        radios += f'<label class="m-radio"><input type="radio" disabled> {lbl}</label>'
                else:
                    radios = '<label class="m-radio"><input type="radio" disabled> Opción</label>'
                input_html = f'<div class="m-radio-group">{radios}</div>'
            elif c.tipo == 'checkbox':
                checks = ""
                if c.catalogo:
                    for op in c.catalogo:
                        lbl = e(op.etiqueta or op.valor)
                        checks += f'<label class="m-radio"><input type="checkbox" disabled> {lbl}</label>'
                else:
                    checks = '<label class="m-radio"><input type="checkbox" disabled> Opción</label>'
                input_html = f'<div class="m-radio-group">{checks}</div>'
            else:
                input_html = f'<div class="m-file">🧩 Componente: <strong>{e(c.tipo)}</strong></div>'
                
            ayuda_html = f'<div class="m-ayuda">ℹ️ {e(c.ayuda)}</div>' if c.ayuda else ""
            solo_lectura = '<span class="m-readonly">(Sólo lectura)</span>' if c.solo_lectura else ""

            campos_html += f"""
            <div class="m-field">
                <label class="m-label">{e(c.etiqueta)} {req} {solo_lectura}</label>
                {input_html}
                {ayuda_html}
            </div>
            """

        pantallas_html += f"""
        <div class="pantalla">
            <div class="pantalla-header">
                <strong>{e(p.nombre)}</strong>
                <span>{actor}</span>
            </div>
            <div class="pantalla-body">
                {campos_html}
            </div>
        </div>
        """

    acciones_html = ""
    if m.acciones:
        acciones_html = "<h2>Acciones Automáticas</h2><ul>"
        for a in m.acciones:
            acciones_html += f"<li><strong>{e(a.tipo).upper()}</strong>: {e(a.nombre)}</li>"
        acciones_html += "</ul>"

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Diseño de Trámite — {e(m.tramite.nombre)}</title>
  <style>{_ESTILO}</style>
</head>
<body>
  <div class="marca-agua">BORRADOR - SIN FIRMAR</div>
  <div class="barra">
    <strong>Documento de Aprobación de Diseño</strong>
    <em>Generado por Compilador GPM</em>
  </div>
  
  <div class="marco">
    <div class="ficha">
      <h1>{e(m.tramite.nombre)}</h1>
      <p><strong>Dependencia:</strong> {e(m.tramite.dependencia)}</p>
      {f'<p><strong>Homoclave:</strong> {e(m.tramite.homoclave)}</p>' if m.tramite.homoclave else ''}
      <p style="margin-top:1rem;font-size:0.85rem;color:var(--gris)">
        Este documento representa el diseño del trámite tal como se configurará en la plataforma. 
        Revisar y firmar este documento aprueba la estructura de datos, el flujo y las pantallas.
      </p>
    </div>

    <h2>Flujo del Trámite</h2>
    {_flujo(m, e)}

    <h2>Pantallas y Campos</h2>
    {pantallas_html}

    {acciones_html}

    <div class="firmas">
      <div class="firma">
        <div class="firma-linea">
          <div class="firma-nombre">Responsable del Trámite</div>
          <div class="firma-cargo">{e(m.tramite.dependencia)}</div>
        </div>
      </div>
      <div class="firma">
        <div class="firma-linea">
          <div class="firma-nombre">Dirección de Gestión Tecnológica</div>
          <div class="firma-cargo">Secretaría de Desarrollo Económico</div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""
