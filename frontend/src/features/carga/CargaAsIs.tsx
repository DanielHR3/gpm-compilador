import { FileText, Sparkles, UploadCloud } from "lucide-react";
import { useState } from "react";
import type { DragEvent } from "react";

import { cn } from "cn";

import AvisoModoPruebas, { useModoPruebas } from "@/components/AvisoModoPruebas";
import { Button } from "@/components/ui/button";
import { ErrorApi, proponerExpediente } from "@/lib/api";

import ErrorDeCarga, { comoErrorDeCarga } from "./ErrorDeCarga";

/**
 * Camino «Solo tengo el AS-IS»: se sube el AS-IS (y adjuntos, si hay) y el
 * compilador redacta el Diccionario y el TO-BE en segundo plano.
 */
export default function CargaAsIs({ onPropuesta }: { onPropuesta: (sid: string) => void }) {
  const [asIs, setAsIs] = useState<File | null>(null);
  const [apoyo, setApoyo] = useState<File[]>([]);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [enviando, setEnviando] = useState(false);
  const pruebas = useModoPruebas();
  const [sobre, setSobre] = useState(false);
  const [sobreApoyo, setSobreApoyo] = useState(false);

  const alSoltar = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setSobre(false);
    const archivo = e.dataTransfer.files[0];
    if (archivo) setAsIs(archivo);
  };

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
          partir del AS-IS. Después los revisas uno por uno y decides si se usan. Suele tardar de dos a cinco minutos.
        </p>
      </header>

      {pruebas ? <AvisoModoPruebas /> : null}

      {/* Toda la zona es el control, como en la carga de carpeta: la caja
          punteada invita a hacer clic en cualquier parte, y antes solo
          respondia el boton nativo (reportado el 2026-09-24: «el dialogo ni
          siquiera abre»). Tambien acepta el archivo arrastrado. */}
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">Análisis AS-IS</span>
        <input
          id="as-is"
          type="file"
          aria-label="Análisis AS-IS"
          accept=".md,.docx,.pdf,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          onChange={(e) => setAsIs(e.target.files?.[0] ?? null)}
        />
        <label
          htmlFor="as-is"
          onDragOver={(e) => {
            e.preventDefault();
            setSobre(true);
          }}
          onDragLeave={() => setSobre(false)}
          onDrop={alSoltar}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center text-sm transition-colors",
            "focus-within:ring-2 focus-within:ring-ring",
            sobre ? "border-primary bg-primary/5" : "border-border bg-card hover:border-primary/60",
          )}
        >
          {asIs ? (
            <>
              <FileText aria-hidden className="size-8 text-primary" />
              <span className="font-medium text-foreground">{asIs.name}</span>
              <span className="text-muted-foreground">Haz clic para cambiarlo</span>
            </>
          ) : (
            <>
              <UploadCloud aria-hidden className="size-8 text-muted-foreground" />
              <span className="text-foreground">Arrastra el AS-IS aquí o haz clic para elegirlo</span>
              <span className="text-muted-foreground">.md, .docx o PDF con texto</span>
            </>
          )}
        </label>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">Documentos de apoyo (opcional)</span>
        <input
          id="apoyo-as-is"
          type="file"
          multiple
          aria-label="Documentos de apoyo (opcional)"
          className="sr-only"
          onChange={(e) => setApoyo(Array.from(e.target.files ?? []))}
        />
        <label
          htmlFor="apoyo-as-is"
          onDragOver={(e) => {
            e.preventDefault();
            setSobreApoyo(true);
          }}
          onDragLeave={() => setSobreApoyo(false)}
          onDrop={(e) => {
            e.preventDefault();
            setSobreApoyo(false);
            setApoyo(Array.from(e.dataTransfer.files));
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed p-5 text-center text-sm transition-colors",
            "focus-within:ring-2 focus-within:ring-ring",
            sobreApoyo ? "border-primary bg-primary/5" : "border-border hover:border-primary/60",
          )}
        >
          {apoyo.length > 0 ? (
            <>
              <span className="font-medium text-foreground">
                {apoyo.length === 1 ? "1 documento de apoyo" : `${apoyo.length} documentos de apoyo`}
              </span>
              <span className="text-muted-foreground">Haz clic para cambiarlos</span>
            </>
          ) : (
            <>
              <span className="text-foreground">
                Arrastra aquí diagramas o PDF, o haz clic para elegirlos
              </span>
              <span className="text-muted-foreground">
                Los tendrás a la vista al revisar; no se envían al modelo.
              </span>
            </>
          )}
        </label>
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
