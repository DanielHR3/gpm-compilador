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

from gpmc.nucleo.integraciones import resolver
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.simulador.analisis import analizar
from gpmc.simulador.documentos import documentos_de


def _js(obj) -> str:
    """JSON para incrustar en un <script>. Escapa '<' y los separadores de
    linea U+2028/U+2029 para que un nombre de tarea con '</script>' o un
    salto de linea Unicode no rompa la etiqueta ni el parseo."""
    salida = json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")
    salida = salida.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return salida


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
/* Instrucciones de la pantalla: mismo patron que el componente
   `Instrucciones` de la SPA, en HTML plano porque esta vista la genera
   Python. Abre desplegado; a diferencia de la SPA no recuerda si se
   plego, porque esta pagina es de un solo uso. */
.ayuda{max-width:70ch;margin:1rem auto 0;border:1px solid var(--linea);border-radius:8px;background:#fff;font-size:.86rem}
.ayuda>summary{cursor:pointer;padding:.6rem .9rem;font-weight:600;color:var(--tinta)}
.ayuda>div{border-top:1px solid var(--linea);padding:.7rem .9rem;color:var(--gris);display:flex;flex-direction:column;gap:.5rem}
.ayuda p{margin:0}
.ayuda strong{color:var(--tinta)}
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

/* --- Documentos del tramite ------------------------------------------
   La miniatura de cada tarjeta es la plantilla de verdad dibujada en
   pequeno, no un icono: de un vistazo se distingue un oficio redactado de
   un volcado de PDF escaneado, que es justo lo que hay que cazar. */
.docs-cab{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;
          flex-wrap:wrap;margin-bottom:1.4rem}
.docs-cab h2{margin:0;font-size:1.2rem;letter-spacing:-.01em}
.docs-cab p{margin:.35rem 0 0;font-size:.86rem;color:var(--gris);max-width:62ch}
.docs-resumen{display:flex;gap:.4rem;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:.3rem;font-size:.72rem;font-weight:600;
      padding:.22rem .6rem;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.chip.ok{background:#e9f3f0;color:var(--verde);border-color:#c2dcd5}
.chip.warn{background:#fdf2e6;color:#8a4b09;border-color:#f0d7b6}
.chip.off{background:var(--suave);color:var(--gris);border-color:var(--linea)}
.docs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(19rem,1fr));gap:1.15rem}
.doc{background:#fff;border:1px solid var(--linea);border-radius:.85rem;display:flex;
     flex-direction:column;overflow:hidden;
     transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
.doc:hover{transform:translateY(-3px);border-color:#d9c4c9;
           box-shadow:0 16px 30px -20px rgba(94,19,44,.55)}
.doc:focus-within{border-color:var(--guinda);box-shadow:0 0 0 3px rgba(94,19,44,.13)}
.doc-hoja{position:relative;height:9.5rem;background:#fff;border-bottom:1px solid var(--linea);
          overflow:hidden;cursor:pointer}
.doc-hoja pre{margin:0;padding:.85rem 1rem;white-space:pre-wrap;word-break:break-word;
              font:6px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#3a3d44}
.doc-hoja::after{content:"";position:absolute;inset:auto 0 0 0;height:3.6rem;
                 background:linear-gradient(to bottom,rgba(255,255,255,0),#fff 85%)}
.doc-hoja.rota pre{color:#9b6b17}
.doc-hoja.vacia{display:grid;place-items:center;color:var(--gris);font-size:.78rem;
  background:repeating-linear-gradient(45deg,#fcfbfb,#fcfbfb 9px,#f5f2f2 9px,#f5f2f2 18px)}
.doc-hoja.vacia::after{display:none}
.doc-cuerpo{padding:.9rem 1.05rem 1rem;display:flex;flex-direction:column;gap:.6rem;flex:1}
.doc-cuerpo>.chip{align-self:flex-start}
.doc-cuerpo h3{margin:0;font-size:.95rem;line-height:1.35;letter-spacing:-.01em}
.doc-meta{margin:0;display:grid;gap:.3rem;font-size:.78rem}
.doc-meta div{display:flex;gap:.45rem}
.doc-meta dt{color:var(--gris);flex:0 0 5.4rem}
.doc-meta dd{margin:0;color:var(--tinta)}
.doc-nota{margin:0;font-size:.76rem;color:#8a4b09;background:#fdf2e6;border-radius:.4rem;
          padding:.45rem .6rem;line-height:1.45}
.doc-pie{display:flex;gap:.5rem;padding:.75rem 1.05rem;border-top:1px solid var(--linea);
         background:#fffdfd}
.doc-pie button{flex:1;font-size:.82rem;padding:.45rem .6rem}
.doc-pie button[disabled]{opacity:.45;cursor:not-allowed}
.sb-cuenta{background:var(--suave);color:var(--gris);border-radius:999px;padding:0 .4rem;
           font-size:.72rem;margin-left:.3rem}
.sim-nav-item.act .sb-cuenta{background:rgba(255,255,255,.25);color:#fff}

/* Vista previa: la hoja a tamano de lectura, sobre un velo oscuro. */
.velo{position:fixed;inset:0;background:rgba(26,10,15,.55);display:flex;align-items:center;
      justify-content:center;padding:1.5rem;z-index:50}
.modal{background:#fff;border-radius:.9rem;width:min(52rem,100%);max-height:100%;
       display:flex;flex-direction:column;overflow:hidden;box-shadow:0 30px 60px -20px rgba(0,0,0,.5)}
.modal header{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;
              padding:1rem 1.25rem;border-bottom:1px solid var(--linea)}
.modal header h3{margin:0;font-size:1rem}
.modal header p{margin:.25rem 0 0;font-size:.78rem;color:var(--gris)}
.modal .cerrar{background:transparent;border:1px solid var(--linea);color:var(--gris);
               border-radius:.4rem;padding:.25rem .6rem;line-height:1}
.modal-cuerpo{overflow:auto;padding:1.5rem;background:#f4efef}
.hoja{background:#fff;max-width:44rem;margin:0 auto;padding:2.6rem 2.8rem;
      box-shadow:0 2px 14px rgba(0,0,0,.12);border-radius:2px}
.hoja pre{margin:0;white-space:pre-wrap;word-break:break-word;
          font:13px/1.65 "Times New Roman",Georgia,serif;color:#111}
.hoja .firma{margin-top:3rem;text-align:center;font-size:.85rem;color:var(--gris)}
.hoja .firma b{display:block;color:var(--tinta);border-top:1px solid #999;padding-top:.4rem;
               max-width:22rem;margin:0 auto .15rem}
.modal footer{display:flex;justify-content:space-between;align-items:center;gap:.75rem;
              padding:.85rem 1.25rem;border-top:1px solid var(--linea);flex-wrap:wrap}
.modal footer small{color:var(--gris);font-size:.75rem}
@media (max-width:700px){
  .docs-grid{grid-template-columns:1fr}
  .hoja{padding:1.4rem 1.2rem}
  .modal-cuerpo{padding:.75rem}
}
"""

_GUION = """
// Todo lo que venga del manifiesto (nombres de tarea, etiquetas, valores de
// catalogo) se escapa antes de entrar al DOM por innerHTML: un Diccionario con
// '<br>' o '<img onerror=...>' en una etiqueta —cosa que ya se ha visto en
// catalogos reales— no debe romper el render ni ejecutar nada.
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>(
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
const ir=(id)=>{ESTADO.tarea=id;ESTADO.rastro.push(id);pintar()};
// Los nombres de campo van por CSS.escape en los selectores y por esc() en los
// atributos: hoy son \\w+ de <=30, pero la defensa va en el punto de uso.
function porNombre(n){return document.querySelector(`[name="${CSS.escape(n)}"]`)}
function valorActual(campo){const el=porNombre(campo);return el?el.value:""}
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
  if(t.campos){
    // Bifurcacion sobre varios campos (condicion con clausulas Y): la clave
    // de "destinos" es JSON.stringify() de los valores capturados, en el
    // mismo orden que "campos" -- ver analisis.py, misma codificacion.
    const vals=t.campos.map(c=>ESTADO.datos[c]);
    const clave=JSON.stringify(vals);
    const destino=t.destinos[clave];
    if(destino){return ir(destino)}
    const desc=t.campos.map((c,i)=>c+"="+(vals[i]||"(vacío)")).join(", ");
    alert("Ninguna rama corresponde a «"+desc+"». En la plataforma el trámite quedaría detenido aquí.");
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
        const activa = (id === ESTADO.tarea && ESTADO.vista !== "documentos") ? "act" : "";
        // data-id + delegación en vez de onclick="saltarA('${id}')": un id con
        // comilla rompería el string JS del atributo.
        html += `<button class="sim-nav-item ${activa}" data-id="${esc(id)}">📄 ${esc(t.nombre)}</button>`;
    }
  }
  html += '</div>';
  // Los documentos son una vista aparte, no una pantalla mas del recorrido:
  // no se capturan, se recogen al final.
  if(DOCUMENTOS.length){
    const act=(ESTADO.vista==="documentos")?"act":"";
    html += `<div style="margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid var(--linea)">
      <b style="font-size:0.9rem;display:block;margin-bottom:0.5rem">Lo que entrega:</b>
      <button class="sim-nav-item ${act}" data-vista="documentos">🗂️ Documentos<span class="sb-cuenta">${DOCUMENTOS.length}</span></button></div>`;
  }
  html += `<div style="margin-top:auto"><button class="sim-nav-item" style="color:var(--guinda);border:1px solid var(--guinda)" onclick="window.history.back()">← Salir del Simulador</button></div>`;
  cont.innerHTML = html;
  cont.querySelectorAll("[data-id]").forEach(b =>
    b.addEventListener("click", () => saltarA(b.dataset.id)));
  cont.querySelectorAll("[data-vista]").forEach(b =>
    b.addEventListener("click", () => vistaDocumentos()));
}

function saltarA(id) {
  ESTADO.vista = "recorrido";
  ESTADO.tarea = id;
  if (!ESTADO.rastro.includes(id)) {
    ESTADO.rastro.push(id);
  }
  pintar();
}

function pintar(){
  const ayuda=document.querySelector(".ayuda");
  if(ayuda){ayuda.style.display=(ESTADO.vista==="documentos")?"none":""}
  if(ESTADO.vista==="documentos"){pintarSidebar();pintarDocumentos();return}
  const t=TAREAS[ESTADO.tarea];
  const cont=document.getElementById("lienzo");
  if(t.terminal){pintarSidebar();
  cont.innerHTML=`<div class="tarjeta"><div class="encabezado"><strong>${esc(t.nombre)}</strong></div>
    <p>El trámite concluyó. Recorrido: ${ESTADO.rastro.map(x=>esc(TAREAS[x].nombre)).join(" → ")}</p>
    <div class="pie"><button class="sec" onclick="retroceder()">← Atrás</button>
    <button onclick="reiniciar()">Reiniciar</button></div></div>`;return}
  const pantallas=(t.pantallas||[]).map(pid=>PANTALLAS[pid]);
  const paso=pantallas.find(p=>p&&p.paso_ciudadano);
  let stepper="";
  if(paso){stepper=`<div class="stepper">`+PASOS.map(n=>
    `<div class="paso ${n===paso.paso_ciudadano?"activo":(n<paso.paso_ciudadano?"hecho":"")}">${n}</div>`).join("")+`</div>`}
  const camposDeLaTarea=pantallas.flatMap(p=>p?p.campos:[]);
  const campos=camposDeLaTarea.map(c=>{
    const req=c.obligatorio?` <span class="req">*</span>`:"";
    let api_badge = "";
    if (c.dependencia_tipo === "api_ajax") {
      api_badge = ` <span style="font-size:0.75rem;color:var(--guinda);background:var(--fondo);padding:0.1rem 0.4rem;border-radius:1rem;border:1px solid var(--guinda)">⚡ API AJAX</span>`;
    } else if (c.dependencia_tipo === "campo") {
      api_badge = ` <span style="font-size:0.75rem;color:var(--tinta);background:var(--suave);padding:0.1rem 0.4rem;border-radius:1rem;">Depende de: ${esc(c.dependencia_campo)}</span>`;
    }

    if (c.tipo === "select" || (c.catalogo && c.catalogo.length)) {
      // Un desplegable se dibuja como desplegable aunque no se pueda poblar:
      // deshabilitado dice la verdad, una caja de texto no.
      if (c.catalogo && c.catalogo.length) {
        const opts = c.catalogo.map(o => `<option value="${esc(o.valor)}">${esc(o.etiqueta)}</option>`).join("");
        return `<label><span>${esc(c.etiqueta)}${req}${api_badge}</span><select name="${esc(c.nombre)}">
          <option value="">— elegir —</option>${opts}</select></label>`;
      }
      if (c.catalogo_url) {
        return `<label><span>${esc(c.etiqueta)}${req}${api_badge}</span>
          <select name="${esc(c.nombre)}" disabled><option value="">(consultando…)</option></select></label>`;
      }
      return `<label><span>${esc(c.etiqueta)}${req}${api_badge}</span>
        <select name="${esc(c.nombre)}" disabled><option value="">(sin catálogo resoluble)</option></select></label>`;
    }
    return `<label><span>${esc(c.etiqueta)}${req}${api_badge}</span><input name="${esc(c.nombre)}" ${c.solo_lectura?"readonly value='(autocompletado)'":""}></label>`
  }).join("")||"<p style='color:var(--gris)'>Esta tarea no muestra pantallas al usuario.</p>";
  pintarSidebar();
  cont.innerHTML=`<div class="tarjeta">${stepper}
    <div class="encabezado"><strong>${esc(t.nombre)}</strong><span class="actor">${esc(ACTORES[t.actor]||"")}</span></div>
    ${campos}
    <div class="pie"><button class="sec" onclick="retroceder()">← Atrás</button>
    <button onclick="avanzar()">Continuar →</button></div></div>
    <div class="rastro">Recorrido: ${ESTADO.rastro.map(x=>esc(TAREAS[x].nombre)).join(" → ")}</div>`;
  conectarCatalogos(camposDeLaTarea);
}
// Los catalogos remotos se piden desde el navegador, no desde Python: es donde
// la plataforma tambien los pide, y los tres endpoints responden con CORS
// abierto. Un fallo se dice en voz alta — un desplegable vacio por falta de red
// no se distingue de uno vacio de verdad.
async function poblar(campo,el,valorPadre){
  if(!campo.catalogo_url){return}
  let url=campo.catalogo_url;
  if(campo.depende_de){
    if(!valorPadre){
      el.disabled=true;
      el.innerHTML=`<option value="">(elige ${esc(campo.depende_de)} primero)</option>`;
      return;
    }
    url=url.replace("{padre}",encodeURIComponent(valorPadre));
  }
  el.disabled=true;
  el.innerHTML='<option value="">(consultando…)</option>';
  // Sin timeout, una API de gobierno colgada deja el desplegable en
  // "(consultando…)" para siempre.
  const ctrl=new AbortController();
  const reloj=setTimeout(()=>ctrl.abort(),8000);
  try{
    const res=await fetch(url,{signal:ctrl.signal});
    // fetch() resuelve con 404 o 500. Sin esto, un error con cuerpo JSON caeria
    // en la lista vacia y el desplegable saldria habilitado y vacio, que un
    // analista no puede distinguir de un catalogo genuinamente vacio.
    if(!res.ok){throw new Error("HTTP "+res.status)}
    const datos=(await res.json())[campo.catalogo_nodo]||[];
    // new Option() fija texto y valor como propiedades, no como marcado: un
    // nombre de colonia con comillas o con < no puede romper el atributo ni
    // inyectar nada. El invariante del proyecto sobre escapado no admite
    // excepciones, y uno de los tres endpoints es un dominio de terceros.
    el.replaceChildren(new Option("— elegir —",""));
    datos.forEach(o=>el.appendChild(
      new Option(o[campo.catalogo_etiqueta], o[campo.catalogo_valor])));
    el.disabled=false;
  }catch(err){
    el.innerHTML='<option value="">(no se pudo consultar el catálogo)</option>';
  }finally{
    clearTimeout(reloj);
  }
}
function conectarCatalogos(campos){
  campos.forEach(c=>{
    const el=porNombre(c.nombre);
    if(!el||!c.catalogo_url){return}
    if(c.depende_de){
      const padre=porNombre(c.depende_de);
      if(padre){padre.addEventListener("change",()=>poblar(c,el,padre.value))}
      poblar(c,el,padre?padre.value:"");
    }else{
      poblar(c,el,null);
    }
  });
}

// --- Documentos --------------------------------------------------------
// Un documento no es una pantalla del recorrido: no se captura, se recoge.
// Por eso vive en su propia vista y no en el paso a paso.
const _CHIP={legible:["ok","Plantilla legible"],
             ilegible:["warn","Sin texto legible"],
             sin_plantilla:["off","Sin plantilla"]};

function vistaDocumentos(){ESTADO.vista="documentos";pintar()}
function volverAlRecorrido(){ESTADO.vista="recorrido";pintar()}

function cuandoSeGenera(d){
  if(!d.tarea){return "no está enganchado a ninguna tarea"}
  return (d.instante==="antes"?"al abrir «":"al terminar «")+d.tarea+"»";
}

function miniatura(d){
  if(d.estado==="sin_plantilla"){
    return `<div class="doc-hoja vacia">Sin plantilla en el expediente</div>`}
  // 1400 caracteres bastan para llenar la miniatura; mandar la plantilla
  // entera solo engorda el DOM de una vista que se recorre completa.
  return `<div class="doc-hoja ${d.estado==="ilegible"?"rota":""}" data-ver="${esc(d.id)}"
    role="button" tabindex="0" aria-label="Vista previa de ${esc(d.nombre)}"
    ><pre>${esc(d.plantilla.slice(0,1400))}</pre></div>`;
}

function tarjetaDoc(d){
  const chip=_CHIP[d.estado]||["off",d.estado];
  const firma=d.firmador_nombre
    ? `<div><dt>Firma</dt><dd>${esc(d.firmador_nombre)}${d.firmador_cargo?" — "+esc(d.firmador_cargo):""}</dd></div>`
    : "";
  const puede=d.estado!=="sin_plantilla";
  return `<article class="doc">${miniatura(d)}
    <div class="doc-cuerpo">
      <span class="chip ${chip[0]}">${esc(chip[1])}</span>
      <h3>${esc(d.titulo||d.nombre)}</h3>
      <dl class="doc-meta">
        <div><dt>Se genera</dt><dd>${esc(cuandoSeGenera(d))}</dd></div>
        ${d.actor?`<div><dt>Responsable</dt><dd>${esc(d.actor)}</dd></div>`:""}
        ${firma}
      </dl>
      ${d.nota?`<p class="doc-nota">${esc(d.nota)}</p>`:""}
    </div>
    <div class="doc-pie">
      <button class="sec" data-ver="${esc(d.id)}"${puede?"":" disabled"}>Vista previa</button>
      <button data-baja="${esc(d.id)}"${puede?"":" disabled"}>Descargar PDF</button>
    </div></article>`;
}

function pintarDocumentos(){
  const cont=document.getElementById("lienzo");
  const buenos=DOCUMENTOS.filter(d=>d.estado==="legible").length;
  const revisar=DOCUMENTOS.length-buenos;
  cont.innerHTML=`<div class="docs-cab">
      <div>
        <h2>Documentos que entrega el trámite</h2>
        <p>Son las acciones de tipo <b>documento</b> del manifiesto. Cada tarjeta
        muestra la plantilla tal como quedó guardada y en qué punto del flujo se
        genera. Descargar imprime la hoja; es una simulación, no un documento válido.</p>
      </div>
      <div class="docs-resumen">
        ${buenos?`<span class="chip ok">${buenos} con plantilla legible</span>`:""}
        ${revisar?`<span class="chip warn">${revisar} por revisar</span>`:""}
      </div>
    </div>
    <div class="docs-grid">${DOCUMENTOS.map(tarjetaDoc).join("")}</div>
    <div style="margin-top:1.75rem"><button class="sec" onclick="volverAlRecorrido()">← Volver al recorrido</button></div>`;
  cont.querySelectorAll("[data-ver]").forEach(b=>{
    b.addEventListener("click",()=>abrirDoc(b.dataset.ver));
    // La miniatura es un div con role=button: el teclado no lo activa solo.
    b.addEventListener("keydown",e=>{
      if(e.key==="Enter"||e.key===" "){e.preventDefault();abrirDoc(b.dataset.ver)}});
  });
  cont.querySelectorAll("[data-baja]").forEach(b=>
    b.addEventListener("click",()=>descargarDoc(b.dataset.baja)));
}

function firmaHTML(d){
  if(!d.firmador_nombre){return ""}
  return `<div class="firma"><b>${esc(d.firmador_nombre)}</b>${esc(d.firmador_cargo||"")}</div>`;
}

function hojaHTML(d){
  const sub=d.subtitulo?`<p style="text-align:center;color:#555;margin:.2rem 0 1.4rem">${esc(d.subtitulo)}</p>`:"";
  return `<article class="hoja">${sub}<pre>${esc(d.plantilla)}</pre>${firmaHTML(d)}</article>`;
}

let _focoPrevio=null;
function abrirDoc(id){
  const d=DOCUMENTOS.find(x=>x.id===id);
  if(!d||d.estado==="sin_plantilla"){return}
  cerrarDoc();
  _focoPrevio=document.activeElement;
  const velo=document.createElement("div");
  velo.className="velo";velo.id="velo-doc";
  velo.innerHTML=`<div class="modal" role="dialog" aria-modal="true" aria-labelledby="doc-tit">
    <header>
      <div><h3 id="doc-tit">${esc(d.titulo||d.nombre)}</h3>
      <p>Se genera ${esc(cuandoSeGenera(d))}</p></div>
      <button class="cerrar" aria-label="Cerrar vista previa">✕</button>
    </header>
    <div class="modal-cuerpo">${hojaHTML(d)}</div>
    <footer>
      <small>Simulación. La plataforma generará este documento con la plantilla
      guardada en el expediente.</small>
      <button data-baja="${esc(d.id)}">Descargar PDF</button>
    </footer></div>`;
  document.body.appendChild(velo);
  velo.addEventListener("click",e=>{if(e.target===velo){cerrarDoc()}});
  velo.querySelector(".cerrar").addEventListener("click",cerrarDoc);
  velo.querySelector("[data-baja]").addEventListener("click",()=>descargarDoc(d.id));
  document.addEventListener("keydown",_teclaModal);
  velo.querySelector(".cerrar").focus();
}
function _teclaModal(e){if(e.key==="Escape"){cerrarDoc()}}
function cerrarDoc(){
  const velo=document.getElementById("velo-doc");
  if(!velo){return}
  velo.remove();
  document.removeEventListener("keydown",_teclaModal);
  if(_focoPrevio&&_focoPrevio.focus){_focoPrevio.focus()}
}

// La descarga imprime una hoja aparte y deja que el navegador la guarde como
// PDF. Sin libreria y sin ventana emergente: un iframe oculto no lo bloquea
// ningun navegador, y lo que se imprime es exactamente lo que se ve.
function paginaImpresa(d){
  const titulo=esc(d.titulo||d.nombre);
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${titulo}</title>
<style>
@page{size:letter;margin:2.2cm 2.4cm}
body{font:12pt/1.65 "Times New Roman",Georgia,serif;color:#111;margin:0}
@media screen{body{padding:2.2cm 2.4cm;max-width:21.6cm;margin:0 auto}}
.sello{border:1px solid #999;color:#666;font:8pt/1.3 Arial,sans-serif;letter-spacing:.08em;
       text-align:center;padding:.25rem;margin-bottom:1.4rem;text-transform:uppercase}
h1{font-size:13pt;text-align:center;margin:0 0 .3rem}
.sub{text-align:center;color:#555;font-size:10pt;margin:0 0 1.6rem}
pre{font:inherit;white-space:pre-wrap;word-break:break-word;margin:0}
.firma{margin-top:3.2rem;text-align:center;font-size:10pt;color:#444}
.firma b{display:block;border-top:1px solid #777;max-width:22rem;margin:0 auto .2rem;
         padding-top:.35rem;color:#111}
.pie{margin-top:2.4rem;border-top:1px solid #ddd;padding-top:.4rem;
     font:7.5pt/1.4 Arial,sans-serif;color:#888}
</style></head><body>
<div class="sello">Simulación — Compilador GPM · ${esc(TRAMITE)}</div>
<h1>${titulo}</h1>
${d.subtitulo?`<p class="sub">${esc(d.subtitulo)}</p>`:""}
<pre>${esc(d.plantilla)}</pre>
${d.firmador_nombre?`<div class="firma"><b>${esc(d.firmador_nombre)}</b>${esc(d.firmador_cargo||"")}</div>`:""}
<div class="pie">Documento simulado por el Compilador GPM para revisar la plantilla del
expediente. No tiene validez oficial y no proviene de ningún sistema de gobierno.</div>
</body></html>`;
}

function descargarDoc(id){
  const d=DOCUMENTOS.find(x=>x.id===id);
  if(!d||d.estado==="sin_plantilla"){return}
  let marco=document.getElementById("imprenta");
  if(!marco){
    marco=document.createElement("iframe");
    marco.id="imprenta";
    marco.setAttribute("aria-hidden","true");
    marco.setAttribute("tabindex","-1");
    marco.style.cssText="position:fixed;right:0;bottom:0;width:0;height:0;border:0";
    document.body.appendChild(marco);
  }
  marco.onload=()=>{
    try{marco.contentWindow.focus();marco.contentWindow.print()}
    catch(err){alert("El navegador no dejó imprimir. Abre la vista previa y usa Archivo → Imprimir.")}
  };
  marco.srcdoc=paginaImpresa(d);
}

function reiniciar(){ESTADO.vista="recorrido";cerrarDoc();ESTADO.tarea=INICIAL;ESTADO.rastro=[INICIAL];ESTADO.datos={};pintar()}
reiniciar();
"""


def _catalogo_de_campo(c) -> dict:
    """Lo que el navegador necesita para poblar un select remoto.

    La plataforma interpola `@@campo` en tiempo de ejecucion; el simulador no
    tiene ese runtime, asi que la URL viaja con un hueco `{padre}` que el
    JavaScript sustituye por el valor elegido. Sin endpoint resoluble devuelve
    un dict vacio y el campo se dibuja como desplegable deshabilitado: nunca
    como caja de texto, porque el simulador no puede mentir sobre lo que hara
    la plataforma.
    """
    if c.tipo != "select":
        # conectarCatalogos recorre todos los campos: si un campo de texto
        # trajera catalogo_url, poblar() lo deshabilitaria y el analista
        # veria una caja bloqueada donde la plataforma pone una editable.
        return {}
    cat = resolver(c.endpoint)
    if cat is None:
        return {}
    if cat.requiere_padre and not c.dependencia_campo:
        # Sin campo padre la URL no se puede construir: url_para(None) la
        # dejaria colgando en '@@'. El compilador degrada este caso a catalogo
        # manual; aqui se degrada a desplegable deshabilitado. Mentir con una
        # URL rota es peor que decir que no hay catalogo.
        return {}
    # La plataforma interpola @@campo en tiempo de ejecucion. El simulador no
    # tiene ese runtime, asi que se sustituye por un hueco que el JavaScript
    # rellena con el valor elegido — y de paso la pagina no lleva sintaxis GPM.
    url = cat.url.replace("@@{padre}", "{padre}") if cat.requiere_padre else cat.url
    return {
        "catalogo_url": url,
        "catalogo_nodo": cat.nodo,
        "catalogo_etiqueta": cat.etiqueta,
        "catalogo_valor": cat.valor,
        # Solo si el catalogo lo toma: marcarlo en un catalogo simple haria
        # que el simulador pidiera un padre que la plataforma no pide.
        "depende_de": c.dependencia_campo if cat.requiere_padre else None,
    }


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
                 "tipo": c.tipo,
                 "dependencia_tipo": c.dependencia_tipo,
                 "dependencia_campo": c.dependencia_campo,
                 "catalogo": [{"etiqueta": o.etiqueta, "valor": o.valor} for o in c.catalogo],
                 **_catalogo_de_campo(c)}
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
        f"const TAREAS={_js(tareas)};\n"
        f"const PANTALLAS={_js(pantallas)};\n"
        f"const ACTORES={_js(actores)};\n"
        f"const TRANSICIONES={_js(a.transiciones)};\n"
        f"const PASOS={_js(pasos)};\n"
        f"const INICIAL={_js(inicial)};\n"
        f"const DOCUMENTOS={_js(documentos_de(m))};\n"
        f"const TRAMITE={_js(m.tramite.nombre)};\n"
        "const ESTADO={tarea:INICIAL,rastro:[INICIAL],datos:{},vista:\"recorrido\"};\n"
    )

    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Simulación — {e(m.tramite.nombre)}</title>
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
<details class="ayuda" aria-label="Instrucciones de la pantalla" open>
  <summary>¿Cómo funciona esta pantalla?</summary>
  <div>
    <p>Es un <strong>recorrido de prueba</strong> del trámite tal como lo verá
    el ciudadano. Sirve para cotejar que el flujo y las pantallas quedaron
    como los describe el TO-BE, antes de importar nada.</p>
    <p><strong>No escribe en ningún sistema.</strong> Nada de lo que captures
    aquí se guarda, no genera folio y no llega a la plataforma. Puedes probar
    todas las veces que quieras.</p>
    <p>Las <strong>bifurcaciones dependen de lo que captures</strong>: si una
    tarea lleva a dos caminos según un campo, el recorrido toma el que
    corresponda a tu respuesta. Para ver la otra rama, vuelve a empezar y
    contesta distinto.</p>
    <p>Si una pantalla no aparece o el recorrido se corta antes de tiempo, el
    flujo está incompleto: vuelve al paso 2 y revisa las inconsistencias de flujo.</p>
  </div>
</details>
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
