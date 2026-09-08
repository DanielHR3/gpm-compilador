"""Plantillas del asistente. Sin build de frontend ni dependencias externas."""

import html as _h

from gpmc.nucleo.huecos import NIVELES

# Paleta muestreada de capturas reales de la plataforma de modelado,
# pero con un diseño modernizado inspirado en bibliotecas UI modernas.
ESTILO = """
:root{
  --guinda:#831b43; --guinda2:#9d2050; --tinta:#09090b; --gris:#71717a;
  --linea:#e4e4e7; --fondo:#fafafa; --suave:#f4f4f5; --verde:#10b981;
  --alerta:#ef4444; --alerta-suave:#fef2f2; --ok:#ecfdf5;
  --sombra-card: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  --sombra-btn: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --ring: rgba(131, 27, 67, 0.2);
  --radio: 0.75rem; --radio-peq: 0.5rem;
}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
     font:15px/1.6 "Inter", ui-sans-serif, system-ui, -apple-system, sans-serif;}
.barra{background:#ffffff; color:var(--tinta); padding:1rem 2rem; display:flex;
       justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;
       border-bottom: 1px solid var(--linea); position: sticky; top: 0; z-index: 10;
       backdrop-filter: blur(8px); background-color: rgba(255,255,255,0.85);}
.barra strong{font-size:1.15rem; font-weight:600; letter-spacing: -0.01em;}
.barra em{font-style:normal;font-size:0.75rem; font-weight: 500; color:var(--guinda); background:var(--suave); padding:0.25rem 0.75rem; border-radius:1rem; border: 1px solid var(--linea);}

.layout{display:flex; min-height: calc(100vh - 60px);}
.sidebar{width: 250px; background: #ffffff; border-right: 1px solid var(--linea); padding: 2rem 1rem; display:flex; flex-direction:column; gap:0.5rem;}
.contenido{flex:1; padding: 3rem 2rem; max-width: 52rem; margin: 0 auto;}

.nav-item{display:flex; align-items:center; padding: 0.5rem 1rem; border-radius: var(--radio-peq); color: var(--gris); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: all 0.2s;}
.nav-item:hover{background: var(--suave); color: var(--tinta);}
.nav-item.act{background: var(--suave); color: var(--tinta); font-weight: 600;}
.nav-item.disabled{opacity: 0.5; pointer-events: none;}

.tarjeta{background:#fff; border:1px solid var(--linea); border-radius:var(--radio); padding:2rem; margin-bottom:1.5rem; box-shadow:var(--sombra-card); transition: box-shadow 0.2s;}
.tarjeta h2{font-size:1.15rem; margin:0 0 1.25rem; font-weight:600; color:var(--tinta); letter-spacing: -0.01em;}

label{display:block; margin-bottom:1.5rem;}
label b{display:block; font-weight:500; font-size:.9rem; margin-bottom:.35rem; color:var(--tinta);}
label em{display:block; font-style:normal; color:var(--gris); font-size:.85rem; margin-bottom:.6rem;}

input[type=text]{width:100%; padding:0.6rem 0.75rem; border:1px solid var(--linea); border-radius:var(--radio-peq); font:inherit; font-size:0.9rem; transition:all 0.2s; outline:none; background: #fff;}
input[type=text]:focus{border-color:var(--guinda); box-shadow: 0 0 0 3px var(--ring);}

/* Drag and Drop Zone */
.dropzone{width:100%; padding:2.5rem 2rem; border:1.5px dashed var(--linea); border-radius:var(--radio);
          background:#fafafa; color:var(--tinta); font:inherit; text-align:center;
          transition:all 0.2s ease; cursor:pointer; position:relative;}
.dropzone:hover, .dropzone.dragover{border-color:var(--guinda); background:rgba(131, 27, 67, 0.02);}
.dropzone input[type=file]{opacity:0; position:absolute; top:0; left:0; width:100%; height:100%; cursor:pointer;}
.dropzone-text{font-weight:500; color:var(--gris); font-size: 0.9rem;}
.dropzone-text span{color:var(--guinda); font-weight:600;}

button{padding:0.6rem 1.2rem; border-radius:var(--radio-peq); border:1px solid transparent;
       background:var(--tinta); color:#fff; font:inherit; font-size:0.9rem; font-weight:500; cursor:pointer;
       transition:all 0.2s; box-shadow:var(--sombra-btn);}
button:hover{background:#27272a; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);}
button:active{transform:translateY(1px);}
button:focus-visible{outline:none; box-shadow: 0 0 0 3px rgba(9, 9, 11, 0.2);}

a.btn{display:inline-flex; align-items:center; justify-content:center; padding:0.5rem 1rem; border:1px solid var(--linea); border-radius:var(--radio-peq);
      color:var(--tinta); text-decoration:none; font-size:0.9rem; font-weight:500; margin:0 .5rem .5rem 0;
      transition:all 0.2s; background: #fff; box-shadow: var(--sombra-btn);}
a.btn:hover{background:var(--suave); border-color:#d4d4d8;}
a.btn.p{background:var(--guinda); color:#fff; border-color:transparent;}
a.btn.p:hover{background:var(--guinda2);}

table{width:100%; border-collapse:collapse; font-size:.85rem; margin-top:1rem;}
th,td{text-align:left; padding:0.75rem 1rem; border-bottom:1px solid var(--linea); vertical-align:top;}
th{background:#fff; color:var(--gris); font-weight:500; font-size:.8rem; border-bottom: 2px solid var(--linea);}

.huecos{background:#fff; border:1px solid var(--alerta); border-radius:var(--radio);
        padding:1.5rem; margin-bottom:1.5rem; box-shadow: 0 1px 2px 0 rgba(239, 68, 68, 0.05);}
.huecos h2{color:var(--alerta); font-size:1.05rem; margin:0 0 1rem; display:flex; align-items:center; gap:0.5rem;}
.huecos li{font-size:.9rem; margin-bottom:.5rem; line-height:1.5; color:var(--tinta);}
details.huecos{padding:1rem 1.5rem; border-color: var(--linea);}
details.huecos h2{color: var(--tinta);}
details.huecos summary{cursor:pointer; font-size:0.95rem; font-weight:500; outline:none;}
details.huecos summary:focus-visible{color: var(--guinda);}
details.huecos summary::-webkit-details-marker {display:none;}
details.huecos ul{margin:1rem 0 .5rem; padding-left:1.5rem;}

.cifras{display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:1rem; margin:1rem 0 1.5rem;}
.cifra{background:#fff; padding:1.25rem; border-radius:var(--radio); text-align:center; border: 1px solid var(--linea); box-shadow: var(--sombra-card);}
.cifra b{display:block; font-size:2rem; line-height:1; color:var(--tinta); margin-bottom:0.35rem; font-weight: 600; letter-spacing: -0.02em;}
.cifra span{font-size:.8rem; color:var(--gris); font-weight:500;}

.err{background:var(--alerta-suave); border:1px solid rgba(239, 68, 68, 0.2); color:var(--alerta);
     padding:1rem 1.25rem; border-radius:var(--radio-peq); margin-bottom:1.5rem; font-size:.9rem; font-weight:500; display:flex; align-items:center; gap:0.5rem;}
.nota{font-size:.85rem; color:var(--gris); margin-top:2rem; padding:1.25rem; background:var(--suave); border-radius:var(--radio-peq); border: 1px solid var(--linea);}
"""





