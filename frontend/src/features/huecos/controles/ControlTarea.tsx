import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import type { Hueco } from "@/lib/types";

import { pistaDeCodigo } from "../lenguaje";
import type { TareaCandidata } from "../tareasDeDocumento";

import BotonGuardar from "./BotonGuardar";
import DetalleTecnico from "./DetalleTecnico";

/** `<select>` nativo, con las clases de `components/ui/input.tsx`: las opciones
 *  deshabilitadas con su motivo se leen sin abrir nada mas, y las pruebas lo
 *  manejan con `selectOptions`. Mismo criterio que `ConstructorRegla`. */
const claseSelect =
  "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30";

/**
 * Control para `DOC-04` de nivel `por_confirmar`: en qué tarea se genera un
 * documento del trámite.
 *
 * El compilador lo cuelga de la primera tarea que ya tiene sus datos, y con
 * plantillas sin variables esa es siempre la primera: los oficios de rechazo
 * salían al enviar la solicitud, antes de que nadie decidiera nada. Las tareas
 * que no valen no se esconden: se enseñan deshabilitadas con el motivo, para
 * que quien busca «la de la firma» sepa por qué no puede elegirla.
 */
export default function ControlTarea({
  hueco,
  candidatas,
  onConfirmar,
  onDejar,
  guardando = false,
}: {
  hueco: Hueco;
  candidatas: TareaCandidata[];
  onConfirmar: (tareaId: string) => void | Promise<void>;
  onDejar: () => void | Promise<void>;
  /** Lo controla `TarjetaHueco` via `useAccion`: cierra la puerta al doble envio. */
  guardando?: boolean;
}) {
  const actual = candidatas.find((c) => c.actual)?.id ?? "";
  const [valor, setValor] = useState<string>(actual);
  const id = useId();
  const pista = pistaDeCodigo(hueco.codigo);

  return (
    <div className="flex flex-col gap-3">
      {pista ? (
        <p className="text-sm text-muted-foreground">{pista.instruccion}</p>
      ) : null}

      <div className="flex flex-col gap-1">
        <label htmlFor={id} className="text-sm font-medium">
          Tarea en la que se genera el documento
        </label>
        <select
          id={id}
          className={claseSelect}
          value={valor}
          onChange={(e) => setValor(e.target.value)}
        >
          {actual ? null : <option value="">Elige una tarea</option>}
          {candidatas.map((c) => (
            <option key={c.id} value={c.id} disabled={!c.vale}>
              {c.motivo ? `${c.nombre} — ${c.motivo}` : c.nombre}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <BotonGuardar
          guardando={guardando}
          disabled={!valor || valor === actual}
          onClick={() => onConfirmar(valor)}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={guardando}
          onClick={() => onDejar()}
        >
          Dejarlo así
        </Button>
      </div>

      <DetalleTecnico
        codigo={hueco.codigo}
        ubicacion={hueco.ubicacion}
        crudo={hueco.mensaje}
      />
    </div>
  );
}
