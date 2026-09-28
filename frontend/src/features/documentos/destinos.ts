import type { Destino, DestinoOSin, DocumentoTramite } from "@/lib/types";

/**
 * Como se dice cada destino. Aparte de los componentes porque la pagina
 * descargable dice lo mismo desde el servidor
 * (`comparativa/pagina_documentos.py`): si un nombre cambia aqui, cambia alla.
 */

/** Orden de lectura: primero lo que el ciudadano dejo de traer. */
export const ORDEN: DestinoOSin[] = ["elimina", "consulta", "sistema", "conserva", "sin_destino"];
export const DESTINOS: Destino[] = ["elimina", "consulta", "sistema", "conserva"];

const NOMBRE: Record<DestinoOSin, string> = {
  elimina: "Se elimina",
  consulta: "Se sustituye por consulta en línea",
  sistema: "Lo genera el sistema",
  conserva: "Se conserva",
  sin_destino: "Sin destino",
};

export function nombreDe(d: DestinoOSin): string {
  return NOMBRE[d];
}

/** El color sigue al destino, nunca a su posicion ni a su cuenta. */
export function colorDe(d: DestinoOSin): string {
  return d === "sin_destino" ? "var(--muted-foreground)" : `var(--dest-${d})`;
}

const ESTADO: Record<DocumentoTramite["estado"], string> = {
  propuesto: "Propuesto, sin revisar",
  aceptado: "Aceptado",
  corregido: "Corregido por una persona",
};

export function estadoEnPalabras(e: DocumentoTramite["estado"]): string {
  return ESTADO[e];
}

const VEREDICTO: Record<string, string> = {
  cita_inventada: "La frase que citó el agente no está en el TO-BE.",
  campo_inventado: "El agente nombró un campo que no existe en el trámite.",
  evidencia_insuficiente: "Lo que citó el agente no respalda ese destino.",
  sin_fundamento: "El agente dice que se elimina, pero el TO-BE no lo dice.",
  destino_invalido: "El agente propuso un destino que no existe.",
  campo_repetido: "Ese campo ya respalda a otro documento.",
  omitido_por_el_modelo: "El agente no lo revisó; está en el AS-IS.",
  campo_desaparecido: "El campo en que se apoyaba ya no existe en el trámite.",
};

export function veredictoEnPalabras(v: string): string {
  if (!v) return "";
  return VEREDICTO[v] ?? v;
}
