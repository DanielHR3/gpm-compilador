import { Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ErrorApi, proponerExpediente } from "@/lib/api";

import ErrorDeCarga, { comoErrorDeCarga } from "./ErrorDeCarga";

const CLASE_INPUT =
  "text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground";

/**
 * Camino «Solo tengo el AS-IS»: se sube el AS-IS (y adjuntos, si hay) y el
 * compilador redacta el Diccionario y el TO-BE en segundo plano.
 */
export default function CargaAsIs({ onPropuesta }: { onPropuesta: (sid: string) => void }) {
  const [asIs, setAsIs] = useState<File | null>(null);
  const [apoyo, setApoyo] = useState<File[]>([]);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [enviando, setEnviando] = useState(false);

  const proponer = async () => {
    if (!asIs) return;
    setError(null);
    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("as_is", asIs);
      apoyo.forEach((a) => fd.append("adjuntos", a));
      const { sid } = await proponerExpediente(fd);
      onPropuesta(sid);
    } catch (e) {
      setError(comoErrorDeCarga(e));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Sube el Análisis AS-IS</h1>
        <p className="text-sm text-muted-foreground">
          El compilador redacta un borrador del Diccionario de Datos y de la Propuesta TO-BE a
          partir del AS-IS. Después los revisas uno por uno y decides si se usan. Suele tardar
          uno o dos minutos.
        </p>
      </header>

      <div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-4">
        <label htmlFor="as-is" className="text-sm font-medium">
          Análisis AS-IS
        </label>
        <input
          id="as-is"
          type="file"
          accept=".md,.docx,.pdf,text/markdown"
          className={CLASE_INPUT}
          onChange={(e) => setAsIs(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-4">
        <label htmlFor="apoyo-as-is" className="text-sm font-medium">
          Documentos de apoyo (opcional)
        </label>
        <p className="text-sm text-muted-foreground">
          Diagramas o PDF que quieras tener a la vista al revisar.
        </p>
        <input
          id="apoyo-as-is"
          type="file"
          multiple
          className={CLASE_INPUT}
          onChange={(e) => setApoyo(Array.from(e.target.files ?? []))}
        />
      </div>

      {error ? <ErrorDeCarga error={error} /> : null}

      <Button
        type="button"
        size="lg"
        onClick={proponer}
        disabled={asIs === null || enviando}
        className="h-11 self-stretch text-base sm:self-start"
      >
        <Sparkles aria-hidden className="size-4" />
        Proponer TO-BE y Diccionario
      </Button>
    </section>
  );
}
