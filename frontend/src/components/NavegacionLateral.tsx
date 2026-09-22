import { BookOpen, Download, FileUp, History, ListChecks, MonitorPlay } from "lucide-react";

import { cn } from "cn";

/**
 * Navegación lateral del proceso: los cuatro pasos del Compilador GPM.
 *
 * Sigue el armazón que ya usan `checador-web` y `GeoApertura`: barra guinda de
 * piso a techo, un icono por paso, el paso actual en arena (`brand-secondary`)
 * y un bloque de contexto abajo, separado por una línea tenue. No es una
 * decisión estética nueva — es la casa.
 *
 * Existió en `plantillas.py` (commit 311bbe1) y se perdió cuando la SPA tomó
 * `/` y `/revisar/:sid` en 3aa59c3.
 *
 * Un paso al que todavía no se puede llegar se pinta igual pero NO es enlace:
 * el analista necesita ver el camino completo desde el primer momento, y a la
 * vez no debe poder saltar a una pantalla que no existe sin expediente.
 */
const PASOS = [
  { n: 1, nombre: "Insumos", icono: FileUp, href: () => "/" },
  { n: 2, nombre: "Revisión", icono: ListChecks, href: (sid: string) => `/revisar/${sid}` },
  { n: 3, nombre: "Simulación", icono: MonitorPlay, href: (sid: string) => `/simulador/${sid}` },
  { n: 4, nombre: "Descarga", icono: Download, href: () => "#entrega" },
] as const;

export default function NavegacionLateral({
  sid,
  tramite,
}: {
  sid: string | null;
  /** Nombre del trámite en curso, para el bloque de contexto de abajo. */
  tramite?: string | null;
}) {
  // Sin expediente solo existe el paso 1; con expediente, el actual es la
  // revisión (los pasos 3 y 4 son destinos, no estados de la SPA).
  const actual = sid ? 2 : 1;

  const base =
    "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors max-lg:justify-center max-lg:px-0";

  return (
    // En pantalla angosta se reduce a un carril de iconos en vez de
    // desaparecer: perder la navegacion entera es peor que perder las
    // etiquetas, que siguen en el arbol para un lector de pantalla.
    // `sticky` + alto de pantalla: al bajar por la lista de huecos el menu se
    // iba con el scroll, y «Descarga» —el ultimo paso— quedaba inalcanzable
    // justo al final de la revision, que es cuando se usa. Visto en pantalla
    // el 2026-09-21 con Prorroga cargada.
    <div className="sticky top-0 flex h-svh w-16 shrink-0 flex-col overflow-y-auto bg-primary text-primary-foreground lg:w-64">
      <div className="flex h-16 items-center justify-center border-b border-white/10 px-3 lg:justify-start lg:px-6">
        <span className="font-heading text-lg font-bold tracking-tight">
          <span className="lg:hidden" aria-hidden>GPM</span>
          <span className="hidden lg:inline">Compilador GPM</span>
        </span>
      </div>

      <nav aria-label="Proceso" className="flex flex-1 flex-col gap-1 px-3 py-4">
        {PASOS.map((paso) => {
          const alcanzable = paso.n === 1 || sid !== null;
          const esActual = paso.n === actual;
          const Icono = paso.icono;
          const contenido = (
            <>
              <Icono aria-hidden className="size-5 shrink-0" />
              <span className="max-lg:sr-only">{paso.nombre}</span>
            </>
          );
          const clases = cn(
            base,
            esActual
              ? "bg-secondary font-semibold text-secondary-foreground"
              : alcanzable
                ? "text-white/70 hover:bg-white/10 hover:text-white"
                : "cursor-default text-white/35",
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

      <div className="flex flex-col gap-3 border-t border-white/10 p-4">
        {sid ? (
          <div className="flex flex-col gap-1 px-3 max-lg:hidden">
            <p className="truncate text-sm font-bold" title={tramite ?? undefined}>
              {tramite || "Expediente en curso"}
            </p>
            <span className="inline-flex w-fit rounded-full border border-white/5 bg-white/10 px-2 py-0.5 font-mono text-[9px] font-black uppercase tracking-widest text-white/80">
              {sid.slice(0, 8)}
            </span>
          </div>
        ) : null}
        {/* Referencia, no un paso: va fuera de <nav aria-label="Proceso"> y se
            alcanza sin expediente. Lista lo que el compilador sabe emitir. */}
        <a href="/catalogos" className={cn(base, "text-white/70 hover:bg-white/10 hover:text-white")}>
          <BookOpen aria-hidden className="size-5 shrink-0" />
          <span className="max-lg:sr-only">Catálogos</span>
        </a>
        <a href="/historial" className={cn(base, "text-white/70 hover:bg-white/10 hover:text-white")}>
          <History aria-hidden className="size-5 shrink-0" />
          <span className="max-lg:sr-only">Historial</span>
        </a>
      </div>
    </div>
  );
}
