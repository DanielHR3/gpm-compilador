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
 * local sin recargar. Al llegar a `bloquean = 0` (ningun `bloqueante` y ningun
 * `falta_dato` sin reconocer) aparecen los enlaces de descarga y a las
 * pantallas HTML que siguen vivas.
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

  const hayBloqueante = huecos.some((h) => h.nivel === "bloqueante");
  const faltaDatoPendiente = huecos.some(
    (h) => h.nivel === "falta_dato" && !reconocidos.has(clave(h)),
  );
  const desbloqueado = !hayBloqueante && !faltaDatoPendiente;

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

      {desbloqueado ? (
        <section className="flex flex-col gap-3 rounded-lg border border-border p-4">
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
            <a
              className="text-primary underline"
              href={urlManifiesto(estado.sid)}
            >
              Descargar manifiesto
            </a>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
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
          </div>
        </section>
      ) : null}
    </main>
  );
}
