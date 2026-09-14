import { useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Hueco } from "@/lib/types";

import BotonGuardar from "./BotonGuardar";

/** Un actor del manifiesto (`manifiesto.actores[]`). */
export type Actor = { id: string; nombre: string };

/**
 * Control para `MMD-03`: elige el actor responsable de una tarea. El valor que
 * viaja a la API es el `id` del actor; la etiqueta visible es su `nombre`.
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

  return (
    <div className="flex flex-col gap-2">
      <Select
        items={items}
        value={valor || null}
        onValueChange={(v) => setValor(typeof v === "string" ? v : "")}
      >
        <SelectTrigger aria-label={hueco.mensaje || "Actor responsable"}>
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
      />
    </div>
  );
}
