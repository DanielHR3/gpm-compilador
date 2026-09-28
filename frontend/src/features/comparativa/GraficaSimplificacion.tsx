import type { ComparativaOut } from "@/lib/types";

import { anchoBarra, textoCambio, textoGlobal } from "./formato";

/**
 * Porcentaje de simplificacion: una pareja de barras por metrica que tiene
 * numero en los dos lados, y la cifra global arriba con su base.
 *
 * CSS y tokens, como el tablero: sin libreria de graficas ni CDN. El par
 * `--cmp-antes` / `--cmp-despues` (de la rampa `--viz-*`, validado en claro y
 * oscuro) distingue los lados, pero cada barra lleva su valor escrito y su
 * rotulo: el color no es el unico portador.
 */
export default function GraficaSimplificacion({ comparativa }: { comparativa: ComparativaOut }) {
  const comparables = comparativa.metricas.filter(
    (m) => m.porcentaje !== null && m.antes.numero !== null && m.despues.numero !== null,
  );

  return (
    <div className="flex flex-col gap-4">
      <p className="text-2xl font-bold leading-tight tracking-tight text-primary">
        {textoGlobal(comparativa)}
      </p>
      {comparables.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Declara el antes y el después de las métricas que faltan para ver la gráfica.
        </p>
      ) : (
        <ul className="flex flex-col gap-4">
          {comparables.map((m) => {
            const antes = m.antes.numero as number;
            const despues = m.despues.numero as number;
            const tope = Math.max(antes, despues);
            return (
              <li key={m.clave} aria-label={m.nombre} className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0 truncate font-medium">{m.nombre}</span>
                  <span className="shrink-0 font-semibold tabular-nums">
                    {textoCambio(m.porcentaje as number)}
                  </span>
                </div>
                {([
                  ["Antes", antes, m.antes.texto, "var(--cmp-antes)"],
                  ["Después", despues, m.despues.texto, "var(--cmp-despues)"],
                ] as const).map(([rotulo, valor, texto, color]) => (
                  <div key={rotulo} className="flex items-center gap-2 text-xs">
                    <span className="w-14 shrink-0 text-muted-foreground">{rotulo}</span>
                    <div
                      role="meter"
                      aria-label={`${rotulo}: ${m.nombre}`}
                      aria-valuemin={0}
                      aria-valuemax={tope}
                      aria-valuenow={valor}
                      className="h-3 flex-1 overflow-hidden rounded-full bg-muted"
                    >
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${anchoBarra(valor, tope)}%`, backgroundColor: color }}
                      />
                    </div>
                    <span className="w-24 shrink-0 tabular-nums">{texto}</span>
                  </div>
                ))}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
