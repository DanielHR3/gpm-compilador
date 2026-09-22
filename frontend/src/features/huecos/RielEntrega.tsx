import { ArrowDown, CircleCheck, Lock } from "lucide-react";

import { cn } from "cn";
import type { Hueco } from "@/lib/types";

import { contarPorCodigo } from "./agrupar";
import { tituloDeCodigo } from "./lenguaje";

/**
 * Columna de estado, siempre a la vista.
 *
 * Antes esto era un recuadro al final del scroll. Con 65 huecos el analista
 * nunca lo veia, y es justo lo que mas se consulta: si la puerta del `.gpm`
 * esta abierta y que la mantiene cerrada.
 *
 * Las descargas **ya no viven aqui**: en 240 px solo cabian enlaces de texto
 * con nombres que se parecen —dos `.gpm`, un manifiesto, unas observaciones—
 * y no habia forma de mirar dentro antes de bajarlos. Se mudaron al panel
 * `#entrega`, al final de la pagina, donde cada una es una tarjeta con vista
 * previa. El riel conserva el semaforo y apunta hacia alla.
 */
export default function RielEntrega({
  sid,
  desbloqueado,
  bloqueantes,
}: {
  sid: string;
  desbloqueado: boolean;
  bloqueantes: Hueco[];
}) {
  const enlace = "text-primary underline underline-offset-2 hover:text-primary/80";

  return (
    <aside
      aria-label="Estado de la entrega"
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
            : `${bloqueantes.length} por revisar`}
        </p>
      </div>

      {desbloqueado ? null : (
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

      {/* Las observaciones salen tambien con el expediente bloqueado: lo que
          bloquea es justo lo que hay que mandarle a Simplificacion. Por eso el
          enlace no depende del semaforo. */}
      <a
        href="#entrega"
        className="inline-flex items-center gap-1.5 border-t border-border/60 pt-3 text-sm text-primary underline underline-offset-2 hover:text-primary/80"
      >
        <ArrowDown aria-hidden className="size-3.5" />
        Ver las descargas
      </a>

      {/* Dos destinos que no son archivos y no dependen del linter. La
          aprobacion no tiene otra puerta en toda la SPA: si sale de aqui,
          desaparece. */}
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
      </div>
    </aside>
  );
}