def _envoltura(titulo: str, cuerpo: str, paso: int, sid: str = "") -> str:
    # Sidebar layout and clickable steps if sid is present
    
    # CSS additions for sidebar layout
    sidebar_css = '''
    .layout { display: flex; min-height: 100vh; }
    .sidebar { width: 260px; background: #fff; border-right: 1px solid var(--linea); padding: 2rem 1.5rem; flex-shrink: 0; box-shadow: var(--sombra); z-index: 10; }
    .main-content { flex: 1; display: flex; flex-direction: column; background: var(--fondo); height: 100vh; overflow-y: auto; }
    .sidebar-title { font-size: 1.1rem; font-weight: 700; color: var(--guinda); margin-bottom: 2rem; display: flex; align-items: center; gap: 0.5rem; }
    .nav-item { display: block; padding: 0.75rem 1rem; color: var(--gris); text-decoration: none; border-radius: var(--radio-peq); margin-bottom: 0.5rem; font-weight: 500; transition: all 0.2s; }
    .nav-item:hover { background: var(--suave); color: var(--tinta); }
    .nav-item.act { background: var(--guinda); color: #fff; box-shadow: var(--sombra); }
    .nav-item.disabled { opacity: 0.5; pointer-events: none; }
    '''
    
    # Sidebar navigation items
    nav_links = ""
    if sid:
        nav_links += f'''
        <a href="/" class="nav-item {'act' if paso == 1 else ''}">1. Insumos</a>
        <a href="/revisar/{sid}" class="nav-item {'act' if paso == 2 else ''}">2. Revisión</a>
        <a href="/simulador/{sid}" class="nav-item {'act' if paso == 3 else ''}">3. Simulación</a>
        <a href="#descargas" class="nav-item {'act' if paso == 4 else ''}" onclick="document.getElementById('descargas').scrollIntoView({{behavior:'smooth'}});">4. Descarga</a>
        <a href="/aprobacion/{sid}" class="nav-item">📄 HTML de Aprobación</a>
        '''
    else:
        nav_links += f'''
        <a href="/" class="nav-item {'act' if paso == 1 else ''}">1. Insumos</a>
        <span class="nav-item disabled">2. Revisión</span>
        <span class="nav-item disabled">3. Simulación</span>
        <span class="nav-item disabled">4. Descarga</span>
        '''
        
    nav_links += '<hr style="border:0;border-top:1px solid var(--linea);margin:2rem 0;"><a href="/historial" class="nav-item ' + ('act' if paso == 0 else '') + '">🕒 Historial</a>'

    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_h.escape(titulo)}</title><style>{ESTILO}{sidebar_css}</style></head><body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-title">GPMC</div>
    <div class="nav-menu">
      {nav_links}
    </div>
  </div>
  <div class="main-content">
    <div class="barra"><strong>{_h.escape(titulo)}</strong>
    <em>Dirección de Gestión Tecnológica</em></div>
    <div class="barra2">Herramienta interna · genera el archivo, la importación a la plataforma es manual</div>
    <div class="marco">
    {cuerpo}
    </div>
  </div>
