import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { MetricaComparada } from "@/lib/types";

/**
 * Captura de un dato que no sale de los documentos. El compilador no lo
 * infiere: lo escribe una persona y queda rotulado «declarado».
 *
 * Lo escrito se conserva si guardar falla: volver a teclear dos cifras por un
 * tropiezo de red es la clase de friccion que esta vista viene a señalar.
 */
export default function CapturaMetrica({
  metrica,
  onGuardar,
}: {
  metrica: MetricaComparada;
  onGuardar: (antes: string, despues: string) => Promise<void>;
}) {
  const id = useId();
  const [antes, setAntes] = useState(metrica.antes.origen === "declarado" ? metrica.antes.texto : "");
  const [despues, setDespues] = useState(
    metrica.despues.origen === "declarado" ? metrica.despues.texto : "",
  );
  // Con algo ya declarado, guardar en blanco lo quita y vuelve a lo contado.
  const habiaDeclarado =
    metrica.antes.origen === "declarado" || metrica.despues.origen === "declarado";
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await onGuardar(antes.trim(), despues.trim());
    } catch {
      setError("No se pudo guardar. Lo que escribiste sigue aquí; inténtalo otra vez.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="flex flex-col gap-2 border-t border-border/60 pt-3">
      <p className="text-xs text-muted-foreground">
        Escribe solo el número, o el número con la misma unidad en los dos lados.
        {habiaDeclarado ? " Para quitar lo declarado, deja los dos en blanco y guarda." : ""}
      </p>
      <div className="flex gap-2">
        <label htmlFor={`${id}-antes`} className="flex flex-1 flex-col gap-1 text-xs">
          Antes
          <Input id={`${id}-antes`} value={antes} maxLength={80}
                 onChange={(e) => setAntes(e.target.value)} />
        </label>
        <label htmlFor={`${id}-despues`} className="flex flex-1 flex-col gap-1 text-xs">
          Después
          <Input id={`${id}-despues`} value={despues} maxLength={80}
                 onChange={(e) => setDespues(e.target.value)} />
        </label>
      </div>
      {error ? <p role="alert" className="text-xs text-destructive">{error}</p> : null}
      <Button type="submit" size="sm" variant="outline"
              disabled={
                guardando || (!habiaDeclarado && antes.trim() === "" && despues.trim() === "")
              }>
        {guardando ? "Guardando…" : "Guardar"}
      </Button>
    </form>
  );
}
