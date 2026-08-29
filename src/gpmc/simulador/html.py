"""Simulador navegable del tramite, como pagina HTML autocontenida.

El JavaScript NO evalua reglas de GPM: consulta una tabla de transiciones que
Python precalculo con nucleo/reglas. Asi hay una sola interpretacion de las
reglas y el simulador no puede mentir sobre lo que hara la plataforma.

Fidelidad funcional, no visual. No existe ninguna captura de la interfaz real
de GPM en el material disponible, asi que la pagina se presenta como lo que es
—una simulacion— en vez de imitar una apariencia que nadie ha verificado.
"""

import html as _html
import json

from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.simulador.analisis import analizar

# Paleta muestreada de capturas reales de la plataforma de modelado:
# guinda institucional #5e132c/#66132a, fondo #fff9f9, encabezado de tabla
# #f0f0f0, verde de accion #11453d, nodo BPMN #330915.
_ESTILO = """
:root{--guinda:#5e132c;--guinda2:#66132a;--tinta:#1a1a1a;--gris:#6b7280;
      --linea:#e2d5d8;--fondo:#fff9f9;--suave:#f0f0f0;--alerta:#7f1d1d;--verde:#11453d}

.layout { display: flex; min-height: 100vh; background: var(--fondo); }
.sim-sidebar { width: 280px; background: #fff; border-right: 1px solid var(--linea); padding: 1.5rem 1rem; flex-shrink: 0; box-shadow: 2px 0 5px rgba(0,0,0,0.05); height: 100vh; overflow-y: auto; }
.sim-main { flex: 1; display: flex; flex-direction: column; height: 100vh; overflow-y: auto; }
.sim-nav-item { display: block; width: 100%; text-align: left; padding: 0.6rem 0.8rem; background: transparent; border: none; border-radius: 6px; color: var(--gris); font-size: 0.85rem; cursor: pointer; margin-bottom: 0.25rem; transition: all 0.15s; }
.sim-nav-item:hover { background: var(--suave); color: var(--tinta); }
.sim-nav-item.act { background: var(--guinda); color: #fff; font-weight: 600; }
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
     font:16px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.barra{background:var(--guinda);color:#fff;padding:.85rem 1.5rem;display:flex;
       justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.barra strong{font-size:1rem;font-weight:600}
.barra em{font-style:normal;font-size:.78rem;opacity:.85}
.barra2{background:var(--guinda2);color:#fff;padding:.5rem 1.5rem;font-size:.8rem;
        letter-spacing:.03em;opacity:.95}
.marco{max-width:52rem;margin:0 auto;padding:2rem 1rem}
.aviso{background:#fff;border:2px solid var(--alerta);border-left-width:5px;
       padding:.85rem 1.1rem;border-radius:.4rem;font-size:.87rem;margin-bottom:1.75rem}
.aviso strong{color:var(--alerta)}
.tarjeta{background:#fff;border:1px solid var(--linea);border-radius:.6rem;padding:1.5rem;margin-bottom:1rem}
.encabezado{display:flex;justify-content:space-between;align-items:baseline;
            border-bottom:1px solid var(--linea);padding-bottom:.75rem;margin-bottom:1.25rem}
.actor{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--gris)}
.stepper{display:flex;gap:.5rem;margin-bottom:1.25rem;flex-wrap:wrap}
.paso{width:1.75rem;height:1.75rem;border-radius:50%;display:grid;place-items:center;
      font-size:.8rem;border:1px solid var(--linea);color:var(--gris)}
.paso.activo{background:var(--guinda);color:#fff;border-color:var(--guinda)}
.paso.hecho{background:var(--suave)}
label{display:block;margin-bottom:1rem}
label span{display:block;font-size:.85rem;color:var(--gris);margin-bottom:.3rem}
input,select{width:100%;padding:.5rem .65rem;border:1px solid var(--linea);border-radius:.35rem;
             background:var(--fondo);color:var(--tinta);font:inherit}
input[readonly]{background:var(--suave);color:var(--gris)}
.req{color:var(--alerta)}
button{padding:.55rem 1.1rem;border-radius:.35rem;border:1px solid var(--guinda);
       background:var(--guinda);color:#fff;font:inherit;cursor:pointer}
button.sec{background:transparent;color:var(--guinda)}
.pie{display:flex;justify-content:space-between;margin-top:1.5rem}
.problemas{border:1px solid var(--alerta);border-radius:.6rem;padding:1rem 1.25rem;margin-top:2rem}
.problemas h2{font-size:.9rem;margin:0 0 .6rem;color:var(--alerta)}
.problemas li{font-size:.85rem;margin-bottom:.35rem}
.rastro{font-size:.8rem;color:var(--gris);margin-top:1.5rem}
"""

