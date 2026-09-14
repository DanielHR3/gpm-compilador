import { useState } from "react";
import type { DragEvent } from "react";
import { ArrowRight, FileText, UploadCloud, FileWarning } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "cn";
import { crearExpediente, ErrorApi } from "@/lib/api";
import type { EstadoExpediente } from "@/lib/types";

/** Las cuatro llaves multipart que acepta `POST /api/v1/expedientes`. */
type CampoInsumo = "as_is" | "to_be" | "diccionario" | "vistas";

type DefCampo = {
  campo: CampoInsumo;
  etiqueta: string;
  obligatorio: boolean;
  ayuda: string;
  /** Ruta de la plantilla de ejemplo para este insumo, si tiene una. Los
   * insumos con formato propenso a error (TO-BE: carriles/`@@campo` en el
   * Mermaid; Diccionario: catálogos, nombres técnicos) llevan un ejemplo
   * descargable — As Is/Vistas no tienen un formato tan rígido que enseñar. */
  plantilla?: string;
};

const CAMPOS: readonly DefCampo[] = [
  {
    campo: "as_is",
    etiqueta: "As Is",
    obligatorio: false,
    ayuda: "Proceso actual (opcional).",
  },
  {
    campo: "to_be",
    etiqueta: "To Be",
    obligatorio: false,
    ayuda: "Proceso objetivo (opcional).",
    plantilla: "/descargar-plantilla-tobe",
  },
  {
    campo: "diccionario",
    etiqueta: "Diccionario",
    obligatorio: true,
    ayuda: "Diccionario de datos (obligatorio).",
    plantilla: "/descargar-plantilla",
  },
  {
    campo: "vistas",
    etiqueta: "Vistas",
    obligatorio: false,
    ayuda: "Definicion de vistas (opcional).",
  },
];

/** Tope de subida por archivo. Copia estatica: el 413 puede no traer `limite_mb`. */
const LIMITE_POR_ARCHIVO = "10 MB";

type Slots = Record<CampoInsumo, File | null>;

const SLOTS_VACIOS: Slots = {
  as_is: null,
  to_be: null,
  diccionario: null,
  vistas: null,
};