</div>
</body></html>'''



def portada(error: str = "") -> str:
    aviso = f'<div class="err">{_h.escape(error)}</div>' if error else ""
    return _envoltura("Compilador GPM", f"""{aviso}

<form class="tarjeta" method="post" action="/extraer" enctype="multipart/form-data">
  <h2>Insumos del expediente</h2>
  <label><b>Nombre del Trámite</b> (Opcional si subes Análisis AS-IS)
    <em>Para identificarlo fácilmente si no adjuntas el documento AS-IS.</em>
    <input type="text" name="nombre_tramite" placeholder="Ej. Acceso a la Información"></label>
    
  <label><b>1. Análisis AS-IS</b>
    <em>De ahí salen el nombre, la dependencia, la homoclave y la ficha RUTS.</em>
    <div class="dropzone" id="dz1">
      <div class="dropzone-text" id="dt1">Arrastra tu archivo aquí o <span>haz clic para examinar</span></div>
      <input type="file" name="as_is" accept=".md" onchange="document.getElementById('dt1').innerText = this.files[0].name">
    </div>
  </label>
  
  <label><b>Propuesta TO-BE</b>
    <em>De su diagrama Mermaid sale el flujo: tareas, compuertas y actores.</em>
    <div class="dropzone" id="dz2">
      <div class="dropzone-text" id="dt2">Arrastra tu archivo aquí o <span>haz clic para examinar</span></div>
      <input type="file" name="to_be" accept=".md" onchange="document.getElementById('dt2').innerText = this.files[0].name">
    </div>
  </label>
  
  <label><b>Diccionario de Datos</b> <span style="color:var(--alerta)">— obligatorio</span>
    <em>De ahí salen las pantallas y los campos. Sin él no hay nada que compilar. <a href="/descargar-plantilla" style="color:var(--guinda);text-decoration:none;font-weight:bold;margin-left:5px">↓ Descargar plantilla de ejemplo</a></em>
    <div class="dropzone" id="dz3" style="border-color:var(--guinda)">
      <div class="dropzone-text" id="dt3">Arrastra tu archivo aquí o <span>haz clic para examinar</span></div>
      <input type="file" name="diccionario" accept=".md" required onchange="document.getElementById('dt3').innerText = this.files[0].name">
    </div>
  </label>
  
  <label><b>Vistas (HTML)</b>
    <em>Mockup de las pantallas propuesto por el equipo de Simplificación. Es referencia visual; no afecta la compilación.</em>
    <div class="dropzone" id="dz4">
      <div class="dropzone-text" id="dt4">Arrastra tu archivo aquí o <span>haz clic para examinar</span></div>
      <input type="file" name="vistas" accept=".html,.htm" onchange="document.getElementById('dt4').innerText = this.files[0].name">
    </div>
  </label>
  
  <div style="margin-top:2rem;display:flex;justify-content:space-between;align-items:center">
    <a href="/historial" style="font-size:0.95rem;color:var(--gris);text-decoration:none;font-weight:500;transition:color 0.2s" onmouseover="this.style.color='var(--guinda)'" onmouseout="this.style.color='var(--gris)'">Ver historial de trámites procesados</a>
    <button type="submit">Extraer manifiesto →</button>
  </div>
  
  <script>
    document.querySelectorAll('.dropzone').forEach(dz => {{
      dz.addEventListener('dragover', e => {{ e.preventDefault(); dz.classList.add('dragover'); }});
      dz.addEventListener('dragleave', e => {{ e.preventDefault(); dz.classList.remove('dragover'); }});
      dz.addEventListener('drop', e => {{ dz.classList.remove('dragover'); }});
    }});
  </script>
</form>

<p class="nota">La herramienta <strong>propone</strong>; no adivina. Lo que no puede derivar de los
insumos lo reporta como hueco para que una persona lo resuelva antes de compilar.</p>""", 1)


def revision(m, huecos, problemas, estimacion, sid: str, tiene_vistas: bool = False) -> str:
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
    bloque_huecos = f'<form method="POST" action="/resolver/{e(sid)}">'
    
    # Construir diccionarios para traducir IDs técnicos a nombres amigables
    mapa_actores = {a.id: a.nombre for a in m.actores}
    opciones_actores = "".join(f'<option value="{e(id)}">{e(nombre)}</option>' for id, nombre in mapa_actores.items())
    
    mapa_campos = {c.nombre: c.etiqueta or c.nombre for p in m.pantallas for c in p.campos}
    opciones_campos = "".join(f'<option value="{e(nombre)}">{e(etiqueta)}</option>' for nombre, etiqueta in mapa_campos.items())
    
    mapa_tareas = {t.id: t.nombre for t in m.flujo.tareas}

    for nivel in NIVELES:
        grupo = [h for h in huecos if h.nivel == nivel]
        if not grupo:
            continue
        titulo, nota, color = _ROTULO[nivel]
        
        lis = ""
        for h in grupo:
            # Renderizado interactivo y amigable para huecos específicos
            if h.codigo == "MMD-03":
                nombre_tarea = mapa_tareas.get(h.ubicacion, h.ubicacion)
                texto_amigable = f"La tarea <b>«{e(nombre_tarea)}»</b> no tiene responsable asignado."
                control = f'<br><select name="mmd03_{e(h.ubicacion)}" style="margin-top:0.5rem;padding:0.4rem;border-radius:4px;border:1px solid #ccc;font-size:0.9rem;width:100%;max-width:300px"><option value="">(Selecciona quién hace esto...)</option>{opciones_actores}</select>'
            elif h.codigo == "META-01":
                texto_amigable = "Falta el <b>tiempo de respuesta</b> que se le promete al ciudadano."
                control = f'<br><input type="text" name="meta01" placeholder="Ej. 5 días hábiles" style="margin-top:0.5rem;padding:0.4rem;border-radius:4px;border:1px solid #ccc;font-size:0.9rem;width:100%;max-width:300px">'
            elif h.codigo == "META-02":
                texto_amigable = "Falta indicar qué <b>Dependencia o Secretaría</b> atiende este trámite."
                control = f'<br><input type="text" name="meta02" placeholder="Ej. Dirección General de Tránsito" style="margin-top:0.5rem;padding:0.4rem;border-radius:4px;border:1px solid #ccc;font-size:0.9rem;width:100%;max-width:300px">'
            elif h.codigo == "API-03":
                etiqueta_campo = mapa_campos.get(h.ubicacion, h.ubicacion)
                texto_amigable = f"El campo <b>«{e(etiqueta_campo)}»</b> es un catálogo dinámico, pero no sabemos de qué otro campo depende para cargar sus datos."
                control = f'<br><select name="api03_{e(h.ubicacion)}" style="margin-top:0.5rem;padding:0.4rem;border-radius:4px;border:1px solid #ccc;font-size:0.9rem;width:100%;max-width:300px"><option value="">(Depende de lo que elija en...)</option>{opciones_campos}</select>'
            elif h.codigo == "INS-04":
                texto_amigable = f"<b style='color:var(--alerta)'>¡Alerta de archivos mezclados!</b><br>{e(h.mensaje)}"
                control = ""
            else:
                texto_amigable = f"{(e(h.ubicacion) + ': ') if h.ubicacion else ''}{e(h.mensaje)}"
                control = ""
                
            lis += (
                f"<li style='margin-bottom:1.25rem; background: var(--suave); padding: 1rem; border-radius: var(--radio-peq); border: 1px solid var(--linea);'>"
                f"<div style='font-size:0.8rem; color:var(--gris); margin-bottom:0.25rem; font-family:monospace'>Código interno: {e(h.codigo)}</div>"
                f"{texto_amigable}"
                f"{(' → <b>' + e(h.propuesta) + '</b>') if h.propuesta else ''}"
                f"{control}</li>"
            )
            
        abierto = " open" if nivel != "por_confirmar" else ""
        bloque_huecos += (
            f'<details class="huecos"{abierto} style="border-left:4px solid {color}">'
            f"<summary><b>{len(grupo)}</b> {titulo} — {nota}</summary>"
            f"<ul style='list-style:none;padding-left:0;margin-top:1.5rem'>{lis}</ul></details>"
        )
        
    # Botón flotante para guardar cambios si hay resolubles
    if any(h.codigo in ("MMD-03", "META-01", "META-02", "API-03") for h in huecos):
        bloque_huecos += (
            f'<div style="text-align:right; margin-bottom:1.5rem;">'
            f'<button type="submit" style="background:var(--verde);border-color:var(--verde)">Guardar y Recompilar</button>'
            f'</div>'
        )
    bloque_huecos += "</form>"

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

<div class="tarjeta" id="descargas">
  <h2>Salidas y Descargas (Paso 4)</h2>
  <a class="btn" href="/aprobacion/{e(sid)}">Documento de aprobación</a><br>
  <a class="btn" href="/simulador/{e(sid)}">Recorrer el trámite</a>
  <a class="btn" href="/descargar/{e(sid)}/manifiesto">Manifiesto YAML</a><br>
  <div style="margin-top:1rem;display:flex;gap:1rem;flex-wrap:wrap;">
      <a class="btn p" href="/descargar/{e(sid)}/gpm" style="background:var(--verde);border-color:var(--verde)">Archivo .gpm (Producción)</a>
      <a class="btn p" href="/descargar/{e(sid)}/gpm-pruebas" title="Agrupa todas las pantallas en una sola tarea inicial para revisión visual rápida">Archivo .gpm (Modo Pruebas / Test UI)</a>
  </div>
  {'<br><a class="btn" href="/vistas/' + e(sid) + '" target="_blank">Ver vistas (HTML) ↗</a>' if tiene_vistas else ''}
</div>

<p class="nota">El flujo propuesto es <strong>lineal</strong>, una tarea por pantalla. Las
compuertas del diagrama TO-BE se cuentan y se reportan arriba, pero no se reproducen: hay que
ramificarlas a mano en el manifiesto. La importación a la plataforma también es manual.</p>""", 2, sid=sid)

def historial(archivos) -> str:
    lista = ""
    for a in archivos:
        lista += f'<li><a href="/revisar/{a["sid"]}"><strong>{_h.escape(a["nombre"])}</strong></a> - {_h.escape(a["dependencia"])} <a class="btn" href="/descargar/{a["sid"]}/gpm" style="margin-left:1rem;padding:0.2rem 0.5rem">Descargar .gpm</a></li>'
    
    if not lista:
        lista = '<li style="color:var(--gris)">Todavía no hay ningún trámite procesado.</li>'
    
    html = f"""
<div class="tarjeta">
  <h2>Historial de trámites procesados</h2>
  <ul style="line-height:2">
    {lista}
  </ul>
  <br>
  <a class="btn" href="/">← Volver al inicio</a>
</div>
"""
    return _envoltura("Historial GPM", html, 0)
