import { useState } from "react";
import type { ReactNode } from "react";

import { cn } from "cn";

const CLAVE = (id: string) => `gpmc.ayuda.${id}`;

/**
 * Lee si esta pantalla quedó plegada en una visita anterior.
 *
 * `localStorage` lanza en ventana privada y con las cookies de sitio
 * bloqueadas. La ayuda no puede ser el motivo de que una pantalla no se vea,
 * así que ante cualquier fallo se responde "nunca se plegó" y el detalle abre:
 * mejor de más que de menos para quien no ha usado esto antes.
 */
function quedoPlegado(id: string): boolean {
  try {
    return localStorage.getItem(CLAVE(id)) === "plegado";
  } catch {
    return false;
  }
}

function recordar(id: string, plegado: boolean) {
  try {
    if (plegado) localStorage.setItem(CLAVE(id), "plegado");
    else localStorage.removeItem(CLAVE(id));
  } catch {
    // Sin dónde guardarlo, el detalle abrirá en la siguiente visita. Es
    // molesto, no roto.
  }
}

/**
 * Las instrucciones de una pantalla: una línea fija con lo que hay que hacer y
 * un desplegable con el detalle.
 *
 * El flujo del compilador —insumos, huecos por severidad, simulación, la puerta
 * de la descarga— es mucho para quien entra por primera vez, y los analistas de
 * Simplificación lo usan con semanas de por medio. El resumen está siempre a la
 * vista; el detalle abre solo la primera vez y después se queda plegado, para
 * que a quien ya sabe no le estorbe.
 *
 * `id` distingue la memoria de cada pantalla: plegar la de insumos no pliega la
 * de revisión.
 */
export default function Instrucciones({
  id,
  resumen,
  children,
  className,
}: {
  id: string;
  resumen: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const [abierto, setAbierto] = useState(() => !quedoPlegado(id));

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <p className="max-w-prose text-sm text-muted-foreground">{resumen}</p>
      <details
        aria-label="Instrucciones de la pantalla"
        open={abierto}
        onToggle={(e) => {
          const ahora = (e.currentTarget as HTMLDetailsElement).open;
          setAbierto(ahora);
          recordar(id, !ahora);
        }}
        className="max-w-prose rounded-lg border border-border bg-card/60 text-sm"
      >
        <summary className="cursor-pointer px-3 py-2 font-medium text-foreground">
          ¿Cómo funciona esta pantalla?
        </summary>
        <div className="flex flex-col gap-2 border-t border-border px-3 py-2.5 text-muted-foreground [&_strong]:font-medium [&_strong]:text-foreground">
          {children}
        </div>
      </details>
    </div>
  );
}
