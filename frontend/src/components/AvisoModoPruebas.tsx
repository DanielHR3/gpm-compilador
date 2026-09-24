import { FlaskConical } from "lucide-react";
import { useEffect, useState } from "react";

import { leerCapacidades } from "@/lib/api";

/**
 * Si el servidor esta en modo de pruebas: el candado de la Fase 3 abierto sin
 * la licencia de Planeacion (decision del 2026-09-24, uso interno de la DSA y
 * la DGT). Si la consulta falla, se asume que no.
 */
export function useModoPruebas(): boolean {
  const [pruebas, setPruebas] = useState(false);
  useEffect(() => {
    let vivo = true;
    leerCapacidades()
      .then((c) => {
        if (vivo) setPruebas(c.pruebas === true);
      })
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, []);
  return pruebas;
}

/**
 * Aviso informativo, no alarma: quien lo lee es del equipo interno y solo
 * necesita saber con que se esta procesando su AS-IS y por que.
 */
export default function AvisoModoPruebas() {
  return (
    <aside
      role="note"
      aria-label="Modo de pruebas"
      className="flex items-start gap-2 rounded-md border border-border bg-muted p-3 text-sm text-foreground"
    >
      <FlaskConical aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
      <p>
        <strong className="font-semibold">Modo de pruebas</strong> — uso interno de la DSA y la
        DGT. Mientras llegan las credenciales de OpenAI, el AS-IS se procesa con Gemini.
      </p>
    </aside>
  );
}
