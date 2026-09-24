import { useEffect, useId, useState } from "react";

const RE_BLOQUE = /```mermaid\s*\n([\s\S]*?)```/;

/** El primer bloque ```mermaid``` del texto: es el que lee el compilador. */
export function primerBloqueMermaid(texto: string): string | null {
  const m = RE_BLOQUE.exec(texto);
  return m ? m[1].trim() : null;
}

type Props = { texto: string; retardoMs?: number };

/**
 * Dibuja el diagrama del TO-BE mientras se edita. `mermaid` se carga con
 * `import()` la primera vez que hace falta: pesa mas que el resto de la SPA
 * junta y solo esta pantalla lo usa. `securityLevel: "strict"` deja los
 * `<br/>` de las etiquetas (los usan los diagramas del equipo) y bloquea
 * cualquier `<script>` o `onclick` que venga en el texto.
 */
export default function DiagramaMermaid({ texto, retardoMs = 600 }: Props) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "_");
  const [svg, setSvg] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

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
          className="overflow-x-auto rounded-md border border-border bg-card p-3"
          // SVG que produce mermaid con securityLevel strict a partir del texto
          // que la propia persona esta editando; no viene de otro usuario.
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : null}
    </div>
  );
}
