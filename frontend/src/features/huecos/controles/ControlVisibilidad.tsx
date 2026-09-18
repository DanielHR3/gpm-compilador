import { useState } from "react";
import { Check, Eye, Lightbulb, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { camposDelManifiesto, resolverDic08 } from "@/lib/api";
import type { Condicion, Hueco, Propuesta } from "@/lib/types";

import {
  describirCondicion,
  leerMensajeVisibilidad,
  pistaDeCodigo,
} from "../lenguaje";
import { useAccion } from "../useAccion";

import ConstructorRegla from "./ConstructorRegla";
import DetalleTecnico from "./DetalleTecnico";

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
 *
 * Con `propuesta` (Fase 2, generador de IA) el constructor arranca prellenado
 * y aparecen Aceptar / Corregir / Descartar con la cita de dónde salió. La
 * escritura sigue siendo `resolverDic08`; `onDecision` solo anota, después.
 */
export default function ControlVisibilidad({
  hueco,
  sid,
  manifiesto,
  onResuelto,
  propuesta = null,
  onDecision,
}: {
  hueco: Hueco;
  sid: string;
  manifiesto: Record<string, unknown>;
  onResuelto: (resp: { manifiesto: Record<string, unknown>; huecos: Hueco[] }) => void;
  /** Propuesta del generador de IA para este campo, si la hay. */
  propuesta?: Propuesta | null;
  /** Anota qué se hizo con la propuesta. Se llama DESPUÉS de resolver. */
  onDecision?: (
    decision: "aceptada" | "corregida" | "descartada",
    condicionFinal?: Condicion,
  ) => Promise<void>;
}) {
  // Con propuesta el constructor arranca prellenado; `descartada` la retira y
  // vuelve al modo manual de siempre.
  const [activa, setActiva] = useState<Propuesta | null>(propuesta);
  const [condicion, setCondicion] = useState<Condicion | null>(propuesta?.condicion ?? null);
  const [editando, setEditando] = useState(false);
  const { ejecutar, guardando, error } = useAccion();
  const campos = camposDelManifiesto(manifiesto);
  const leido = leerMensajeVisibilidad(hueco.mensaje);
  const frase = describirCondicion(condicion, campos);
  const pista = pistaDeCodigo(hueco.codigo);

  const resolver = async (cond: Condicion) => {
    const resp = await resolverDic08(sid, hueco.ubicacion, cond);
    onResuelto(resp);
  };

  const guardar = async () => {
    if (!condicion) return;
    await ejecutar(async () => {
      await resolver(condicion);
      // Si venía de una propuesta y se editó, es "corregida". Si el registro
      // falla, la resolución ya quedó: no se deshace nada.
      if (activa && onDecision) await onDecision("corregida", condicion);
    });
  };

  const aceptar = async () => {
    if (!activa?.condicion) return;
    const cond = activa.condicion;
    await ejecutar(async () => {
      await resolver(cond);
      if (onDecision) await onDecision("aceptada", undefined);
    });
  };

  const descartar = async () => {
    if (!activa) return;
    if (onDecision) await onDecision("descartada", undefined);
    setActiva(null);
    setCondicion(null);
    setEditando(false);
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
      {/* `key`: ConstructorRegla solo lee `value` al montar. Al descartar la
          propuesta se remonta vacío en vez de conservar las filas prellenadas. */}
      <ConstructorRegla
        key={activa ? activa.id : "manual"}
        campos={campos}
        value={activa ? activa.condicion : null}
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

      {activa ? (
        <div className="flex flex-col gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm">
          <p className="flex items-start gap-2">
            <Sparkles aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
            <span>
              <span className="font-medium text-foreground">Propuesto a partir de: </span>
              «{activa.cita.texto}» — {activa.cita.fuente} · {activa.cita.pantalla_nombre} ·{" "}
              {activa.cita.campo}
              <span className="ml-2 text-xs text-muted-foreground">
                (confianza {activa.confianza})
              </span>
            </span>
          </p>
          {!editando ? (
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={aceptar} disabled={guardando} aria-busy={guardando}>
                <Check aria-hidden className="size-4" />
                Aceptar
              </Button>
              <Button type="button" variant="outline" onClick={() => setEditando(true)} disabled={guardando}>
                Corregir
              </Button>
              <Button type="button" variant="ghost" onClick={descartar} disabled={guardando}>
                <X aria-hidden className="size-4" />
                Descartar
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <p>{error.message}</p>
        </div>
      ) : null}

      {!activa || editando ? (
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
      ) : null}

      <DetalleTecnico
        codigo={hueco.codigo}
        ubicacion={hueco.ubicacion}
        crudo={leido ? leido.frase : hueco.mensaje}
        extra={
          leido ? (
            <div className="flex gap-2">
              <dt className="font-medium">Nombre interno:</dt>
              <dd className="font-mono">{leido.interno}</dd>
            </div>
          ) : null
        }
      />
    </div>
  );
}
