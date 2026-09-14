export type Resumen = {
  nombre: string | null;
  dependencia: string | null;
  pantallas: number;
  campos: number;
  /** Campos que solo se muestran si se cumple una condicion. */
  condicionales: number;
  tareas: number;
  actores: number;
  /** Conexiones del flujo que llevan una condicion: las bifurcaciones. */
  decisiones: number;
};

/** Lee una lista del manifiesto sin confiar en que exista ni sea lista. */
function lista(o: unknown, clave: string): unknown[] {
  const v = (o as Record<string, unknown> | undefined)?.[clave];
  return Array.isArray(v) ? v : [];
}

/**
 * Cuenta lo que el compilador entendio del expediente.
 *
 * Es el espejo del trabajo de quien documento el tramite: «de tu Diccionario
 * salieron 13 pantallas, 87 campos y 36 tareas». Sin esto, la unica forma de
 * saber si la herramienta leyo bien el documento era recorrer los huecos uno a
 * uno, y los huecos solo cuentan lo que fallo.
 *
 * El manifiesto no esta tipado en el frontend —viaja como dict— asi que cada
 * lectura es defensiva: un expediente a medio extraer no debe tumbar la
 * pantalla.
 */
export function resumirManifiesto(manifiesto: Record<string, unknown>): Resumen {
  const m = manifiesto ?? {};
  const pantallas = lista(m, "pantallas");
  const flujo = (m as { flujo?: Record<string, unknown> }).flujo ?? {};

  let campos = 0;
  let condicionales = 0;
  for (const p of pantallas) {
    for (const c of lista(p, "campos")) {
      campos += 1;
      if ((c as Record<string, unknown>)?.condicion_visible) condicionales += 1;
    }
  }

  const bruto = (m as { tramite?: { nombre?: unknown; dependencia?: unknown } })
    .tramite ?? {};
  // El compilador escribe «[por confirmar]» cuando no lo encontro: presentarlo
  // como si fuera el nombre del tramite seria mentir con formato bonito.
  const limpio = (v: unknown): string | null =>
    typeof v === "string" && v.trim() !== "" && !v.startsWith("[por confirmar")
      ? v
      : null;

  return {
    nombre: limpio(bruto.nombre),
    dependencia: limpio(bruto.dependencia),
    pantallas: pantallas.length,
    campos,
    condicionales,
    tareas: lista(flujo, "tareas").length,
    actores: lista(m, "actores").length,
    decisiones: lista(flujo, "conexiones").filter(
      (c) => (c as Record<string, unknown>)?.cuando != null,
    ).length,
  };
}
