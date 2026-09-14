import { ArrowLeft, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "cn";
import type { Hueco } from "@/lib/types";

import { tituloDeCodigo } from "./lenguaje";

/** Misma clave estable que el resto del wizard. */
const clave = (h: Hueco): string => `${h.codigo}|${h.ubicacion}`;

const PUNTO: Record<Hueco["nivel"], string> = {
  bloqueante: "bg-destructive",
  falta_dato: "bg-amber-500",
  por_confirmar: "bg-muted-foreground/40",
};

/**
 * Índice de todos los huecos, para no perder el sitio en el modo foco.
 *
 * Es lo único que justifica recorrer 65 huecos de uno en uno: con la lista
 * completa el analista pierde la referencia en cuanto hace scroll; aquí ve
 * siempre dónde está y cuánto falta.
 */
export default function ModoFoco({
  huecos,
  actualClave,
  onIr,
  onAnterior,
  onSiguiente,
  indice,
  total,
}: {
  huecos: Hueco[];
  actualClave: string | null;
  onIr: (k: string) => void;
  onAnterior: () => void;
  onSiguiente: () => void;
  indice: number;
  total: number;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Hueco <span className="font-medium text-foreground">{indice + 1}</span>{" "}
          de {total}
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onAnterior}
            disabled={indice === 0}
          >
            <ArrowLeft aria-hidden className="size-3.5" />
            Anterior
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onSiguiente}
            disabled={indice >= total - 1}
          >
            Siguiente
            <ArrowRight aria-hidden className="size-3.5" />
          </Button>
        </div>
      </div>

      <nav
        aria-label="Todos los huecos"
        className="flex max-h-40 flex-wrap gap-1 overflow-y-auto rounded-lg border border-border bg-card p-2"
      >
        {huecos.map((h, i) => {
          const k = clave(h);
          const esActual = k === actualClave;
          return (
            <button
              key={k}
              type="button"
              aria-current={esActual ? "true" : undefined}
              title={`${i + 1}. ${tituloDeCodigo(h.codigo)} — ${h.ubicacion}`}
              onClick={() => onIr(k)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors",
                esActual
                  ? "bg-primary font-semibold text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "size-1.5 shrink-0 rounded-full",
                  esActual ? "bg-primary-foreground" : PUNTO[h.nivel],
                )}
              />
              {i + 1}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
