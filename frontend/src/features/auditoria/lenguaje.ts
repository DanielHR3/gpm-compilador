import type { FilaAuditoria } from "@/lib/types";

/**
 * Cada acción de la bitácora, dicha como la leería quien audita, no como la
 * guarda el servidor. Misma idea que `huecos/lenguaje.ts`: el backend conserva
 * el código (`hueco.reconocer`), la pantalla lo traduce. Un código que no se
 * conoce se enseña tal cual, nunca se esconde.
 */
const CODIGO_AL_FINAL = /\s*\((\d{3})\)$/;

export type Evento = {
  /** Lo que hizo, en una frase. */
  frase: string;
  /** Código HTTP cuando el servidor rechazó la acción; null si salió bien. */
  rechazo: number | null;
  /** Fallo del servidor (500), el peor de los casos. */
  fallo: boolean;
};

const QUE: Record<string, (detalle: string) => string> = {
  "sesion.entrar": () => "Entró al asistente",
  "sesion.salir": () => "Salió del asistente",
  "sesion.fallo": () => "Intentó entrar con una contraseña incorrecta",
  "usuario.registro": () => "Registró una cuenta, pendiente de aprobación",
  "usuario.alta": (d) => `Dio de alta la cuenta ${d}`.trim(),
  "usuario.aprobar": (d) => `Aprobó la cuenta ${d}`.trim(),
  "usuario.baja": (d) => `Desactivó la cuenta ${d}`.trim(),
  "usuario.rol": (d) => `Cambió el rol de ${d}`.trim(),
  "recuperacion.pedir": () => "Pidió recuperar su contraseña",
  "recuperacion.restablecer": () => "Restableció su contraseña",
  "expediente.subir": () => "Subió los insumos de un expediente",
  "as_is.proponer": () => "Pidió al generador una propuesta desde el AS-IS",
  "propuesta.decidir": (d) => `Decidió sobre la propuesta (${d})`,
  "propuesta.subir": (d) => `Subió su propio ${d || "documento"} sobre la propuesta`,
  "hueco.resolver": (d) => `Resolvió la inconsistencia ${d}`.trim(),
  "hueco.reconocer": (d) => `Reconoció la inconsistencia ${d} («lo configuro a mano»)`.trim(),
  "propuesta_ia.decidir": (d) => `Decidió sobre una propuesta de IA (${d})`,
  "documentos.analizar": () => "Pidió al agente el análisis de documentos",
  "documentos.decidir": (d) => `Decidió el destino de un documento ${d}`.trim(),
  "comparativa.declarar": () => "Declaró una cifra de la comparativa",
  "comparativa.analizar": () => "Pidió al agente la comparativa",
  "comparativa.descartar": () => "Descartó un punto de mejora",
  "gpm.descargar": (d) => `Descargó el .gpm de ${d === "pruebas" ? "pruebas" : "producción"}`,
  "error.servidor": (d) => `Fallo del servidor: ${d}`,
};

export function redactarEvento(f: FilaAuditoria): Evento {
  const detalle = f.detalle ?? "";
  const m = CODIGO_AL_FINAL.exec(detalle);
  const codigo = m ? Number(m[1]) : null;
  const limpio = m ? detalle.slice(0, m.index) : detalle;
  const fallo = f.accion === "error.servidor" || codigo === 500;
  const redactor = QUE[f.accion];
  let frase = redactor ? redactor(limpio) : `${f.accion}${limpio ? ` (${limpio})` : ""}`;
  if (codigo !== null && !fallo) frase += ` — el servidor la rechazó (${codigo})`;
  return { frase, rechazo: codigo !== null && !fallo ? codigo : null, fallo };
}

/** «16 oct 2026, 12:05» en la hora de la máquina que lee. */
export function fechaCorta(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export type Persona = {
  usuario: string;
  dependencia: string;
  /** Del más reciente al más viejo, como llegan del servidor. */
  eventos: FilaAuditoria[];
  tramites: number;
  rechazos: number;
  fallos: number;
  ultima: string;
};

/** Una entrada por persona, en el orden en que aparece su acción más reciente. */
export function agruparPorPersona(filas: FilaAuditoria[]): Persona[] {
  const por = new Map<string, Persona>();
  for (const f of filas) {
    let p = por.get(f.usuario);
    if (!p) {
      p = { usuario: f.usuario, dependencia: f.dependencia, eventos: [], tramites: 0, rechazos: 0, fallos: 0, ultima: f.fecha };
      por.set(f.usuario, p);
    }
    p.eventos.push(f);
    if (!p.dependencia && f.dependencia) p.dependencia = f.dependencia;
    const ev = redactarEvento(f);
    if (ev.fallo) p.fallos++;
    else if (ev.rechazo !== null) p.rechazos++;
  }
  for (const p of por.values()) p.tramites = new Set(p.eventos.map((e) => e.sid).filter(Boolean)).size;
  return [...por.values()];
}
