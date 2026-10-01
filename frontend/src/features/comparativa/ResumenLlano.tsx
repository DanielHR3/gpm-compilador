import { CircleHelp, Equal, ListChecks, Scale, TrendingDown, TrendingUp } from "lucide-react";

import type { LineaResumen } from "@/lib/types";

const ICONO = {
  elementos: ListChecks,
  baja: TrendingDown,
  igual: Equal,
  sube: TrendingUp,
  sin_comparar: Scale,
  sin_dato: CircleHelp,
} as const;

/**
 * Lo mismo que dicen las tarjetas, en frases. Las arma el servidor
 * (`armar._resumen`) con las cifras ya contadas: aqui no se redacta nada.
 */
export default function ResumenLlano({ lineas }: { lineas: LineaResumen[] }) {
  if (lineas.length === 0) return null;
  return (
    <ul aria-label="En pocas palabras" className="flex flex-col gap-1.5 border-t border-border/60 pt-3">
      {lineas.map((l) => {
        const Icono = ICONO[l.clase] ?? CircleHelp;
        return (
          <li key={l.clase} className="flex items-start gap-2 text-sm">
            <Icono aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span className="max-w-prose">{l.texto}</span>
          </li>
        );
      })}
    </ul>
  );
}
