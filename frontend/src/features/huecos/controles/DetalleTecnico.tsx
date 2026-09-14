import type { ReactNode } from "react";

/**
 * Lo que solo le sirve a quien programa o reporta: codigo de validacion,
 * nombres internos, el texto crudo del compilador.
 *
 * Va plegado, no borrado. Quien documenta el tramite no lo necesita para
 * decidir; quien rastrea un fallo o levanta un reporte, si. Una sola pieza
 * para que todas las tarjetas lo presenten igual.
 */
export default function DetalleTecnico({
  codigo,
  ubicacion,
  crudo,
  extra,
}: {
  codigo: string;
  ubicacion?: string;
  /** El mensaje tal cual lo emitio el compilador. */
  crudo: string;
  extra?: ReactNode;
}) {
  return (
    <details className="text-xs text-muted-foreground">
      <summary className="cursor-pointer select-none underline-offset-2 hover:underline">
        Ver detalle técnico
      </summary>
      <dl className="mt-2 flex flex-col gap-1 rounded-md bg-muted/40 p-3">
        <div className="flex gap-2">
          <dt className="font-medium">Código:</dt>
          <dd className="font-mono">{codigo}</dd>
        </div>
        {ubicacion ? (
          <div className="flex gap-2">
            <dt className="font-medium">Ubicación:</dt>
            <dd className="font-mono break-all">{ubicacion}</dd>
          </div>
        ) : null}
        {extra}
        <div className="flex flex-col gap-0.5">
          <dt className="font-medium">Mensaje del compilador:</dt>
          <dd className="italic">{crudo}</dd>
        </div>
      </dl>
    </details>
  );
}
