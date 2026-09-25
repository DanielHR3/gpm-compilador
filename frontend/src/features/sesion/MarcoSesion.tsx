import type { ReactNode } from "react";

import PieInstitucional from "@/components/PieInstitucional";

/**
 * El marco de las pantallas sin sesión (entrar, registro, recuperación).
 *
 * Dos columnas: a la izquierda la franja guinda de la casa —la misma barra
 * lateral que verá la persona en cuanto entre— con el nombre del producto y
 * una sola frase de lo que hace; a la derecha, el formulario sobre superficie
 * clara, con el logo institucional en sus colores. En angosto la franja se
 * vuelve una banda arriba y el formulario ocupa el ancho.
 */
export default function MarcoSesion({
  titulo,
  descripcion,
  etiqueta,
  children,
}: {
  titulo: string;
  descripcion: string;
  /** `aria-label` de la región del formulario. */
  etiqueta: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col bg-background lg:flex-row">
      <aside className="flex shrink-0 flex-col justify-between bg-primary px-8 py-8 text-primary-foreground lg:min-h-svh lg:w-[42%] lg:max-w-xl lg:px-14 lg:py-14">
        <p className="font-heading text-lg font-bold tracking-tight">Compilador GPM</p>
        <div className="my-10 flex flex-col gap-5 lg:my-0">
          <p className="font-heading text-3xl font-bold leading-tight lg:text-4xl">
            Del expediente de un trámite al .gpm que importa la plataforma.
          </p>
          <p className="max-w-md text-base text-white/80">
            Sube el AS-IS, el TO-BE y el Diccionario; el compilador revisa qué falta, lo deja
            simular y entrega el archivo listo para el modelador.
          </p>
        </div>
        <p className="text-xs text-white/60">
          Dirección de Gestión Tecnológica · Dirección de Simplificación Administrativa
        </p>
      </aside>

      <div className="flex flex-1 flex-col">
        <main className="flex flex-1 items-center justify-center px-6 py-10 lg:px-16">
          <section role="region" aria-label={etiqueta} className="w-full max-w-sm">
            <img
              src="/logo-hidalgo-coemere.svg"
              alt="Gobierno del Estado de Hidalgo · Comisión Estatal de Mejora Regulatoria"
              className="mb-10 h-11 w-auto"
            />
            <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">{titulo}</h1>
            <p className="mt-2 mb-8 text-sm text-muted-foreground">{descripcion}</p>
            {children}
          </section>
        </main>
        <PieInstitucional />
      </div>
    </div>
  );
}
