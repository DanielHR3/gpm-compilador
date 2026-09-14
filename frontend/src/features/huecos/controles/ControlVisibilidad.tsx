import { useState } from "react";
import { Check, Eye, Lightbulb } from "lucide-react";

import { Button } from "@/components/ui/button";
import { camposDelManifiesto, resolverDic08 } from "@/lib/api";
import type { Condicion, Hueco } from "@/lib/types";

import {
  describirCondicion,
  leerMensajeVisibilidad,
  pistaDeCodigo,
} from "../lenguaje";
import { useAccion } from "../useAccion";

import ConstructorRegla from "./ConstructorRegla";

/**
 * Control para `DIC-08`: el Diccionario declaró una condición de visibilidad
 * que el parser no supo traducir, y hay que armarla a mano.
 *
 * La tarjeta está escrita para quien documenta el trámite, no para quien
 * programa el compilador: encabeza con una pregunta, nombra el campo por la
 * etiqueta que ve el ciudadano y lee la regla armada como frase para que se
 * pueda comprobar. El código del hueco, el nombre interno del campo y la frase
 * cruda del Diccionario siguen ahí, plegados: hacen falta para rastrear y
 * reportar, pero no para decidir.
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
  const leido = leerMensajeVisibilidad(hueco.mensaje);
  const frase = describirCondicion(condicion, campos);
  const pista = pistaDeCodigo(hueco.codigo);

  const guardar = async () => {
    if (!condicion) return;
    await ejecutar(async () => {
      const resp = await resolverDic08(sid, hueco.ubicacion, condicion);
      onResuelto(resp);
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-base font-semibold tracking-tight text-foreground">
        ¿Cuándo debe verse{" "}
        {leido ? `«${leido.etiqueta}»` : "este campo"}?
      </h3>

      {pista ? (
        <div className="flex flex-col gap-1.5 text-sm text-muted-foreground">
          <p>{pista.instruccion}</p>
          {pista.ejemplo ? (
            <p className="flex items-start gap-2 rounded-md border border-dashed border-border px-3 py-2">
              <Lightbulb aria-hidden className="mt-0.5 size-3.5 shrink-0 text-secondary" />
              <span>
                <span className="font-medium text-foreground">Por ejemplo: </span>
                {pista.ejemplo}
              </span>
            </p>
          ) : null}
        </div>
      ) : null}

      <p className="text-sm text-muted-foreground">Muéstralo solo cuando:</p>
      <ConstructorRegla
        campos={campos}
        value={null}
        onChange={setCondicion}
        marcadorValor={pista?.marcador}
      />

      {frase ? (
        <p className="flex items-start gap-2 rounded-lg bg-muted/50 p-3 text-sm text-foreground">
          <Eye aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
          <span>
            Quedará así: el campo se muestra solo si <strong>{frase}</strong>.
          </span>
        </p>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <p>{error.message}</p>
        </div>
      ) : null}

      <Button
        type="button"
        aria-busy={guardando}
        disabled={!condicion || guardando}
        onClick={guardar}
        className="self-start"
      >
        <Check aria-hidden className="size-4" />
        {guardando ? "Guardando…" : "Guardar"}
      </Button>

      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer select-none underline-offset-2 hover:underline">
          Ver detalle técnico
        </summary>
        <dl className="mt-2 flex flex-col gap-1 rounded-md bg-muted/40 p-3">
          <div className="flex gap-2">
            <dt className="font-medium">Código:</dt>
            <dd className="font-mono">{hueco.codigo}</dd>
          </div>
          {leido ? (
            <div className="flex gap-2">
              <dt className="font-medium">Nombre interno:</dt>
              <dd className="font-mono">{leido.interno}</dd>
            </div>
          ) : null}
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium">Se escribió en el Diccionario:</dt>
            <dd className="italic">{leido ? leido.frase : hueco.mensaje}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}
