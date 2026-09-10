import { useState } from "react";
import type { DragEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { crearExpediente, ErrorApi } from "@/lib/api";
import type { EstadoExpediente } from "@/lib/types";

/** Las cuatro llaves multipart que acepta `POST /api/v1/expedientes`. */
type CampoInsumo = "as_is" | "to_be" | "diccionario" | "vistas";

type DefCampo = {
  campo: CampoInsumo;
  etiqueta: string;
  obligatorio: boolean;
  ayuda: string;
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
  },
  {
    campo: "diccionario",
    etiqueta: "Diccionario",
    obligatorio: true,
    ayuda: "Diccionario de datos (obligatorio).",
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
  const [error, setError] = useState<ErrorApi | null>(null);
  const [enviando, setEnviando] = useState(false);

  const asignar = (campo: CampoInsumo, archivo: File | null) => {
    setSlots((prev) => ({ ...prev, [campo]: archivo }));
  };

  const alSoltar =
    (campo: CampoInsumo) => (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
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
    <main className="mx-auto flex min-h-svh max-w-3xl flex-col gap-6 bg-background p-8 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">Carga de insumos</h1>
        <p className="text-sm text-muted-foreground">
          Arrastra un archivo sobre cada zona o eligelo con el selector. El
          Diccionario es obligatorio.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        {CAMPOS.map(({ campo, etiqueta, obligatorio, ayuda }) => {
          const inputId = `insumo-${campo}`;
          const archivo = slots[campo];
          return (
            <Card key={campo}>
              <CardHeader>
                <CardTitle>
                  {etiqueta}
                  {obligatorio ? " *" : ""}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={alSoltar(campo)}
                  className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-4 text-sm"
                >
                  <label htmlFor={inputId} className="font-medium">
                    {etiqueta}
                  </label>
                  <span className="text-muted-foreground">{ayuda}</span>
                  {campo === "diccionario" ? (
                    <a
                      className="text-primary underline"
                      href="/descargar-plantilla"
                    >
                      Descargar plantilla de ejemplo
                    </a>
                  ) : null}
                  <input
                    id={inputId}
                    type="file"
                    onChange={(e) =>
                      asignar(campo, e.target.files?.[0] ?? null)
                    }
                  />
                  <span
                    data-testid={`nombre-${campo}`}
                    className="break-all text-foreground"
                  >
                    {archivo ? archivo.name : "Sin archivo"}
                  </span>
                </div>
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
              <ul className="list-disc pl-5">
                {(error.archivos ?? []).map((nombre) => (
                  <li key={nombre}>{nombre}</li>
                ))}
              </ul>
            </>
          ) : (
            <p>{error.message}</p>
          )}
        </div>
      ) : null}

      <Button
        type="button"
        onClick={enviar}
        disabled={slots.diccionario === null || enviando}
      >
        Extraer
      </Button>

      <footer className="text-sm text-muted-foreground">
        <a className="text-primary underline" href="/historial">
          Ver expedientes anteriores
        </a>
      </footer>
    </main>
  );
}
