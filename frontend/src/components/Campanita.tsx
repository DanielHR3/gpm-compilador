import { Bell } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { cn } from "cn";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { leerSolicitudes, marcarSolicitudVista, type Solicitud, urlAsIsDeSolicitud } from "@/lib/api";
import { guardarTramiteLigado } from "@/lib/tramiteLigado";

/**
 * Campanita de la barra superior: trámites que Reingeniería envió desde Simplifica
 * («Enviar al Compilador», spec 2026-11-10-solicitudes-desde-simplifica). Cada uno
 * baja un AS-IS inicial con el `ruts_id` ya puesto, así el expediente nace ligado.
 * Se consulta al entrar y cada minuto. Si el servidor no tiene la ruta o falla,
 * no se enseña nada: la campanita nunca estorba al trabajo.
 */
const CADA_MS = 60_000;

function fecha(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso
    : d.toLocaleString("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function Campanita() {
  const [datos, setDatos] = useState<{ solicitudes: Solicitud[]; nuevas: number } | null>(null);
  const [fallo, setFallo] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setDatos(await leerSolicitudes());
      setFallo(false);
    } catch {
      setFallo(true);
    }
  }, []);

  useEffect(() => {
    void cargar();
    const id = setInterval(() => void cargar(), CADA_MS);
    return () => clearInterval(id);
  }, [cargar]);

  if (fallo || datos === null) return null;
  const { solicitudes, nuevas } = datos;
  const enlace = "text-primary underline underline-offset-2 hover:text-primary/80";

  return (
    <Popover>
      <PopoverTrigger
        aria-label={`Solicitudes de Simplifica: ${nuevas ? `${nuevas} nueva${nuevas === 1 ? "" : "s"}` : "sin nuevas"}`}
        className={cn(
          "relative inline-flex size-9 items-center justify-center rounded-md border border-border bg-card text-foreground",
          "transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <Bell aria-hidden className="size-4" />
        {nuevas ? (
          <span className="absolute -right-1.5 -top-1.5 flex min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[11px] font-bold text-primary-foreground tabular-nums">
            {nuevas}
          </span>
        ) : null}
      </PopoverTrigger>
      <PopoverContent aria-label="Solicitudes de Simplifica" className="flex max-h-[70vh] w-96 flex-col gap-3 overflow-y-auto">
        <p className="text-sm font-semibold text-foreground">Enviados desde Simplifica</p>
        {solicitudes.length === 0 ? (
          <p className="text-xs text-muted-foreground">Todavía no llega ningún trámite.</p>
        ) : (
          solicitudes.map((s) => (
            <div key={s.ruts_id} className={cn("flex flex-col gap-1 rounded-md p-2.5 text-xs", s.nueva ? "bg-primary/10" : "bg-muted/60")}>
              <p className="font-semibold text-foreground">{s.nombre}</p>
              <p className="text-muted-foreground">
                RUTS {s.ruts_id} · {s.dependencia}{s.enviado_por ? ` · enviado por ${s.enviado_por}` : ""}
              </p>
              <p className="text-muted-foreground">
                {fecha(s.recibida)}
                {s.etapa ? <> · <span className="font-semibold text-foreground">{s.etapa}</span></> : null}
              </p>
              <div className="flex flex-wrap gap-3">
                {/* El expediente nace ligado a este trámite aunque el AS-IS no traiga su ID de RUTS. */}
                <a className={enlace} href="/desde-as-is"
                   onClick={() => guardarTramiteLigado({ ruts_id: s.ruts_id, nombre: s.nombre })}>
                  {!s.etapa || s.etapa === "Por iniciar" ? "Empezar expediente" : "Continuar expediente"}
                </a>
                <a className={enlace} href={urlAsIsDeSolicitud(s.ruts_id)}>Descargar AS-IS</a>
                {s.nueva ? (
                  <button
                    type="button"
                    className={enlace}
                    onClick={async () => {
                      await marcarSolicitudVista(s.ruts_id).catch(() => undefined);
                      await cargar();
                    }}
                  >
                    Marcar como vista
                  </button>
                ) : null}
              </div>
            </div>
          ))
        )}
      </PopoverContent>
    </Popover>
  );
}
