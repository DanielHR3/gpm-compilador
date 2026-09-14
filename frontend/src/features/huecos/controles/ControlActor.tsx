import { useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Hueco } from "@/lib/types";

import { nombreDeTarea, pistaDeCodigo } from "../lenguaje";

import BotonGuardar from "./BotonGuardar";
import DetalleTecnico from "./DetalleTecnico";

/** Un actor del manifiesto (`manifiesto.actores[]`). */
export type Actor = { id: string; nombre: string };

/**
 * Control para `MMD-03`: quién realiza una tarea del flujo.
 *
 * Es el hueco más repetido de los trámites grandes —Publicación trae 42—, así
 * que es donde más se nota la diferencia entre preguntar bien y volcar el
 * mensaje del compilador. La pregunta nombra la tarea limpia, sin el emoji, el
 * carril ni el paréntesis operativo que trae el diagrama; el mensaje crudo,
 * con su «no declara carril (:::clase)», se guarda en el detalle técnico.
 */
export default function ControlActor({
  hueco,
  actores,
  onConfirmar,
  guardando = false,
}: {
  hueco: Hueco;
  actores: Actor[];
  onConfirmar: (valor: string) => void | Promise<void>;
  /** Lo controla `TarjetaHueco` via `useAccion`: cierra la puerta al doble envio. */
  guardando?: boolean;
}) {
  const [valor, setValor] = useState<string>("");
  const items = Object.fromEntries(actores.map((a) => [a.id, a.nombre]));
  const tarea = nombreDeTarea(hueco.mensaje);
  const pista = pistaDeCodigo(hueco.codigo);

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-base font-semibold tracking-tight text-foreground">
        {tarea ? `¿Quién hace «${tarea}»?` : "¿Quién hace esta tarea?"}
      </h3>

      {pista ? (
        <p className="text-sm text-muted-foreground">{pista.instruccion}</p>
      ) : null}

      <Select
        items={items}
        value={valor || null}
        onValueChange={(v) => setValor(typeof v === "string" ? v : "")}
      >
        <SelectTrigger aria-label="Responsable de la tarea">
          <SelectValue placeholder="Elige un actor" />
        </SelectTrigger>
        <SelectContent>
          {actores.map((a) => (
            <SelectItem key={a.id} value={a.id}>
              {a.nombre}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <BotonGuardar
        guardando={guardando}
        disabled={!valor}
        onClick={() => onConfirmar(valor)}
        className="self-start"
      />

      <DetalleTecnico
        codigo={hueco.codigo}
        ubicacion={hueco.ubicacion}
        crudo={hueco.mensaje}
      />
    </div>
  );
}
