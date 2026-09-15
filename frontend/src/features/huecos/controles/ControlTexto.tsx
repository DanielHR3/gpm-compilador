import { useId, useState } from "react";

import { Input } from "@/components/ui/input";
import type { Hueco } from "@/lib/types";

import { pistaDeCodigo } from "../lenguaje";

import BotonGuardar from "./BotonGuardar";

/**
 * Etiqueta accesible del campo segun el codigo del hueco. Debe contener
 * "tiempo" para `META-01`, "dependencia" para `META-02` y "nombre" para
 * `META-04` (los controles se localizan en las pruebas por `getByLabelText`).
 */
function etiquetaDe(hueco: Hueco): string {
  if (hueco.codigo === "META-01") return "Tiempo de resolucion";
  if (hueco.codigo === "META-02") return "Dependencia (campo del que depende)";
  if (hueco.codigo === "META-04") return "Nombre del tramite";
  return hueco.mensaje || "Valor";
}

/**
 * Control de texto libre para `META-01` (tiempo de resolucion), `META-02`
 * (dependencia) y `META-04` (nombre del tramite). "Guardar" queda
 * inhabilitado mientras el campo esta vacio.
 */
export default function ControlTexto({
  hueco,
  onConfirmar,
  guardando = false,
}: {
  hueco: Hueco;
  onConfirmar: (valor: string) => void | Promise<void>;
  /** Lo controla `TarjetaHueco` via `useAccion`: cierra la puerta al doble envio. */
  guardando?: boolean;
}) {
  const [valor, setValor] = useState<string>("");
  const id = useId();
  const etiqueta = etiquetaDe(hueco);
  const pista = pistaDeCodigo(hueco.codigo);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
      </label>
      {pista ? (
        <p className="text-sm text-muted-foreground">{pista.instruccion}</p>
      ) : null}
      <Input
        id={id}
        placeholder={pista?.marcador}
        value={valor}
        onChange={(e) => setValor(e.target.value)}
      />
      <BotonGuardar
        guardando={guardando}
        disabled={!valor.trim()}
        onClick={() => onConfirmar(valor)}
      />
    </div>
  );
}
