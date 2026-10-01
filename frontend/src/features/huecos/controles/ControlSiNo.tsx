import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Hueco } from "@/lib/types";

import { pistaDeCodigo } from "../lenguaje";

import DetalleTecnico from "./DetalleTecnico";

/**
 * Control para `META-07`: si el trámite aparece en el portal del ciudadano.
 *
 * Ningún insumo lo dice, así que el trámite se importaba siempre oculto y se
 * corregía a mano en la plataforma. Aquí se decide antes. Los dos botones
 * dicen lo que pasa, no «sí» y «no» a secas: la pregunta se lee en la tarjeta
 * y la respuesta tiene que entenderse sola. «Dejarlo así» no decide nada: deja
 * constancia de que alguien lo vio y el trámite sale oculto, como hasta ahora.
 */
export default function ControlSiNo({
  hueco,
  onConfirmar,
  onDejar,
  guardando = false,
}: {
  hueco: Hueco;
  onConfirmar: (valor: "si" | "no") => void | Promise<void>;
  onDejar: () => void | Promise<void>;
  /** Lo controla `TarjetaHueco` via `useAccion`: cierra la puerta al doble envio. */
  guardando?: boolean;
}) {
  const pista = pistaDeCodigo(hueco.codigo);

  return (
    <div className="flex flex-col gap-3">
      {pista ? (
        <p className="text-sm text-muted-foreground">{pista.instruccion}</p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button type="button" disabled={guardando} onClick={() => onConfirmar("si")}>
          <Eye aria-hidden className="size-4" />
          Sí, que aparezca en el portal
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={guardando}
          onClick={() => onConfirmar("no")}
        >
          <EyeOff aria-hidden className="size-4" />
          No, que quede oculto
        </Button>
      </div>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="self-start"
        disabled={guardando}
        onClick={() => onDejar()}
      >
        Dejarlo así
      </Button>

      <DetalleTecnico
        codigo={hueco.codigo}
        ubicacion={hueco.ubicacion}
        crudo={hueco.mensaje}
      />
    </div>
  );
}
