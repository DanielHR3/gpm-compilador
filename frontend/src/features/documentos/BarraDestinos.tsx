import type { ResumenDocumentos } from "@/lib/types";

import { ORDEN, colorDe, nombreDe } from "./destinos";

/**
 * Parte de un todo: cuantos documentos hay en cada destino. CSS y tokens, sin
 * libreria de graficas. La leyenda esta siempre y cada entrada lleva su
 * cuenta escrita: el color no es el unico portador.
 */
export default function BarraDestinos({ resumen }: { resumen: ResumenDocumentos }) {
  const tramos = ORDEN.map((d) => ({ destino: d, n: resumen.por_destino[d] ?? 0 })).filter(
    (t) => t.n > 0,
  );
  const total = tramos.reduce((s, t) => s + t.n, 0);
  if (total === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <div
        role="img"
        aria-label="Documentos por destino"
        className="flex h-7 w-full gap-0.5 overflow-hidden rounded-md"
      >
        {tramos.map((t) => (
          <div
            key={t.destino}
            title={`${nombreDe(t.destino)}: ${t.n}`}
            style={{ width: `${(100 * t.n) / total}%`, background: colorDe(t.destino) }}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {tramos.map((t) => (
          <li
            key={t.destino}
            aria-label={`${nombreDe(t.destino)}: ${t.n}`}
            className="flex items-center gap-1.5"
          >
            <span
              aria-hidden
              className="inline-block size-2.5 rounded-sm"
              style={{ background: colorDe(t.destino) }}
            />
            {nombreDe(t.destino)} · {t.n}
          </li>
        ))}
      </ul>
    </div>
  );
}
