import { CircleCheck, Download, Lock } from "lucide-react";

import { cn } from "cn";
import { urlGpm, urlManifiesto } from "@/lib/api";
import type { Hueco } from "@/lib/types";

import { contarPorCodigo } from "./agrupar";
import { tituloDeCodigo } from "./lenguaje";

/**
 * Columna de entrega, siempre a la vista.
 *
 * Antes esto era un recuadro al final del scroll. Con 65 huecos el analista
 * nunca lo veia, y es justo lo que mas se consulta: si la puerta del `.gpm`
 * esta abierta y que la mantiene cerrada.
 *
 * El simulador, la aprobacion y el manifiesto viven fuera de esa puerta a
 * proposito: no dependen del linter, asi que se ofrecen aun con huecos
 * pendientes. Un expediente bloqueado nunca deja al analista sin salida.
 */
export default function RielEntrega({
  sid,
  desbloqueado,
  bloqueantes,
  tieneVistas,
  fraseBloqueo,
}: {
  sid: string;
  desbloqueado: boolean;
  bloqueantes: Hueco[];
  tieneVistas: boolean;
  fraseBloqueo: (n: number) => string;
}) {
  const enlace =
    "text-primary underline underline-offset-2 hover:text-primary/80";

  return (
    <aside
      id="entrega"
      aria-label="Entrega"
      className="flex shrink-0 flex-col gap-4 rounded-lg border border-border bg-card p-4 lg:sticky lg:top-6 lg:w-60 lg:self-start"
    >
      <div className="flex flex-col gap-2">
        <p className="font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
          Entrega
        </p>
        <p
          className={cn(
            "flex items-start gap-2 rounded-md p-2.5 text-xs font-semibold",
            desbloqueado
              ? "bg-emerald-50 text-emerald-800"
              : "bg-destructive/10 text-destructive",
          )}
        >
          {desbloqueado ? (
            <CircleCheck aria-hidden className="mt-px size-3.5 shrink-0" />
          ) : (
            <Lock aria-hidden className="mt-px size-3.5 shrink-0" />
          )}
          {desbloqueado
            ? "Todo listo para entregar"
            : fraseBloqueo(bloqueantes.length)}
        </p>
      </div>

      {desbloqueado ? (
        <div className="flex flex-col gap-1.5 text-sm">
          <p className="font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
            Descargas
          </p>
          <a className={cn(enlace, "inline-flex items-center gap-1.5")} href={urlGpm(sid, "produccion")}>
            <Download aria-hidden className="size-3.5" />
            .gpm (producción)
          </a>
          <a className={cn(enlace, "inline-flex items-center gap-1.5")} href={urlGpm(sid, "pruebas")}>
            <Download aria-hidden className="size-3.5" />
            .gpm (pruebas)
          </a>
        </div>
      ) : (
        <div className="flex flex-col gap-1 text-xs">
          {/* En 240px de ancho una tarjeta por codigo seria ilegible: cada uno
              lleva su propia superficie, pero al tamano que cabe. */}
          {contarPorCodigo(bloqueantes).map(({ codigo, total }) => (
            <p
              key={codigo}
              className="flex items-baseline justify-between gap-2 rounded-md bg-muted/60 px-2 py-1 tabular-nums"
            >
              <span className="font-mono text-muted-foreground">
                {tituloDeCodigo(codigo) === codigo ? codigo : tituloDeCodigo(codigo)}
              </span>
              <span className="font-semibold text-foreground">{total}</span>
            </p>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-1.5 border-t border-border/60 pt-3 text-sm">
        <p className="font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
          Siempre disponible
        </p>
        <a className={enlace} href={`/simulador/${sid}`}>
          Abrir simulador
        </a>
        <a className={enlace} href={`/aprobacion/${sid}`}>
          Abrir aprobación
        </a>
        <a className={enlace} href={urlManifiesto(sid)}>
          Descargar manifiesto
        </a>
        {tieneVistas ? (
          <a className={enlace} href={`/vistas/${sid}`} target="_blank" rel="noreferrer">
            Ver vistas HTML
          </a>
        ) : null}
      </div>
    </aside>
  );
}
