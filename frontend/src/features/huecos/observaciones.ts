import type { EstadoExpediente, Hueco } from "@/lib/types";

import { leerMensajeVisibilidad, redactarHueco, tituloDeCodigo } from "./lenguaje";

/**
 * El documento de observaciones que se le manda al equipo de Simplificacion.
 *
 * Hasta ahora esas observaciones se escribian a mano leyendo la pantalla. El
 * compilador ya sabe todo lo que hace falta y —desde que existe `redactarHueco`—
 * ya lo sabe decir en castellano, asi que el documento se arma con lo mismo que
 * lee el analista. No hay una segunda redaccion que mantener.
 *
 * Solo va lo que ELLOS pueden corregir: lo que se configura en la plataforma no
 * es trabajo suyo, y mandarselo obliga a adivinar que le toca a quien.
 */
type Responsable = "diccionario" | "to_be" | "plataforma";

/**
 * Quien resuelve cada codigo.
 *
 * Un codigo que no este aqui NO desaparece: cae en «Otros hallazgos». Es
 * preferible que sobre a que un hallazgo se pierda en silencio porque nadie se
 * acordo de clasificarlo al añadirlo.
 */
const RESPONSABLE: Record<string, Responsable> = {
  "DIC-00": "diccionario", "DIC-01": "diccionario", "DIC-02": "diccionario",
  "DIC-03": "diccionario", "DIC-04": "diccionario", "DIC-05": "diccionario",
  "DIC-06": "diccionario", "DIC-07": "diccionario", "DIC-08": "diccionario",
  "DIC-09": "diccionario",
  "DOC-02": "diccionario",
  // La plantilla ilegible la resuelve quien entrega el documento, no la DGT.
  "DOC-03": "diccionario",
  "META-01": "diccionario", "META-02": "diccionario", "META-03": "diccionario",
  "META-04": "diccionario",
  "API-03": "diccionario",
  "INS-02": "diccionario", "INS-03": "diccionario", "INS-04": "diccionario",

  "INS-01": "to_be", "MMD-01": "to_be", "MMD-02": "to_be", "MMD-03": "to_be",
  "MMD-04": "to_be", "FLU-01": "to_be", "FLU-02": "to_be",

  // GPM asigna la homoclave y el tipo de persona; el resto es configuracion.
  "META-05": "plataforma", "META-06": "plataforma",
  "API-01": "plataforma", "API-02": "plataforma", "API-04": "plataforma",
  "API-05": "plataforma", "DOC-04": "plataforma", "FLU-03": "plataforma",
};

const TITULO_SECCION: Record<Responsable, string> = {
  diccionario: "Lo que hay que corregir en el Diccionario de Datos",
  to_be: "Lo que hay que corregir en la Propuesta TO-BE",
  plataforma: "",
};

function nombreDelTramite(m: Record<string, unknown>): string {
  const t = (m as { tramite?: { nombre?: unknown } }).tramite?.nombre;
  return typeof t === "string" && t ? t : "trámite sin nombre";
}

/** `p7::campo` -> «Cargar Copia del Certificado»; lo que no sea pantalla, null. */
function nombreDePantalla(ubicacion: string, m: Record<string, unknown>): string | null {
  const id = ubicacion.split("::")[0];
  const pantallas = (m as { pantallas?: unknown }).pantallas;
  if (!Array.isArray(pantallas)) return null;
  for (const p of pantallas) {
    if (typeof p === "object" && p !== null && (p as Record<string, unknown>).id === id) {
      const n = (p as Record<string, unknown>).nombre;
      return typeof n === "string" ? n : id;
    }
  }
  return null;
}

function fechaLarga(hoy: Date): string {
  return hoy.toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" });
}

/** Un bloque por inconsistencia, agrupadas por la pantalla donde viven. */
function seccion(huecos: Hueco[], m: Record<string, unknown>): string[] {
  const porPantalla = new Map<string, Hueco[]>();
  for (const h of huecos) {
    const clave = nombreDePantalla(h.ubicacion, m) ?? "";
    porPantalla.set(clave, [...(porPantalla.get(clave) ?? []), h]);
  }
  const lineas: string[] = [];
  for (const [pantalla, lista] of porPantalla) {
    lineas.push(pantalla ? `### Pantalla «${pantalla}»` : "### Fuera de una pantalla concreta");
    lineas.push("");
    for (const h of lista) {
      const leido = leerMensajeVisibilidad(h.mensaje);
      lineas.push(`**${leido?.etiqueta ?? tituloDeCodigo(h.codigo)}**`);
      lineas.push("");
      lineas.push(redactarHueco(h));
      if (leido?.frase) {
        lineas.push("");
        lineas.push(`> En el Diccionario se escribió: «${leido.frase}»`);
      }
      lineas.push("");
    }
  }
  return lineas;
}

/**
 * Arma el documento en Markdown. Markdown y no PDF a proposito: el objetivo es
 * que Simplificacion lo INTEGRE en su documentacion, y un PDF se lee pero no se
 * integra.
 */
export function documentoDeObservaciones(
  estado: EstadoExpediente,
  hoy: Date = new Date(),
): string {
  const m = estado.manifiesto;
  const pendientes = estado.huecos;

  const grupos: Record<Responsable | "otros", Hueco[]> = {
    diccionario: [], to_be: [], plataforma: [], otros: [],
  };
  for (const h of pendientes) grupos[RESPONSABLE[h.codigo] ?? "otros"].push(h);

  const out: string[] = [
    `# Observaciones al expediente — ${nombreDelTramite(m)}`,
    "",
    `_Generado por el Compilador GPM el ${fechaLarga(hoy)}._`,
    "",
  ];

  const hayTrabajo =
    grupos.diccionario.length + grupos.to_be.length + grupos.otros.length > 0;

  if (!hayTrabajo) {
    out.push("No hay observaciones que requieran cambios en los documentos del expediente.");
    out.push("");
  }

  for (const r of ["diccionario", "to_be"] as const) {
    if (!grupos[r].length) continue;
    out.push(`## ${TITULO_SECCION[r]}  (${grupos[r].length})`, "");
    out.push(...seccion(grupos[r], m));
  }

  if (grupos.otros.length) {
    out.push(`## Otros hallazgos  (${grupos.otros.length})`, "");
    out.push(
      "Sin clasificar por responsable: conviene revisarlos con la Dirección de",
      "Gestión Tecnológica.",
      "",
    );
    out.push(...seccion(grupos.otros, m));
  }

  if (grupos.plataforma.length) {
    out.push("---", "");
    out.push(
      `_Además, ${grupos.plataforma.length} se configuran en la plataforma y no ` +
        "requieren cambios en sus documentos._",
      "",
    );
  }
  return out.join("\n");
}
