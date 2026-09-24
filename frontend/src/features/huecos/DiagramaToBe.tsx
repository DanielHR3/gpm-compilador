import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DiagramaMermaid from "@/features/propuestas/DiagramaMermaid";
import { leerToBe } from "@/lib/api";

type Flujo = {
  tareas?: { pantallas?: string[] }[];
  conexiones?: { de: string; cuando?: unknown }[];
};

function plural(n: number, s: string, p: string) {
  return `${n} ${n === 1 ? s : p}`;
}

/** «2 tareas · 1 decisión», contado del manifiesto que ya se extrajo. */
function conteo(manifiesto: Record<string, unknown>): string {
  const f = (manifiesto.flujo ?? {}) as Flujo;
  const tareas = (f.tareas ?? []).filter((t) => (t.pantallas ?? []).length > 0).length;
  const decisiones = new Set((f.conexiones ?? []).filter((c) => c.cuando).map((c) => c.de)).size;
  return `${plural(tareas, "tarea", "tareas")} · ${plural(decisiones, "decisión", "decisiones")}`;
}

/**
 * El TO-BE dibujado en la revision de huecos. Plegado por omision: la lista
 * de huecos sigue siendo lo principal; el diagrama se abre cuando ayuda
 * (sobre todo con los huecos de flujo). Sin TO-BE en la sesion, no aparece.
 */
export default function DiagramaToBe({
  sid,
  manifiesto,
}: {
  sid: string;
  manifiesto: Record<string, unknown>;
}) {
  const [texto, setTexto] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const t = await leerToBe(sid);
        if (vivo) setTexto(t);
      } catch {
        if (vivo) setTexto(null);
      }
    })();
    return () => {
      vivo = false;
    };
  }, [sid]);

  if (texto === null) return null;
  return (
    <Card role="article" aria-label="Diagrama del TO-BE" className="py-4">
      <CardHeader>
        <CardTitle>Diagrama del TO-BE · {conteo(manifiesto)}</CardTitle>
        <CardAction>
          <Button type="button" variant="outline" size="sm" onClick={() => setAbierto((a) => !a)}>
            {abierto ? "Ocultar el diagrama" : "Ver el diagrama"}
          </Button>
        </CardAction>
      </CardHeader>
      {abierto ? (
        <CardContent>
          <DiagramaMermaid texto={texto} grande />
        </CardContent>
      ) : null}
    </Card>
  );
}