export default function CargaInsumos({
  onListo,
}: {
  onListo: (est: EstadoExpediente) => void;
}) {
  const [slots, setSlots] = useState<Slots>(SLOTS_VACIOS);
  // Diagramas y PDF que el compilador no puede leer pero el analista necesita
  // a la vista mientras resuelve los huecos.
  const [apoyo, setApoyo] = useState<File[]>([]);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [sobrevolando, setSobrevolando] = useState<CampoInsumo | null>(null);

  const asignar = (campo: CampoInsumo, archivo: File | null) => {
    setSlots((prev) => ({ ...prev, [campo]: archivo }));
  };

  const alSoltar =
    (campo: CampoInsumo) => (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setSobrevolando(null);
      const archivo = e.dataTransfer.files[0];
      if (archivo) asignar(campo, archivo);
    };

  const enviar = async () => {
    setError(null);
    setEnviando(true);
    try {
      const fd = new FormData();
      (Object.keys(slots) as CampoInsumo[]).forEach((campo) => {
        const archivo = slots[campo];
        if (archivo) fd.append(campo, archivo);
      });
      apoyo.forEach((a) => fd.append("adjuntos", a));
      const est = await crearExpediente(fd);
      onListo(est);
    } catch (e) {
      if (e instanceof ErrorApi) {
        setError(e);
      } else {
        throw e;
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main className="flex flex-col gap-8 text-foreground">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-bold tracking-tight">Carga de insumos</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          Arrastra un archivo sobre cada zona o eligelo con el selector. El
          Diccionario es obligatorio; el resto ayuda a extraer más completo.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        {CAMPOS.map(({ campo, etiqueta, obligatorio, ayuda, plantilla }) => {
          const inputId = `insumo-${campo}`;
          const archivo = slots[campo];
          const activa = sobrevolando === campo;
          return (
            <Card
              key={campo}
              className={cn(
                "gap-3 transition-shadow",
                obligatorio && "ring-2 ring-primary/30",
              )}
            >
              <CardHeader className="flex items-center justify-between gap-2 space-y-0">
                <CardTitle className="flex items-center gap-2">
                  {etiqueta}
                </CardTitle>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium",
                    obligatorio
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {obligatorio ? "Obligatorio" : "Opcional"}
                </span>
              </CardHeader>
              <CardContent>
                {/* `label`/`input` van como hermanos explícitos (htmlFor/id,
                    NO label-envuelve-input): las pruebas ubican la zona con
                    `getByLabelText(...).closest("div")`, que resuelve al
                    input y sube al div más cercano -- si el input quedara
                    anidado dentro de otro elemento no-div, ese `closest`
                    dejaría de encontrar la zona con los manejadores de
                    arrastre. */}
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setSobrevolando(campo);
                  }}
                  onDragLeave={() => setSobrevolando(null)}
                  onDrop={alSoltar(campo)}
                  className={cn(
                    "flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-5 text-center text-sm transition-colors",
                    activa
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/40 hover:bg-muted/40",
                  )}
                >
                  {archivo ? (
                    <FileText
                      aria-hidden
                      className="size-6 text-primary"
                      strokeWidth={1.75}
                    />
                  ) : (
                    <UploadCloud
                      aria-hidden
                      className="size-6 text-muted-foreground"
                      strokeWidth={1.75}
                    />
                  )}
                  <span
                    data-testid={`nombre-${campo}`}
                    className="max-w-full truncate font-medium text-foreground"
                  >
                    {archivo ? archivo.name : "Sin archivo"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {ayuda}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Elegir{" "}
                    <label
                      htmlFor={inputId}
                      className="cursor-pointer font-medium text-primary underline underline-offset-2"
                    >
                      {etiqueta}
                    </label>
                  </span>
                  <input
                    id={inputId}
                    type="file"
                    className="sr-only"
                    onChange={(e) =>
                      asignar(campo, e.target.files?.[0] ?? null)
                    }
                  />
                </div>
                {plantilla ? (
                  <a
                    className="mt-2 inline-block text-xs text-primary underline underline-offset-2"
                    href={plantilla}
                  >
                    Descargar plantilla de ejemplo ({etiqueta})
                  </a>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {error ? (
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
        >
          {error.status === 413 ? (
            <>
              <p className="font-semibold">Archivo demasiado grande</p>
              <p>
                El limite por archivo es {LIMITE_POR_ARCHIVO}. Reduce o divide
                estos archivos:
              </p>
              <div className="flex flex-col gap-1.5">
                {(error.archivos ?? []).map((nombre) => (
                  <p
                    key={nombre}
                    className="flex items-center gap-2 rounded-md border border-destructive/30 bg-card/60 px-3 py-1.5 font-medium break-all"
                  >
                    <FileWarning aria-hidden className="size-4 shrink-0" />
                    {nombre}
                  </p>
                ))}
              </div>
            </>
          ) : (
            <p>{error.message}</p>
          )}
        </div>
      ) : null}

      <div className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-4">
        <label
          htmlFor="adjuntos-apoyo"
          className="text-sm font-medium text-foreground"
        >
          Documentos de apoyo
        </label>
        <p className="text-sm text-muted-foreground">
          Diagramas en imagen, PDF escaneados, oficios. No se leen para
          compilar, pero los verás junto a los huecos mientras los resuelves.
        </p>
        <input
          id="adjuntos-apoyo"
          type="file"
          multiple
          className="text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground"
          onChange={(e) => setApoyo(Array.from(e.target.files ?? []))}
        />
        {apoyo.length > 0 ? (
          <p className="text-sm text-foreground">
            {apoyo.length === 1
              ? "1 documento adjunto"
              : `${apoyo.length} documentos adjuntos`}
          </p>
        ) : null}
      </div>

      <Button
        type="button"
        size="lg"
        onClick={enviar}
        disabled={slots.diccionario === null || enviando}
        className="h-11 text-base"
      >
        Extraer
        <ArrowRight aria-hidden className="size-4" />
      </Button>

      <footer className="text-sm text-muted-foreground">
        <a className="text-primary underline underline-offset-2" href="/historial">
          Ver expedientes anteriores
        </a>
      </footer>
    </main>
  );
}
