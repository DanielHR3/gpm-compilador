import { useState } from "react";
import { Check, Quote } from "lucide-react";

import { Button } from "@/components/ui/button";
import { camposDelManifiesto, resolverDic08 } from "@/lib/api";
import type { Condicion, Hueco } from "@/lib/types";

import { useAccion } from "../useAccion";

import ConstructorRegla from "./ConstructorRegla";

/**
 * Control para `DIC-08` (visibilidad no interpretable): muestra la frase
 * cruda del `Diccionario` que el parser no pudo traducir (dentro de
 * `hueco.mensaje`) y un `ConstructorRegla` para armarla a mano. "Guardar"
 * queda inhabilitado mientras `ConstructorRegla` no haya emitido una
 * `Condicion` valida.
 */
export default function ControlVisibilidad({
  hueco,
  sid,
  manifiesto,
  onResuelto,
}: {
  hueco: Hueco;
  sid: string;
  manifiesto: Record<string, unknown>;
  onResuelto: (resp: { manifiesto: Record<string, unknown>; huecos: Hueco[] }) => void;
}) {
  const [condicion, setCondicion] = useState<Condicion | null>(null);
  const { ejecutar, guardando, error } = useAccion();
  const campos = camposDelManifiesto(manifiesto);

  const guardar = async () => {
    if (!condicion) return;
    await ejecutar(async () => {
      const resp = await resolverDic08(sid, hueco.ubicacion, condicion);
      onResuelto(resp);
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
        <Quote aria-hidden className="mt-0.5 size-4 shrink-0 text-primary/60" />
        <p>{hueco.mensaje}</p>
      </div>
      <p className="text-sm font-medium">
        Arma la condición que decide cuándo se muestra este campo:
      </p>
      <ConstructorRegla campos={campos} value={null} onChange={setCondicion} />
      {error ? (
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <p>{error.message}</p>
        </div>
      ) : null}
      <Button
        type="button"
        disabled={!condicion || guardando}
        onClick={guardar}
        className="self-start"
      >
        <Check aria-hidden className="size-4" />
        Guardar
      </Button>
    </div>
  );
}
