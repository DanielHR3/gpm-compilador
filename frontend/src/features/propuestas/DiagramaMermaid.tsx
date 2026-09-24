import { useEffect, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "cn";

const RE_BLOQUE = /```mermaid\s*\n([\s\S]*?)```/;

/** El primer bloque ```mermaid``` del texto: es el que lee el compilador. */
export function primerBloqueMermaid(texto: string): string | null {
  const m = RE_BLOQUE.exec(texto);
  return m ? m[1].trim() : null;
}

type Props = {
  texto: string;
  retardoMs?: number;
  /** Lienzo alto (70 % de la ventana) con zoom y pantalla completa. */
  grande?: boolean;
};

/**
 * Dibuja el diagrama del TO-BE mientras se edita. `mermaid` se carga con
 * `import()` la primera vez que hace falta: pesa mas que el resto de la SPA
 * junta y solo esta pantalla lo usa. `securityLevel: "strict"` deja los
 * `<br/>` de las etiquetas (los usan los diagramas del equipo) y bloquea
 * cualquier `<script>` o `onclick` que venga en el texto.
 */
export default function DiagramaMermaid({ texto, retardoMs = 600, grande = false }: Props) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "_");
  const [svg, setSvg] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [escala, setEscala] = useState(1);
  const marco = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let vivo = true;
    const timer = setTimeout(async () => {
      const codigo = primerBloqueMermaid(texto);
      if (codigo === null) {
        if (vivo) {
          setSvg(null);
          setAviso("El texto no tiene un bloque ```mermaid``` que dibujar.");
        }
        return;
      }
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
        const r = await mermaid.render(`dg${id}`, codigo);
        if (vivo) {
          setSvg(r.svg);
          setAviso(null);
        }
      } catch (e) {
        if (vivo) {
          // El mensaje de mermaid dice la linea y el trozo que no entiende
          // («Parse error on line 7: …»): sin el, la persona no sabe que corregir.
          const detalle = e instanceof Error ? e.message : String(e);
          setSvg(null);
          setAviso(
            "No se pudo dibujar el diagrama con el texto actual; revisa la sintaxis del bloque " +
              `mermaid. ${detalle}`,
          );
        }
      }
    }, retardoMs);
    return () => {
      vivo = false;
      clearTimeout(timer);
    };
  }, [texto, retardoMs, id]);

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium">Diagrama compilable (el primero del texto)</p>
      {aviso ? (
        <p role="status" className="whitespace-pre-wrap text-sm text-muted-foreground">
          {aviso}
        </p>
      ) : null}
      {svg ? (
        <div
          ref={marco}
          className={cn(
            "relative overflow-auto rounded-md border border-border bg-card p-3",
            grande && "h-[70vh]",
          )}
        >
          {grande ? (
            <div className="sticky top-0 z-10 flex justify-end gap-1 pb-2">
              <Button type="button" size="sm" variant="outline" aria-label="Alejar"
                onClick={() => setEscala((e) => Math.max(0.5, e - 0.25))}>
                −
              </Button>
              <Button type="button" size="sm" variant="outline" aria-label="Ajustar"
                onClick={() => setEscala(1)}>
                Ajustar
              </Button>
              <Button type="button" size="sm" variant="outline" aria-label="Acercar"
                onClick={() => setEscala((e) => Math.min(3, e + 0.25))}>
                +
              </Button>
              {document.fullscreenEnabled ? (
                <Button type="button" size="sm" variant="outline" aria-label="Pantalla completa"
                  onClick={() => void marco.current?.requestFullscreen()}>
                  Pantalla completa
                </Button>
              ) : null}
            </div>
          ) : null}
          <div
            data-testid="lienzo-diagrama"
            className="origin-top-left transition-transform"
            style={{ transform: `scale(${escala})` }}
            // SVG que produce mermaid con securityLevel strict (DOMPurify) a
            // partir del texto del TO-BE: puede venir del modelo o de otra
            // persona; lo protegen strict y la CSP, que no permite scripts en
            // linea.
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      ) : null}
    </div>
  );
}
