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

/** Un campo de pantalla (`manifiesto.pantallas[].campos[]`). */
export type Campo = { nombre: string };

/**
 * Control para `API-03`: elige el campo padre del que cuelga un catalogo
 * dependiente. El valor que viaja a la API es el `nombre` del campo.
 */
export default function ControlCampoPadre({
  hueco,
  campos,
  onConfirmar,
  guardando = false,
}: {
  hueco: Hueco;
  campos: Campo[];
  onConfirmar: (valor: string) => void | Promise<void>;
  /** Lo controla `TarjetaHueco` via `useAccion`: cierra la puerta al doble envio. */
  guardando?: boolean;
}) {
  const [valor, setValor] = useState<string>("");
  const items = Object.fromEntries(campos.map((c) => [c.nombre, c.nombre]));

  return (
    <div className="flex flex-col gap-2">
      <Select
        items={items}
        value={valor || null}
        onValueChange={(v) => setValor(typeof v === "string" ? v : "")}
      >
        <SelectTrigger aria-label={hueco.mensaje || "Campo padre"}>
          <SelectValue placeholder="Elige un campo" />
        </SelectTrigger>
        <SelectContent>
          {campos.map((c) => (
            <SelectItem key={c.nombre} value={c.nombre}>
              {c.nombre}
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
