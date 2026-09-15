import { Check, Info } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Hueco } from "@/lib/types";

/**
 * Control para los huecos de nivel `por_confirmar`.
 *
 * Estos no se llenan: el compilador tomó una decisión razonable (la homoclave
 * la asigna GPM, un costo ausente se asume gratuito) y solo pide que alguien lo
 * mire. Hasta ahora la tarjeta no llevaba control alguno, así que enunciaba el
 * hecho y dejaba al analista sin saber si tenía que hacer algo —y sin forma de
 * cerrarlo: contaban como pendientes para siempre y el contador de progreso no
 * podía llegar nunca al total.
 */
export default function ControlConfirmar({
  hueco,
  onConfirmar,
  guardando = false,
}: {
  hueco: Hueco;
  onConfirmar: () => void | Promise<void>;
  guardando?: boolean;
}) {
  return (
    <div className="flex flex-col gap-3">
      <p className="flex items-start gap-2 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
        <Info aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
        <span>
          <span className="font-medium text-foreground">
            No tienes que llenar nada.
          </span>{" "}
          {hueco.propuesta
            ? `El compilador usará ${hueco.propuesta}. Confírmalo para cerrarlo.`
            : "Revísalo y confírmalo para cerrarlo de la lista."}
        </span>
      </p>
      <Button
        type="button"
        variant="outline"
        aria-busy={guardando}
        disabled={guardando}
        onClick={() => onConfirmar()}
        className="self-start"
      >
        <Check aria-hidden className="size-4" />
        {guardando ? "Guardando…" : "Entendido"}
      </Button>
    </div>
  );
}
