import { useState } from "react";
import { CircleAlert } from "lucide-react";
import { toast } from "sonner";

import { Progress } from "@/components/ui/progress";
import Instrucciones from "@/components/Instrucciones";
import { cn } from "cn";
import type { EstadoExpediente, Hueco } from "@/lib/types";

import { agruparPorNivel } from "./agrupar";
import Adjuntos from "./Adjuntos";
import ModoFoco from "./ModoFoco";
import ResumenExpediente from "./ResumenExpediente";
import { useFoco } from "./useFoco";
import RielEntrega from "./RielEntrega";
import TarjetaHueco, { type RespuestaResuelto } from "./TarjetaHueco";
import { useListaConSalida } from "./useListaConSalida";

/**
 * A partir de cuantos huecos el modo foco entra solo.
 *
 * Por debajo, la lista completa cabe de un vistazo y obligar a navegar de uno
 * en uno estorba. Por encima —Publicacion trae 65— la lista deja de servir: el
 * analista pierde el sitio en cuanto hace scroll. El umbral se puede cambiar a
 * mano en cualquier momento; esto solo decide con que arranca.
 */
const HUECOS_PARA_FOCO = 20;

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
  const [modo, setModo] = useState<"lista" | "foco">(() =>
    estado.huecos.length > HUECOS_PARA_FOCO ? "foco" : "lista",
  );
  const [ultimoActor, setUltimoActor] = useState<string>("");
  const [reconocidos, setReconocidos] = useState<Set<string>>(
    () => new Set((estado.reconocidos ?? []).map(([c, u]) => `${c}|${u}`)),
  );
  // La lista original nunca encoge: es la que numera el indice del modo foco.
  const [huecosOriginales] = useState<Hueco[]>(estado.huecos);
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
  // Cerrado = ya no vive en la lista del servidor, o esta reconocido.
  const vivos = new Set(huecos.map(clave));
  const cerradas = new Set(
    huecosOriginales
      .map(clave)
      .filter((k) => !vivos.has(k) || reconocidos.has(k)),
  );
  const foco = useFoco(huecosOriginales, cerradas);

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

  const onResuelto = (
    resp: RespuestaResuelto,
    resuelto: Hueco,
    valor?: string,
  ) => {
    // Con 42 MMD-03 seguidos, proponer el actor anterior ahorra dos clics por
    // hueco. Solo se recuerda para ese codigo: en los demas no hay repeticion
    // que aprovechar.
    if (resuelto.codigo === "MMD-03" && valor) setUltimoActor(valor);
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

    // Con la numeracion estable la tarjeta resuelta se queda en su sitio, en
    // verde: si el foco no se mueve, hay que pulsar "Siguiente" tras cada
    // guardado. Se avanza al siguiente pendiente. En lista no hay foco.
    if (modo === "foco") foco.siguientePendiente();
  };

  const grupos = agruparPorNivel(enPantalla.map((e) => e.item));
  const salientes = new Set(
    enPantalla.filter((e) => e.saliendo).map((e) => clave(e.item)),
  );

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
      <main className="flex min-w-0 flex-1 flex-col gap-6 text-foreground">
        {/* Lo que el compilador entendio, antes que lo que falta: el analista
            necesita confirmar que su documento se leyo bien. */}
        <ResumenExpediente manifiesto={manifiesto} estimacion={estado.estimacion} />

        {/* El diagrama contesta «¿quién hace esta tarea?»: va arriba, donde se
            está resolviendo, no en otra pestaña. */}
        <Adjuntos sid={estado.sid} adjuntos={estado.adjuntos ?? []} />

        <header className="flex flex-col gap-2">
          <h1 className="text-2xl font-bold tracking-tight">
            Resolución de huecos
          </h1>
          <Instrucciones
            id="revision"
            resumen="Aquí está lo que el compilador no pudo deducir de tus documentos. Cierra cada tarjeta y se habilita la descarga del .gpm."
          >
            <p>
              Un <strong>hueco</strong> no es un error: es una pregunta que tus
              documentos dejaron sin responder. Vienen en tres severidades.
            </p>
            <p>
              <strong>Bloquean la descarga</strong> — falta un insumo entero.
              No se arregla aquí: se corrige el documento y se vuelve a subir.
            </p>
            <p>
              <strong>Falta un dato</strong> — lo contestas en la tarjeta, o
              dices «lo configuro a mano». Ojo con esa salida: significa que el
              .gpm sale incompleto y que <strong>tú lo terminas dentro de la
              plataforma</strong> después de importarlo. No desaparece el
              trabajo, lo mueve.
            </p>
            <p>
              <strong>Solo confirmar</strong> — el compilador ya decidió algo
              razonable y quiere que lo mires. Léelo y ciérralo.
            </p>
            <p>
              Con muchos huecos conviene <strong>uno a la vez</strong>: al
              guardar salta solo al siguiente pendiente. En{" "}
              <strong>lista</strong> los ves todos y eliges el orden. Cuando no
              quede ninguno sin decidir, se abre el paso 4.
            </p>
          </Instrucciones>
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

        {totalInicial > 0 ? (
          <div
            role="radiogroup"
            aria-label="Cómo ver los huecos"
            className="flex w-fit gap-0.5 rounded-lg bg-muted p-0.5"
          >
            {(
              [
                ["lista", "Lista"],
                ["foco", "Uno a la vez"],
              ] as const
            ).map(([valor, etiqueta]) => (
              <button
                key={valor}
                type="button"
                role="radio"
                aria-checked={modo === valor}
                onClick={() => setModo(valor)}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                  modo === valor
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {etiqueta}
              </button>
            ))}
          </div>
        ) : null}

        {modo === "foco" && foco.actual ? (
          <>
            <ModoFoco
              huecos={huecosOriginales}
              resueltas={cerradas}
              actualClave={clave(foco.actual)}
              onIr={foco.irA}
              onAnterior={foco.anterior}
              onSiguiente={foco.siguiente}
              indice={foco.indice}
              total={foco.total}
            />
            <div className="tarjeta-entrando">
              <TarjetaHueco
                key={clave(foco.actual)}
                hueco={foco.actual}
                manifiesto={manifiesto}
                sid={estado.sid}
                onResuelto={onResuelto}
              />
            </div>
          </>
        ) : null}

        {modo === "lista"
          ? grupos.map((grupo) => (
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
                    ultimoActor={ultimoActor}
                    hueco={h}
                    manifiesto={manifiesto}
                    sid={estado.sid}
                    onResuelto={onResuelto}
                  />
                </div>
              );
            })}
          </section>
            ))
          : null}
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
