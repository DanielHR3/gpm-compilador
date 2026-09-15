import { useState } from "react";
import { FileText, Image as IconoImagen, Paperclip, X } from "lucide-react";

import { cn } from "cn";
import { urlAdjunto } from "@/lib/api";
import type { Adjunto } from "@/lib/types";

/**
 * Documentos de apoyo del expediente, a la vista mientras se resuelven huecos.
 *
 * El diagrama que dice quién hace cada tarea vivía en un PNG fuera de la
 * herramienta: para contestar «¿Quién hace Completar datos?» había que salirse,
 * abrir el archivo y volver. No alimentan al extractor —una imagen no se
 * puede leer sin adivinar— pero sí resuelven la pregunta que tiene enfrente
 * quien está capturando.
 */
export default function Adjuntos({
  sid,
  adjuntos,
}: {
  sid: string;
  adjuntos: Adjunto[];
}) {
  const [abierto, setAbierto] = useState<string | null>(null);

  if (adjuntos.length === 0) return null;

  const abiertoAhora = adjuntos.find((a) => a.nombre === abierto);

  return (
    <section
      aria-label="Documentos de apoyo"
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      <p className="flex items-center gap-2 text-sm font-medium text-foreground">
        <Paperclip aria-hidden className="size-4 text-muted-foreground" />
        Documentos de apoyo
      </p>

      <div className="flex flex-wrap gap-2">
        {adjuntos.map((a) =>
          a.tipo === "imagen" ? (
            <button
              key={a.nombre}
              type="button"
              aria-pressed={abierto === a.nombre}
              onClick={() =>
                setAbierto(abierto === a.nombre ? null : a.nombre)
              }
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors",
                abierto === a.nombre
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border text-foreground/80 hover:bg-muted",
              )}
            >
              <IconoImagen aria-hidden className="size-3.5" />
              {a.nombre}
            </button>
          ) : (
            // Un PDF no se puede mirar de reojo: se abre aparte.
            <a
              key={a.nombre}
              href={urlAdjunto(sid, a.nombre)}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground/80 transition-colors hover:bg-muted"
            >
              <FileText aria-hidden className="size-3.5" />
              {a.nombre}
            </a>
          ),
        )}
      </div>

      {abiertoAhora ? (
        <figure className="relative m-0 overflow-auto rounded-lg border border-border bg-muted/30">
          <button
            type="button"
            aria-label={`Cerrar ${abiertoAhora.nombre}`}
            onClick={() => setAbierto(null)}
            className="absolute top-2 right-2 rounded-md bg-card/90 p-1 text-muted-foreground shadow-sm hover:text-foreground"
          >
            <X aria-hidden className="size-4" />
          </button>
          {/* Un diagrama es ancho: se deja a tamaño real y se desplaza, en vez
              de encogerlo hasta que no se lea. */}
          <img
            src={urlAdjunto(sid, abiertoAhora.nombre)}
            alt={abiertoAhora.nombre}
            className="max-w-none"
          />
        </figure>
      ) : null}
    </section>
  );
}
