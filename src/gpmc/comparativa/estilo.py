"""Cabecera, pie y hoja de estilo comunes a los documentos descargables.

«Antes y despues» y «Documentos del tramite» se bajan, se abren sin red y se
imprimen; antes cada uno traia su CSS y se veian de otra familia que la SPA.
Aqui viven los colores del sistema de diseno (`frontend/src/tokens.css`), la
tipografia (Montserrat si esta instalada; nunca se carga de la red) y la
cabecera que dice de que tramite es, quien lo emitio y cuando.
"""
from datetime import date
from html import escape
from typing import Optional

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")

# `--brand-primary`, `--surface-app`, `--surface-card`, `--text-primary`,
# `--text-secondary`, `--border-default` y `--radius` de la SPA.
CSS = """
:root{--guinda:#A02142;--fondo:#f9fafb;--tarjeta:#ffffff;--texto:#111827;--texto2:#4b5563;
--borde:#d1d5db;--radio:8px}
*{box-sizing:border-box}
body{font-family:"Montserrat",system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--texto);
background:var(--fondo);margin:0;line-height:1.45}
main{max-width:64rem;margin:0 auto;padding:1.5rem 1.25rem 3rem}
.cabecera{border-top:6px solid var(--guinda);background:var(--tarjeta);border-bottom:1px solid var(--borde)}
.cabecera>div{max-width:64rem;margin:0 auto;padding:1rem 1.25rem;display:flex;flex-wrap:wrap;
align-items:baseline;justify-content:space-between;gap:.5rem 1.5rem}
.cabecera .marca{font-weight:700;color:var(--guinda);font-size:.875rem;letter-spacing:.02em}
.cabecera .fecha{color:var(--texto2);font-size:.8125rem}
h1{font-size:1.5rem;margin:0 0 .25rem;letter-spacing:-.01em}
h2{font-size:1.05rem;margin:2rem 0 .75rem;border-bottom:1px solid var(--borde);padding-bottom:.25rem;color:var(--guinda)}
.sub{color:var(--texto2);font-size:.875rem;margin:0 0 1rem}
.veredicto{border-left:4px solid var(--guinda);background:var(--tarjeta);border:1px solid var(--borde);
border-left-width:4px;border-left-color:var(--guinda);border-radius:var(--radio);padding:.75rem 1rem;margin:1rem 0}
.veredicto strong{display:block;font-size:1.1rem}
.titular{font-size:1.35rem;font-weight:700;margin:1.25rem 0}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:.75rem}
.tarjeta{background:var(--tarjeta);border:1px solid var(--borde);border-radius:var(--radio);padding:.75rem;break-inside:avoid}
.tarjeta h3{font-size:.875rem;margin:0 0 .5rem}
.par{display:flex;gap:1rem;font-size:.8125rem}.par div{flex:1}
.cifra{font-size:1.25rem;font-weight:700;display:block}
.origen,.rotulo{color:var(--texto2);font-size:.6875rem;text-transform:uppercase;letter-spacing:.09em;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.cambio{font-weight:700;margin-top:.5rem;font-size:.875rem}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}
ol,ul{padding-left:1.25rem;margin:0}li{margin:.25rem 0;font-size:.875rem}
.nota{color:var(--texto2);font-size:.8125rem;margin:.35rem 0 0}
.resumen{padding-left:1.25rem;margin:.5rem 0 1rem}.resumen li{font-size:.9375rem}
.evidencia{margin:.5rem 0 0;padding-left:1rem;border-left:2px solid var(--borde)}
.evidencia li{list-style:none;font-size:.75rem;color:var(--texto2);margin:.2rem 0}
.motivo{font-size:.8125rem;margin:.5rem 0 0}
.tarjeta p{margin:.35rem 0;font-size:.8125rem}
blockquote{margin:.5rem 0;padding-left:.6rem;border-left:2px solid var(--borde);font-size:.8125rem}
.pie{max-width:64rem;margin:0 auto;padding:0 1.25rem 2rem;color:var(--texto2);font-size:.75rem;
border-top:1px solid var(--borde);padding-top:.75rem}
@media (max-width:40rem){.dos{grid-template-columns:1fr}}
@media print{body{background:#fff}main{padding:0}h2{break-after:avoid}.cabecera{border-top-width:4px}}
"""


def e(texto) -> str:
    return escape(str(texto if texto is not None else ""), quote=True)


def fecha_larga(d: date) -> str:
    return f"{d.day} de {_MESES[d.month - 1]} de {d.year}"


def pagina(clase: str, tramite: str, cuerpo: str, uso: str,
           hoy: Optional[date] = None) -> str:
    """Una pagina completa: cabecera institucional, `cuerpo` tal cual y pie.

    `clase` es el tipo de documento («Antes y despues»); `uso`, la linea que
    dice para quien es. `cuerpo` ya viene escapado por quien lo arma.
    """
    hoy = hoy or date.today()
    titulo = f"{clase} — {tramite}" if tramite else clase
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{e(titulo)}</title><style>{CSS}</style></head><body>"
        '<header class="cabecera"><div>'
        '<span class="marca">Compilador GPM · Simplificación Administrativa</span>'
        f'<span class="fecha">{e(clase)} · {fecha_larga(hoy)}</span>'
        "</div></header>"
        f"<main>{cuerpo}</main>"
        f'<footer class="pie">{e(uso)} Generado por el Compilador GPM el {fecha_larga(hoy)}. '
        "Cada cifra dice de dónde salió; lo propuesto por el agente está rotulado.</footer>"
        "</body></html>"
    )
