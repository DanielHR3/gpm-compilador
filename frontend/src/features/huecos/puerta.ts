import type { Hueco } from "@/lib/types";

/** Identidad de un hueco: código y ubicación, la misma llave que `reconocidos.json`. */
export const clave = (h: Hueco): string => `${h.codigo}|${h.ubicacion}`;

/**
 * La puerta del linter, vista desde el cliente. Es la misma regla que
 * `nucleo/huecos.bloquean` en el servidor: los `bloqueante` siempre cierran;
 * los `falta_dato` solo mientras nadie los haya reconocido («lo configuro a
 * mano»); los `por_confirmar` nunca.
 *
 * Vive aparte del wizard porque el menú «Entrega» de la barra superior y el
 * panel de descargas tienen que leer exactamente el mismo conjunto.
 */
export function puertaDelLinter(
  huecos: Hueco[],
  reconocidos: Set<string>,
): { desbloqueado: boolean; bloqueantes: Hueco[] } {
  const bloqueantes = huecos.filter(
    (h) =>
      h.nivel === "bloqueante" ||
      (h.nivel === "falta_dato" && !reconocidos.has(clave(h))),
  );
  return { desbloqueado: bloqueantes.length === 0, bloqueantes };
}
