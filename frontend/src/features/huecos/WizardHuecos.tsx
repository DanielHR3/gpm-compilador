import { useState } from "react";

import { Progress } from "@/components/ui/progress";
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

  const onResuelto = (resp: RespuestaResuelto) => {
    setHuecos(resp.huecos);
    const nextManifiesto = resp.manifiesto ?? manifiesto;
    if (resp.manifiesto) setManifiesto(resp.manifiesto);
    if (resp.reconocidos) {
      setReconocidos(
        new Set(resp.reconocidos.map(([c, u]) => `${c}|${u}`)),
      );
    }
    onEstado({ ...estado, manifiesto: nextManifiesto, huecos: resp.huecos });
  };

  return (
    <main className="mx-auto flex min-h-svh max-w-3xl flex-col gap-6 bg-background p-8 text-foreground">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Resolucion de huecos</h1>
        <Progress value={progreso} />
        <p className="text-sm text-muted-foreground">
          {resueltos} de {totalInicial} resueltos
        </p>
      </header>

      {problemas.length > 0 ? (
        <section className="flex flex-col gap-2 rounded-lg border border-border p-4">
          <h2 className="text-lg font-medium">Avisos del analisis de flujo</h2>
          <ul className="list-disc pl-5 text-sm text-muted-foreground">
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

      <section className="flex flex-col gap-3 rounded-lg border border-border p-4">
        {desbloqueado ? (
          <>
            <h2 className="text-lg font-medium">Todo listo para entregar</h2>
            <div className="flex flex-wrap gap-4 text-sm">
              <a
                className="text-primary underline"
                href={urlGpm(estado.sid, "produccion")}
              >
                Descargar .gpm (produccion)
              </a>
              <a
                className="text-primary underline"
                href={urlGpm(estado.sid, "pruebas")}
              >
                Descargar .gpm (pruebas)
              </a>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-lg font-medium">
              Faltan {bloqueantes.length} huecos por resolver antes de descargar
              el .gpm
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

        <div className="flex flex-wrap gap-4 text-sm">
          <a
            className="text-primary underline"
            href={urlManifiesto(estado.sid)}
          >
            Descargar manifiesto
          </a>
          <a
            className="text-primary underline"
            href={`/simulador/${estado.sid}`}
          >
            Abrir simulador
          </a>
          <a
            className="text-primary underline"
            href={`/aprobacion/${estado.sid}`}
          >
            Abrir aprobacion
          </a>
          {estado.tieneVistas ? (
            <a
              className="text-primary underline"
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
