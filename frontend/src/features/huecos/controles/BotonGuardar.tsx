import { Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Boton de confirmacion compartido por los controles del wizard.
 *
 * Centraliza el estado ocupado para que ningun control lo implemente a medias:
 * cambia la etiqueta, marca `aria-busy` (un lector de pantalla anuncia que la
 * peticion sigue en curso) y se inhabilita, que es la ultima barrera contra el
 * doble envio despues del candado de `useAccion`.
 */
export default function BotonGuardar({
  guardando = false,
  disabled = false,
  onClick,
  etiqueta = "Guardar",
  className,
}: {
  guardando?: boolean;
  disabled?: boolean;
  onClick: () => void;
  etiqueta?: string;
  className?: string;
}) {
  return (
    <Button
      type="button"
      aria-busy={guardando}
      disabled={disabled || guardando}
      onClick={onClick}
      className={className}
    >
      {guardando ? (
        <Loader2 aria-hidden className="size-4 animate-spin" />
      ) : (
        <Check aria-hidden className="size-4" />
      )}
      {guardando ? "Guardando…" : etiqueta}
    </Button>
  );
}
