/**
 * Escala secuencial de cinco pasos (`--viz-1` … `--viz-5` en index.css): un
 * solo tono, de claro a oscuro, validado contra las dos superficies. El cero
 * queda fuera de la rampa a proposito: «sin dato» no se pinta.
 */
export const PASOS = 5;

export function pasoDe(valor: number, maximo: number): number {
  if (maximo <= 0 || valor <= 0) return 0;
  return Math.max(1, Math.min(PASOS, Math.ceil((valor / maximo) * PASOS)));
}

/** Color de la celda para un paso; 0 es la superficie apagada. */
export function colorDe(paso: number): string {
  return paso === 0 ? "var(--muted)" : `var(--viz-${paso})`;
}

/** A partir del paso 4 el fondo es oscuro (o muy saturado) y el texto va en claro. */
export function tintaDe(paso: number): string {
  return paso >= 4 ? "var(--primary-foreground)" : "var(--foreground)";
}