_GUION = """
const ir=(id)=>{ESTADO.tarea=id;ESTADO.rastro.push(id);pintar()};
function valorActual(campo){const el=document.querySelector(`[name="${campo}"]`);return el?el.value:""}
function avanzar(){
  const t=TRANSICIONES[ESTADO.tarea];
  if(!t){return}
  document.querySelectorAll("[name]").forEach(el=>{ESTADO.datos[el.name]=el.value});
  if(t.campo){
    const v=ESTADO.datos[t.campo];
    const destino=t.destinos[v];
    if(destino){return ir(destino)}
    alert("Ninguna rama corresponde al valor «"+(v||"(vacío)")+"». En la plataforma el trámite quedaría detenido aquí.");
    return;
  }
  if(t.siguiente){ir(t.siguiente)}
}
function retroceder(){if(ESTADO.rastro.length>1){ESTADO.rastro.pop();ESTADO.tarea=ESTADO.rastro[ESTADO.rastro.length-1];pintar()}}

function pintarSidebar() {
  const cont = document.getElementById("sim-sidebar-nav");
  if (!cont) return;
  
  let html = '<div style="margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid var(--linea)"><b style="font-size:0.9rem;display:block;margin-bottom:0.5rem">Ir a pantalla:</b>';
  for (const id in TAREAS) {
    const t = TAREAS[id];
    if (t.nombre) {
        const activa = (id === ESTADO.tarea) ? "act" : "";
        html += `<button class="sim-nav-item ${activa}" onclick="saltarA('${id}')">📄 ${t.nombre}</button>`;
    }
  }
  html += '</div>';
  html += `<div style="margin-top:auto"><button class="sim-nav-item" style="color:var(--guinda);border:1px solid var(--guinda)" onclick="window.history.back()">← Salir del Simulador</button></div>`;
  cont.innerHTML = html;
}

function saltarA(id) {
  ESTADO.tarea = id;
  if (!ESTADO.rastro.includes(id)) {
    ESTADO.rastro.push(id);
  }
  pintar();
}

function pintar(){
  const t=TAREAS[ESTADO.tarea];
  const cont=document.getElementById("lienzo");
  if(t.terminal){pintarSidebar();
  cont.innerHTML=`<div class="tarjeta"><div class="encabezado"><strong>${t.nombre}</strong></div>
    <p>El trámite concluyó. Recorrido: ${ESTADO.rastro.map(x=>TAREAS[x].nombre).join(" → ")}</p>
    <div class="pie"><button class="sec" onclick="retroceder()">← Atrás</button>
    <button onclick="reiniciar()">Reiniciar</button></div></div>`;return}
  const pantallas=(t.pantallas||[]).map(pid=>PANTALLAS[pid]);
  const paso=pantallas.find(p=>p&&p.paso_ciudadano);
  let stepper="";
  if(paso){stepper=`<div class="stepper">`+PASOS.map(n=>
    `<div class="paso ${n===paso.paso_ciudadano?"activo":(n<paso.paso_ciudadano?"hecho":"")}">${n}</div>`).join("")+`</div>`}
  const campos=pantallas.flatMap(p=>p?p.campos:[]).map(c=>{
    const req=c.obligatorio?` <span class="req">*</span>`:"";
    let api_badge = "";
    if (c.dependencia_tipo === "api_ajax") {
      api_badge = ` <span style="font-size:0.75rem;color:var(--guinda);background:var(--fondo);padding:0.1rem 0.4rem;border-radius:1rem;border:1px solid var(--guinda)">⚡ API AJAX</span>`;
    } else if (c.dependencia_tipo === "campo") {
      api_badge = ` <span style="font-size:0.75rem;color:var(--tinta);background:var(--suave);padding:0.1rem 0.4rem;border-radius:1rem;">Depende de: ${c.dependencia_campo}</span>`;
    }
    
    if (c.tipo === "select" || (c.catalogo && c.catalogo.length)) {
      const opts = c.catalogo && c.catalogo.length 
        ? c.catalogo.map(o => `<option value="${o.valor}">${o.etiqueta}</option>`).join("") 
        : `<option value="">(catálogo ${c.endpoint ? 'remoto: ' + c.endpoint : 'sin opciones'})</option>`;
      return `<label><span>${c.etiqueta}${req}${api_badge}</span><select name="${c.nombre}">
        <option value="">— elegir —</option>
        ${opts}</select></label>`;
    }
    return `<label><span>${c.etiqueta}${req}${api_badge}</span><input name="${c.nombre}" ${c.solo_lectura?"readonly value='(autocompletado)'":""}></label>`
  }).join("")||"<p style='color:var(--gris)'>Esta tarea no muestra pantallas al usuario.</p>";
  pintarSidebar();
  cont.innerHTML=`<div class="tarjeta">${stepper}
    <div class="encabezado"><strong>${t.nombre}</strong><span class="actor">${ACTORES[t.actor]||""}</span></div>
    ${campos}
    <div class="pie"><button class="sec" onclick="retroceder()">← Atrás</button>
    <button onclick="avanzar()">Continuar →</button></div></div>
    <div class="rastro">Recorrido: ${ESTADO.rastro.map(x=>TAREAS[x].nombre).join(" → ")}</div>`;
}
function reiniciar(){ESTADO.tarea=INICIAL;ESTADO.rastro=[INICIAL];ESTADO.datos={};pintar()}
reiniciar();
"""


