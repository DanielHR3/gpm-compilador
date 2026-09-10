import { useState } from "react";

import { Button } from "@/components/ui/button";
import { camposDelManifiesto, ErrorApi, resolverDic08 } from "@/lib/api";
import type { Condicion, Hueco } from "@/lib/types";

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
  const [error, setError] = useState<ErrorApi | null>(null);
  const [guardando, setGuardando] = useState(false);
  const campos = camposDelManifiesto(manifiesto);

  const guardar = async () => {
    if (!condicion) return;
    setError(null);
    setGuardando(true);
    try {
      const resp = await resolverDic08(sid, hueco.ubicacion, condicion);
      onResuelto(resp);
    } catch (e) {
      if (e instanceof ErrorApi) {
        setError(e);
      } else {
        throw e;
      }
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <p>{hueco.mensaje}</p>
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
      >
        Guardar
      </Button>
    </div>
  );
}
