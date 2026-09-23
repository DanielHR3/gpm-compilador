import { nombreCorto } from "./codigos";

/**
 * Tres frases en palabras a partir de las cuentas, sin modelo de por medio:
 * lo que mas se repite, el pendiente mas comun y cuantos tramites son
 * complejos. Determinista, para que el equipo pueda fiarse de lo que dice.
 */
interface Entrada {
  total_tramites: number;
  requisitos: { nombre: string; tramites: number; porcentaje?: number }[];
  huecos: { codigo: string; tramites: number }[];
  niveles: { nivel: string; tramites: number }[];
}

function lista(nombres: string[]): string {
  if (nombres.length <= 1) return nombres.join("");
  return `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
}

export function resumenEnPalabras(d: Entrada): string[] {
  const total = d.total_tramites;
  if (total === 0) return [];
  if (total === 1) {
    return ["Todavía hay un solo trámite: las comparaciones aparecen cuando haya dos o más."];
  }
  const frases: string[] = [];
  const repetidos = d.requisitos.filter((r) => r.tramites >= 2);
  if (repetidos.length > 0) {
    const tope = repetidos[0].tramites;
    const punteros = repetidos.filter((r) => r.tramites === tope).slice(0, 3).map((r) => r.nombre);
    frases.push(
      punteros.length === 1
        ? `El documento que más se repite es ${punteros[0]}.`
        : `Los documentos que más se repiten son ${lista(punteros)}.`,
    );
  }
  if (d.huecos.length > 0) {
    const h = d.huecos[0];
    frases.push(`El pendiente más común es «${nombreCorto(h.codigo)}»: aparece en ${h.tramites} de ${total} trámites.`);
  }
  const complejos = d.niveles.find((n) => n.nivel === "Complejo")?.tramites ?? 0;
  if (complejos > 0) {
    frases.push(`${complejos} de ${total} trámites son complejos.`);
  }
  return frases;
}
