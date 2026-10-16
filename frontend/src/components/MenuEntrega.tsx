import { ArrowDown, ChevronDown, CircleCheck, Lock, Send } from "lucide-react";

import { cn } from "cn";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { contarPorCodigo } from "@/features/huecos/agrupar";
import { tituloDeCodigo } from "@/features/huecos/lenguaje";
import type { Hueco } from "@/lib/types";

/**
 * Menú «Entrega» de la barra superior.
 *
 * Antes era un riel fijo de 240 px a la derecha del wizard (`RielEntrega`),
 * y antes de eso un recuadro al final del scroll que con 65 huecos nadie
 * veía. La razón sigue viva: si la puerta del `.gpm` está abierta y qué la
 * mantiene cerrada es lo que más se consulta, y tiene que verse sin bajar.
 * El botón resume el semáforo; el menú trae el detalle y los destinos.
 *
 * Por qué en la barra y no en una columna: en una laptop de 14" la columna
 * se comía un cuarto del ancho, y en un teléfono se apilaba al final de la
 * página, justo donde no servía.
 *
 * Las descargas **no viven aquí**: son tarjetas con vista previa en el
 * panel `#entrega`, al final de la página. El menú apunta hacia allá.
 */
export default function MenuEntrega({
  sid,
  puerta,
  admin = false,
}: {
  sid: string;
  /** Estado de la puerta del linter; `null` cuando esta pantalla no lo carga. */
  puerta: { desbloqueado: boolean; bloqueantes: Hueco[] } | null;
  /** Solo el superusuario ve «quién hizo qué»: el servidor responde 403 a los demás. */
  admin?: boolean;
}) {
  const enlace = "text-primary underline underline-offset-2 hover:text-primary/80";
  const resumen =
    puerta === null ? null
    : puerta.desbloqueado ? "Listo"
    : `${puerta.bloqueantes.length} por revisar`;

  return (
    <Popover>
      <PopoverTrigger
        className={cn(
          "inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-semibold transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          puerta === null ? "border-border bg-card text-foreground hover:bg-muted"
          : puerta.desbloqueado ? "border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
          : "border-destructive/30 bg-destructive/10 text-destructive hover:bg-destructive/15",
        )}
      >
        {puerta === null ? (
          <Send aria-hidden className="size-4 shrink-0" />
        ) : puerta.desbloqueado ? (
          <CircleCheck aria-hidden className="size-4 shrink-0" />
        ) : (
          <Lock aria-hidden className="size-4 shrink-0" />
        )}
        {/* En un telefono solo cabe el icono y el resumen. */}
        <span className="max-sm:sr-only">Entrega</span>
        {resumen ? <span className="tabular-nums">{resumen}</span> : null}
        <ChevronDown aria-hidden className="size-3.5 shrink-0 opacity-70" />
      </PopoverTrigger>

      <PopoverContent aria-label="Entrega" className="flex flex-col gap-4">
        {puerta ? (
          <div className="flex flex-col gap-2">
            <p
              className={cn(
                "flex items-start gap-2 rounded-md p-2.5 text-xs font-semibold",
                puerta.desbloqueado
                  ? "bg-emerald-50 text-emerald-800"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              {puerta.desbloqueado ? (
                <CircleCheck aria-hidden className="mt-px size-3.5 shrink-0" />
              ) : (
                <Lock aria-hidden className="mt-px size-3.5 shrink-0" />
              )}
              {puerta.desbloqueado
                ? "Todo listo para entregar"
                : `${puerta.bloqueantes.length} por revisar`}
            </p>
            {puerta.desbloqueado ? null : (
              <div className="flex flex-col gap-1 text-xs">
                {contarPorCodigo(puerta.bloqueantes).map(({ codigo, total }) => (
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
          </div>
        ) : null}

        {/* Las observaciones salen tambien con el expediente bloqueado: lo que
            bloquea es justo lo que hay que mandarle a Simplificacion. Por eso
            el enlace no depende del semaforo. */}
        <a
          href={puerta ? "#entrega" : `/revisar/${sid}#entrega`}
          className={cn("inline-flex items-center gap-1.5 text-sm", enlace, puerta && "border-t border-border/60 pt-3")}
        >
          <ArrowDown aria-hidden className="size-3.5" />
          Ver las descargas
        </a>

        {/* Destinos que no son archivos y no dependen del linter. La
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
          <a className={enlace} href={`/revisar/${sid}/comparativa`}>
            Ver antes y después
          </a>
          <a className={enlace} href={`/revisar/${sid}/documentos`}>
            Ver documentos del trámite
          </a>
          {admin ? (
            <a className={enlace} href={`/auditoria?sid=${sid}`}>
              Ver quién hizo qué
            </a>
          ) : null}
        </div>
      </PopoverContent>
    </Popover>
  );
}
