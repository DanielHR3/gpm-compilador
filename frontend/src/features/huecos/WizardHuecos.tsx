import { useState } from "react";
import { CircleAlert, CircleCheck, Download } from "lucide-react";
import { toast } from "sonner";

import { Progress } from "@/components/ui/progress";
import { cn } from "cn";
import { urlGpm, urlManifiesto } from "@/lib/api";
import type { EstadoExpediente, Hueco } from "@/lib/types";

import TarjetaHueco, { type RespuestaResuelto } from "./TarjetaHueco";

/** Clave estable de un hueco: `codigo|ubicacion`. */
const clave = (h: Hueco): string => `${h.codigo}|${h.ubicacion}`;

/**
 * Wizard de resolucion de huecos: una `Card` por hueco y una barra de progreso.
 * Cada control resuelve contra `/api/v1` y fusiona la respuesta en el estado
 * local sin recargar. La seccion de entrega se muestra SIEMPRE: si el linter
 * aun bloquea (`bloqueante`, o `falta_dato` sin reconocer) se listan los huecos
 * que faltan en vez del enlace al `.gpm`; el simulador, la aprobacion, las
 * vistas y el manifiesto siguen accesibles porque no dependen de esa puerta.
 */
export default function WizardHuecos({
  estado,
  onEstado,
}: {
  estado: EstadoExpediente;
  onEstado: (e: EstadoExpediente) => void;
}) {
  const [huecos, setHuecos] = useState<Hueco[]>(estado.huecos);
  const [manifiesto, setManifiesto] = useState<Record<string, unknown>>(
    estado.manifiesto,
  );
  const [reconocidos, setReconocidos] = useState<Set<string>>(new Set());
  const [totalInicial] = useState<number>(estado.huecos.length);

  const pendientes = huecos.filter((h) => !reconocidos.has(clave(h)));
  const resueltos = totalInicial - pendientes.length;
  const progreso =
    totalInicial === 0 ? 100 : (100 * resueltos) / totalInicial;

  // Huecos que mantienen cerrada la puerta del linter: los `bloqueante` y los
  // `falta_dato` que aun no se han reconocido. Es el mismo conjunto que decide
  // `desbloqueado`, por eso se deriva de aqui.
  const bloqueantes = huecos.filter(
    (h) =>
      h.nivel === "bloqueante" ||
      (h.nivel === "falta_dato" && !reconocidos.has(clave(h))),
  );
  const desbloqueado = bloqueantes.length === 0;

  const problemas = estado.problemas ?? [];
  const est = estado.estimacion as { nivel?: unknown; dias?: unknown };
  const nivelEst = typeof est?.nivel === "string" ? est.nivel : null;
  const diasEst =
    typeof est?.dias === "string" || typeof est?.dias === "number"
      ? String(est.dias)
      : null;
  const notaComplejidad =
    nivelEst || diasEst
      ? `Complejidad estimada: ${nivelEst ?? "?"} — ${diasEst ?? "?"}`
      : null;

  /** "Quedan 3 huecos" / "Queda 1 hueco" / "No queda ninguno". */
  const frasePendientes = (n: number): string => {
    if (n === 0) return "No queda ningun hueco pendiente.";
    if (n === 1) return "Queda 1 hueco por resolver.";
    return `Quedan ${n} huecos por resolver.`;
  };

  /** Encabezado de la seccion de entrega, concordado en numero. */
  const fraseBloqueo = (n: number): string =>
    n === 1
      ? "Falta 1 hueco por resolver antes de descargar el .gpm"
      : `Faltan ${n} huecos por resolver antes de descargar el .gpm`;

  const onResuelto = (resp: RespuestaResuelto, resuelto: Hueco) => {
    setHuecos(resp.huecos);
    const nextManifiesto = resp.manifiesto ?? manifiesto;
    if (resp.manifiesto) setManifiesto(resp.manifiesto);
    const nextReconocidos = resp.reconocidos
      ? new Set(resp.reconocidos.map(([c, u]) => `${c}|${u}`))
      : reconocidos;
    if (resp.reconocidos) setReconocidos(nextReconocidos);
    onEstado({ ...estado, manifiesto: nextManifiesto, huecos: resp.huecos });

    // Sin esto la tarjeta simplemente desaparecia: no habia forma de saber si
    // el guardado surtio efecto ni cuanto falta para desbloquear el .gpm.
    const faltan = resp.huecos.filter(
      (h) => !nextReconocidos.has(clave(h)),
    ).length;
    toast.success(`${resuelto.codigo} resuelto`, {
      description: frasePendientes(faltan),
    });
  };

  return (
    <main className="mx-auto flex min-h-svh max-w-3xl flex-col gap-6 bg-background p-8 text-foreground">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight">
          Resolución de huecos
        </h1>
        <Progress value={progreso} />
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{resueltos}</span> de{" "}
          {totalInicial} resueltos
        </p>
      </header>

      {problemas.length > 0 ? (
        <section className="flex flex-col gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-amber-800">
            <CircleAlert aria-hidden className="size-4" />
            Avisos del análisis de flujo
          </h2>
          <ul className="list-disc pl-5 text-sm text-amber-900/80">
            {problemas.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {notaComplejidad ? (
        <p className="text-sm text-muted-foreground">{notaComplejidad}</p>
      ) : null}

      <div className="flex flex-col gap-4">
        {huecos.map((h) => (
          <TarjetaHueco
            key={clave(h)}
            hueco={h}
            manifiesto={manifiesto}
            sid={estado.sid}
            onResuelto={onResuelto}
          />
        ))}
      </div>

      <section
        className={cn(
          "flex flex-col gap-3 rounded-lg border p-4",
          desbloqueado
            ? "border-emerald-200 bg-emerald-50"
            : "border-border bg-card",
        )}
      >
        {desbloqueado ? (
          <>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
              <CircleCheck aria-hidden className="size-4" />
              Todo listo para entregar
            </h2>
            <div className="flex flex-wrap gap-4 text-sm">
              <a
                className="inline-flex items-center gap-1.5 text-primary underline underline-offset-2"
                href={urlGpm(estado.sid, "produccion")}
              >
                <Download aria-hidden className="size-3.5" />
                Descargar .gpm (producción)
              </a>
              <a
                className="inline-flex items-center gap-1.5 text-primary underline underline-offset-2"
                href={urlGpm(estado.sid, "pruebas")}
              >
                <Download aria-hidden className="size-3.5" />
                Descargar .gpm (pruebas)
              </a>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-sm font-semibold text-foreground">
              {fraseBloqueo(bloqueantes.length)}
            </h2>
            <ul className="list-disc pl-5 text-sm text-muted-foreground">
              {bloqueantes.map((h) => (
                <li key={clave(h)}>
                  [{h.codigo}] {h.mensaje}
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="flex flex-wrap gap-4 border-t border-border/60 pt-3 text-sm">
          <a
            className="text-primary underline underline-offset-2"
            href={urlManifiesto(estado.sid)}
          >
            Descargar manifiesto
          </a>
          <a
            className="text-primary underline underline-offset-2"
            href={`/simulador/${estado.sid}`}
          >
            Abrir simulador
          </a>
          <a
            className="text-primary underline underline-offset-2"
            href={`/aprobacion/${estado.sid}`}
          >
            Abrir aprobación
          </a>
          {estado.tieneVistas ? (
            <a
              className="text-primary underline underline-offset-2"
              href={`/vistas/${estado.sid}`}
              target="_blank"
              rel="noreferrer"
            >
              Ver vistas HTML
            </a>
          ) : null}
        </div>
      </section>
    </main>
  );
}
