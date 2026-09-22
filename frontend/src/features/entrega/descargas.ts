import { resumirManifiesto } from "@/features/huecos/resumen";
import type { EstadoExpediente } from "@/lib/types";

/**
 * Que se puede sacar de un expediente y que lo detiene.
 *
 * Aparte del componente porque la regla importa mas que la pintura: los dos
 * `.gpm` son lo unico que el linter cierra. Las observaciones y el manifiesto
 * salen siempre —y hacen mas falta justo cuando algo bloquea, porque son lo
 * que hay que mandarle a quien documento el tramite—.
 */

export type ClaveDescarga =
  | "gpm_produccion"
  | "gpm_pruebas"
  | "observaciones"
  | "manifiesto"
  | "vistas";

export type Descarga = {
  clave: ClaveDescarga;
  titulo: string;
  /** Una linea: para que sirve este archivo. */
  proposito: string;
  formato: string;
  /** Lo que lleva dentro, ya contado. */
  detalles: string[];
  bloqueada: boolean;
  /** Que la mantiene cerrada; `null` si esta abierta. */
  motivo: string | null;
};

const plural = (n: number, uno: string, varios: string) =>
  `${n} ${n === 1 ? uno : varios}`;

export function descargasDe(
  estado: EstadoExpediente,
  desbloqueado: boolean,
  motivoBloqueo: string,
): Descarga[] {
  const r = resumirManifiesto(estado.manifiesto);
  const contenido = [
    `${plural(r.pantallas, "pantalla", "pantallas")} · ${plural(r.campos, "campo", "campos")}`,
    `${plural(r.tareas, "tarea", "tareas")} · ${plural(r.decisiones, "decisión", "decisiones")}`,
  ];
  if (r.documentos > 0) {
    contenido.push(plural(r.documentos, "documento", "documentos"));
  }
  const cerrado = { bloqueada: !desbloqueado, motivo: desbloqueado ? null : motivoBloqueo };

  const lista: Descarga[] = [
    {
      clave: "gpm_produccion",
      titulo: ".gpm (producción)",
      proposito: "El archivo que se importa de verdad a la plataforma.",
      formato: "JSON",
      detalles: contenido,
      ...cerrado,
    },
    {
      clave: "gpm_pruebas",
      titulo: ".gpm (pruebas)",
      proposito:
        "El mismo trámite con datos de ejemplo ya capturados, para recorrerlo en la plataforma sin llenar nada.",
      formato: "JSON",
      detalles: contenido,
      ...cerrado,
    },
    {
      clave: "observaciones",
      titulo: "Observaciones",
      proposito:
        "Lo que hay que corregir en el expediente, redactado para mandárselo a quien lo documentó.",
      formato: "Markdown",
      detalles: [plural(estado.huecos.length, "inconsistencia", "inconsistencias")],
      bloqueada: false,
      motivo: null,
    },
    {
      clave: "manifiesto",
      titulo: "Manifiesto",
      proposito:
        "Lo que el compilador entendió del expediente, en texto legible. Sirve para revisarlo sin importar nada.",
      formato: "YAML",
      detalles: contenido,
      bloqueada: false,
      motivo: null,
    },
  ];

  if (estado.tieneVistas) {
    lista.push({
      clave: "vistas",
      titulo: "Vistas HTML",
      proposito: "Las pantallas de solo lectura tal como las dibuja el compilador.",
      formato: "HTML",
      detalles: [],
      bloqueada: false,
      motivo: null,
    });
  }
  return lista;
}
