import { ChevronRight } from "lucide-react";

import type { Tramo } from "@/lib/rutas";

/** Donde esta la persona: camino y paso, arriba del contenido. */
export default function MigasDePan({ tramos }: { tramos: Tramo[] }) {
  return (
    <nav aria-label="Migas de pan" className="pb-4 text-sm text-muted-foreground">
      <ol className="flex flex-wrap items-center gap-1">
        {tramos.map((t, i) => {
          const ultimo = i === tramos.length - 1;
          return (
            <li key={`${t.etiqueta}-${i}`} className="flex items-center gap-1">
              {t.href && !ultimo ? (
                <a href={t.href} className="text-primary underline-offset-2 hover:underline">
                  {t.etiqueta}
                </a>
              ) : (
                <span
                  aria-current={ultimo ? "page" : undefined}
                  className={ultimo ? "font-medium text-foreground" : undefined}
                >
                  {t.etiqueta}
                </span>
              )}
              {!ultimo ? <ChevronRight aria-hidden className="size-4" /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
