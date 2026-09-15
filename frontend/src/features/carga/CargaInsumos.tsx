import { useState } from "react";
import type { DragEvent } from "react";
import { ArrowRight, Download, FileText, FolderOpen, UploadCloud, FileWarning } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Instrucciones from "@/components/Instrucciones";
import { cn } from "cn";
import { clasificar, crearExpediente, ErrorApi } from "@/lib/api";
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
  // Plantillas de los documentos que el tramite genera (oficios, acuses):
  // estas SI las lee el compilador, a diferencia de los adjuntos.
  const [plantillas, setPlantillas] = useState<File[]>([]);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [sobrevolando, setSobrevolando] = useState<CampoInsumo | null>(null);
  // Lo que el servidor no pudo decidir de la carpeta, y lo que dejó fuera.
  const [avisos, setAvisos] = useState<string[]>([]);
  const [ignorados, setIgnorados] = useState<string[]>([]);
  const [repartiendo, setRepartiendo] = useState(false);

  /**
   * Reparte una carpeta completa en las zonas.
   *
   * Se mandan solo los NOMBRES a `POST /clasificar` —no los bytes— y con la
   * respuesta se colocan los File que ya tiene el navegador. Así la carpeta no
   * viaja dos veces y el criterio de "qué es el Diccionario" vive en un solo
   * sitio, el servidor, que lo comparte con `gpmc extraer <carpeta>`.
   */
  const repartirCarpeta = async (archivos: File[]) => {
    if (archivos.length === 0) return;
    // `webkitRelativePath` trae la carpeta raíz delante: se recorta para que el
    // servidor vea las mismas rutas relativas que ve la CLI.
    const rutaDe = (f: File) => {
      const completa = (f as File & { webkitRelativePath?: string })
        .webkitRelativePath || f.name;
      const corte = completa.indexOf("/");
      return corte === -1 ? completa : completa.slice(corte + 1);
    };
    const porRuta = new Map(archivos.map((f) => [rutaDe(f), f]));

    setError(null);
    setRepartiendo(true);
    try {
      const a = await clasificar([...porRuta.keys()]);
      setSlots({
        as_is: a.as_is ? porRuta.get(a.as_is) ?? null : null,
        to_be: a.to_be ? porRuta.get(a.to_be) ?? null : null,
        diccionario: a.diccionario ? porRuta.get(a.diccionario) ?? null : null,
        vistas: a.vistas ? porRuta.get(a.vistas) ?? null : null,
      });
      setApoyo(a.adjuntos.map((r) => porRuta.get(r)).filter((f): f is File => !!f));
      setPlantillas(
        a.documentos.map((r) => porRuta.get(r)).filter((f): f is File => !!f),
      );
      setAvisos(a.avisos);
      setIgnorados(a.ignorados);
    } catch (e) {
      if (e instanceof ErrorApi) setError(e);
      else throw e;
    } finally {
      setRepartiendo(false);
    }
  };

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
      plantillas.forEach((d) => fd.append("documentos", d));
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
      <header className="flex flex-col gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Carga de insumos</h1>
        <Instrucciones
          id="insumos"
          resumen="Sube los documentos del trámite. Con el Diccionario basta para empezar; entre más subas, menos tendrás que contestar a mano después."
        >
          <p>
            <strong>Diccionario de Datos</strong> — obligatorio. De aquí salen
            las pantallas, los campos y sus catálogos. Sin él no hay nada que
            compilar.
          </p>
          <p>
            <strong>Propuesta TO-BE</strong> — de su diagrama sale el flujo:
            las tareas, las bifurcaciones y quién hace cada cosa.{" "}
            <strong>Análisis AS-IS</strong> — de aquí salen el nombre del
            trámite, la dependencia y la ficha RUTS.{" "}
            <strong>Vistas</strong> — referencia visual; no se compila.
          </p>
          <p>
            Los tres primeros se leen en <strong>Word, PDF con texto o
            Markdown</strong>. Un PDF escaneado es una imagen: no se puede leer,
            y si lo pones en una de esas zonas te dirá cuál es y por qué. Súbelo
            como documento de apoyo, que sirve para tenerlo a la vista mientras
            resuelves.
          </p>
          <p>
            Si tienes la carpeta completa tal como la entregó Simplificación,
            usa la zona de arriba: reparte cada archivo en su sitio y tú
            corriges lo que quede mal.
          </p>
        </Instrucciones>
      </header>

      <div className="flex flex-col gap-2 rounded-lg border border-dashed border-primary/40 bg-primary/5 p-4">
        <label
          htmlFor="carpeta-expediente"
          className="flex items-center gap-2 text-sm font-medium text-foreground"
        >
          <FolderOpen aria-hidden className="size-4 shrink-0 text-primary" />
          Carpeta del trámite
        </label>
        <p className="text-sm text-muted-foreground">
          Elige la carpeta completa tal como te la entregó Simplificación y yo
          acomodo cada archivo en su zona. Puedes corregir lo que quede mal
          antes de extraer.
        </p>
        <input
          id="carpeta-expediente"
          type="file"
          // `webkitdirectory` no está en los tipos de React, pero lo soportan
          // Chrome, Edge y Safari; sin él, el input se comporta como uno normal.
          {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
          multiple
          className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-medium"
          onChange={(e) => void repartirCarpeta([...(e.target.files ?? [])])}
        />
        {repartiendo ? (
          <p className="text-sm text-muted-foreground">Acomodando…</p>
        ) : null}
        {avisos.length > 0 ? (
          <div className="flex flex-col gap-1">
            {avisos.map((a) => (
              <p key={a} className="flex items-start gap-2 text-sm text-foreground">
                <FileWarning aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
                {a}
              </p>
            ))}
          </div>
        ) : null}
        {ignorados.length > 0 ? (
          <details className="text-sm text-muted-foreground">
            <summary className="cursor-pointer">
              {ignorados.length} ignorado{ignorados.length === 1 ? "" : "s"} (no
              son insumo ni apoyo)
            </summary>
            <ul className="mt-1 flex flex-col gap-0.5 pl-4">
              {ignorados.map((n) => (
                <li key={n} className="break-all">{n}</li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>

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
                  // Era un enlace subrayado de 12px al pie de la tarjeta, que
                  // es justo donde no se ve. Quien no sabe que existe una
                  // plantilla no la busca: tiene que verse que se puede hacer.
                  // `Button` de este proyecto no lleva `asChild` (no usa el
                  // Slot de Radix), asi que el enlace toma sus clases directo.
                  // El texto visible se queda corto, pero dos enlaces llamados
                  // igual son ambiguos para un lector de pantalla: el rotulo
                  // accesible dice de cual es.
                  <a
                    href={plantilla}
                    aria-label={`Descargar plantilla de ejemplo del ${etiqueta}`}
                    className={cn(
                      buttonVariants({ variant: "outline", size: "sm" }),
                      "mt-2 self-start",
                    )}
                  >
                    <Download aria-hidden className="size-4" />
                    Descargar plantilla
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
            </>
          ) : (
            <p className="font-semibold">{error.message}</p>
          )}
          {/* `archivos` lo manda tanto el 413 (nombres a secas) como el 422 de
              lectura ("NOMBRE: motivo"). Antes solo se pintaba en la rama del
              413, asi que un PDF escaneado daba "no se pudo leer el documento"
              sobre cuatro zonas de carga sin decir cual era -- y el backend ya
              sabia el nombre Y el motivo. */}
          {error.archivos?.length ? (
            <div className="flex flex-col gap-1.5">
              {error.archivos.map((entrada) => {
                const corte = entrada.indexOf(": ");
                const nombre = corte === -1 ? entrada : entrada.slice(0, corte);
                const motivo = corte === -1 ? null : entrada.slice(corte + 2);
                return (
                  <p
                    key={entrada}
                    className="flex items-start gap-2 rounded-md border border-destructive/30 bg-card/60 px-3 py-1.5 break-all"
                  >
                    <FileWarning aria-hidden className="mt-0.5 size-4 shrink-0" />
                    <span>
                      <span className="font-medium">{nombre}</span>
                      {motivo ? (
                        <span className="block text-xs opacity-90">{motivo}</span>
                      ) : null}
                    </span>
                  </p>
                );
              })}
            </div>
          ) : null}
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
          compilar, pero los verás junto a las inconsistencias mientras las resuelves.
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

      <div className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-4">
        <label
          htmlFor="documentos-plantillas"
          className="text-sm font-medium text-foreground"
        >
          Documentos que genera el trámite
        </label>
        <p className="text-sm text-muted-foreground">
          Oficios, acuses o constancias en Word, PDF con texto o{" "}
          <code>.md</code>, con <code>{"{{variables}}"}</code> que sean campos
          del Diccionario. El compilador los convierte en documentos PDF del
          trámite. Un PDF escaneado no se lee: súbelo como documento de apoyo.
        </p>
        <input
          id="documentos-plantillas"
          type="file"
          multiple
          accept=".md,.docx,.pdf,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground"
          onChange={(e) => setPlantillas(Array.from(e.target.files ?? []))}
        />
        {plantillas.length > 0 ? (
          <p className="text-sm text-foreground">
            {plantillas.length === 1
              ? "1 plantilla de documento"
              : `${plantillas.length} plantillas de documento`}
          </p>
        ) : null}
      </div>

      <Button
        type="button"
        size="lg"
        onClick={enviar}
        disabled={slots.diccionario === null || enviando}
        // Un CTA a todo lo ancho es convencion de telefono, donde el pulgar
        // necesita blanco. En escritorio hacia que la accion principal
        // pareciera una barra (976px en un contenedor de 1024) y perdiera
        // jerarquia frente a las tarjetas. No llevaba `w-full`: se estiraba
        // porque el <main> es flex en columna y estira a sus hijos.
        className="h-11 self-stretch text-base sm:self-start"
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