def generar(m: Manifiesto) -> str:
    a = analizar(m)
    e = _html.escape

    tareas = {
        t.id: {"nombre": t.nombre, "actor": t.actor or "", "terminal": t.terminal,
               "pantallas": [p.id for p in t.pantallas]}
        for t in m.flujo.tareas
    }
    pantallas = {
        p.id: {
            "nombre": p.nombre,
            "paso_ciudadano": p.paso_ciudadano,
            "campos": [
                {"nombre": c.nombre, "etiqueta": c.etiqueta or c.nombre,
                 "obligatorio": c.obligatorio, "solo_lectura": c.solo_lectura,
                 "catalogo": [{"etiqueta": o.etiqueta, "valor": o.valor} for o in c.catalogo]}
                for c in p.campos
            ],
        }
        for p in m.pantallas
    }
    actores = {x.id: x.nombre for x in m.actores}
    pasos = sorted({p.paso_ciudadano for p in m.pantallas if p.paso_ciudadano})
    inicial = next((t.id for t in m.flujo.tareas if t.inicial), None)

    problemas = ""
    if a.problemas:
        filas = "".join(f"<li>{e(p)}</li>" for p in a.problemas)
        problemas = (
            f'<div class="problemas"><h2>{len(a.problemas)} problema(s) detectado(s) '
            f"en el flujo</h2><ul>{filas}</ul></div>"
        )

    datos = (
        f"const TAREAS={json.dumps(tareas, ensure_ascii=False)};\n"
        f"const PANTALLAS={json.dumps(pantallas, ensure_ascii=False)};\n"
        f"const ACTORES={json.dumps(actores, ensure_ascii=False)};\n"
        f"const TRANSICIONES={json.dumps(a.transiciones, ensure_ascii=False)};\n"
        f"const PASOS={json.dumps(pasos)};\n"
        f"const INICIAL={json.dumps(inicial)};\n"
        "const ESTADO={tarea:INICIAL,rastro:[INICIAL],datos:{}};\n"
    )

    return f"""<title>Simulación — {e(m.tramite.nombre)}</title>
<style>{_ESTILO}</style>
<div class="layout">
<div class="sim-sidebar">
  <strong style="display:block;margin-bottom:0.5rem;color:var(--guinda)">Simulador GPM</strong>
  <div style="font-size:0.8rem;color:var(--gris);margin-bottom:1.5rem;line-height:1.4">
    Puedes navegar libremente entre las pantallas del trámite para probarlas.
  </div>
  <div id="sim-sidebar-nav"></div>
</div>
<div class="sim-main">
<div class="barra">
  <strong>{e(m.tramite.nombre)}</strong>
  <em>Simulación — Compilador GPM</em>
</div>
<div class="barra2">Vista previa del trámite · no conectada a ningún sistema</div>
<div class="marco" style="margin:0 auto;width:100%">
  <div class="aviso">
    <strong>Esto es una simulación, no es la plataforma GPM.</strong> No guarda nada, no envía
    nada y no está conectada a ningún sistema de gobierno. Reproduce el flujo, los pasos, los
    campos y las ramas del manifiesto para revisarlos antes de importar.
  </div>
  <div id="lienzo"></div>
  {problemas}
</div></div></div>
<script>{datos}{_GUION}</script>"""
