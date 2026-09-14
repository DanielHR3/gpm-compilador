import { cn } from "cn";

/**
 * Navegación lateral del proceso: los cuatro pasos del Compilador GPM.
 *
 * Existió en `plantillas.py` (commit 311bbe1) y se perdió cuando la SPA tomó
 * `/` y `/revisar/:sid` en 3aa59c3: el código de la barra sigue ahí pero hoy
 * solo lo alcanzan `/historial` y la portada de respaldo. Esto la devuelve al
 * lado de React.
 *
 * Un paso al que todavía no se puede llegar se pinta igual pero NO es enlace:
 * el analista necesita ver el camino completo desde el primer momento, y a la
 * vez no debe poder saltar a una pantalla que no existe sin expediente.
 */
const PASOS = [
  { n: 1, nombre: "Insumos", href: () => "/" },
  { n: 2, nombre: "Revisión", href: (sid: string) => `/revisar/${sid}` },
  { n: 3, nombre: "Simulación", href: (sid: string) => `/simulador/${sid}` },
  { n: 4, nombre: "Descarga", href: () => "#entrega" },
] as const;

export default function NavegacionLateral({ sid }: { sid: string | null }) {
  // Sin expediente solo existe el paso 1; con expediente, el actual es la
  // revisión (los pasos 3 y 4 son destinos, no estados de la SPA).
  const actual = sid ? 2 : 1;

  return (
    <div className="flex w-full flex-col gap-1 sm:w-52">
      <nav aria-label="Proceso" className="flex flex-col gap-0.5">
        <p className="px-2 pb-1.5 font-mono text-[0.625rem] uppercase tracking-[0.1em] text-muted-foreground">
          Proceso
        </p>
        {PASOS.map((paso) => {
          const alcanzable = paso.n === 1 || sid !== null;
          const esActual = paso.n === actual;
          const contenido = (
            <>
              <span
                aria-hidden
                className={cn(
                  "grid size-4 place-items-center rounded font-mono text-[0.625rem]",
                  esActual
                    ? "bg-primary-foreground/25 text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {paso.n}
              </span>
              {paso.nombre}
            </>
          );
          const clases = cn(
            "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
            esActual
              ? "bg-primary font-semibold text-primary-foreground"
              : alcanzable
                ? "text-foreground/80 hover:bg-muted hover:text-foreground"
                : "text-muted-foreground/60",
          );

          return alcanzable ? (
            <a
              key={paso.n}
              href={paso.href(sid ?? "")}
              aria-current={esActual ? "step" : undefined}
              className={clases}
            >
              {contenido}
            </a>
          ) : (
            <span key={paso.n} aria-disabled className={clases}>
              {contenido}
            </span>
          );
        })}
      </nav>

      <hr className="my-2 border-border" />

      <a
        href="/historial"
        className="flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm font-medium text-foreground/80 transition-colors hover:bg-muted hover:text-foreground"
      >
        <span aria-hidden className="grid size-4 place-items-center rounded bg-muted font-mono text-[0.625rem] text-muted-foreground">
          ·
        </span>
        Historial
      </a>
    </div>
  );
}
