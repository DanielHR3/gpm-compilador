import { useState } from "react";
import { CircleAlert } from "lucide-react";
import { toast } from "sonner";

import { Progress } from "@/components/ui/progress";
import { cn } from "cn";
import type { EstadoExpediente, Hueco } from "@/lib/types";

import { agruparPorNivel } from "./agrupar";
import RielEntrega from "./RielEntrega";
import TarjetaHueco, { type RespuestaResuelto } from "./TarjetaHueco";
import { useListaConSalida } from "./useListaConSalida";

/** Debe coincidir con --duracion-salida-tarjeta de index.css. */
const MS_SALIDA = 240;

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
  const [reconocidos, setReconocidos] = useState<Set<string>>(
    () => new Set((estado.reconocidos ?? []).map(([c, u]) => `${c}|${u}`)),
  );
  const [totalInicial] = useState<number>(estado.huecos.length);

  // La tarjeta resuelta se retiene un instante para que pueda salir animada;
  // el conteo y la puerta del linter siguen mirando `huecos`, no esta lista.
  const enPantalla = useListaConSalida(huecos, clave, MS_SALIDA);
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

  const grupos = agruparPorNivel(enPantalla.map((e) => e.item));
  const salientes = new Set(
    enPantalla.filter((e) => e.saliendo).map((e) => clave(e.item)),
  );

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
      <main className="flex min-w-0 flex-1 flex-col gap-6 text-foreground">
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
            {/* Cada aviso es un hallazgo distinto del analisis: tarjeta propia
                en vez de vinetas, que los amontonan como si fueran uno solo. */}
            <div className="flex flex-col gap-2">
              {problemas.map((p, i) => (
                <article
                  key={i}
                  className="rounded-md border border-amber-200/80 bg-card/70 px-3 py-2 text-sm text-amber-900"
                >
                  {p}
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {notaComplejidad ? (
          <p className="text-sm text-muted-foreground">{notaComplejidad}</p>
        ) : null}

        {grupos.map((grupo) => (
          <section
            key={grupo.nivel}
            role="group"
            aria-label={`${grupo.rotulo} (${grupo.total})`}
            className="flex flex-col gap-3"
          >
            <h2 className="flex items-center gap-2.5 font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
              {grupo.rotulo}
              <span
                className={cn(
                  "rounded-full px-1.5 font-sans text-xs font-semibold tracking-normal",
                  grupo.nivel === "bloqueante"
                    ? "bg-destructive/10 text-destructive"
                    : grupo.nivel === "falta_dato"
                      ? "bg-amber-50 text-amber-700"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {grupo.total}
              </span>
              <span aria-hidden className="h-px flex-1 bg-border" />
            </h2>
            {grupo.huecos.map((h) => {
              const saliendo = salientes.has(clave(h));
              return (
                <div
                  key={clave(h)}
                  data-saliendo={saliendo}
                  className={saliendo ? "tarjeta-saliendo" : "tarjeta-entrando"}
                  aria-hidden={saliendo || undefined}
                >
                  <TarjetaHueco
                    hueco={h}
                    manifiesto={manifiesto}
                    sid={estado.sid}
                    onResuelto={onResuelto}
                  />
                </div>
              );
            })}
          </section>
        ))}
      </main>

      <RielEntrega
        sid={estado.sid}
        desbloqueado={desbloqueado}
        bloqueantes={bloqueantes}
        tieneVistas={estado.tieneVistas}
        fraseBloqueo={fraseBloqueo}
      />
    </div>
  );
}
