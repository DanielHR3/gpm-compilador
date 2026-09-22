import { useEffect, useRef, useState } from "react";
import { Download, ExternalLink, Eye, FileCode2, FileText, FlaskConical, Lock, Package } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "cn";
import { urlGpm, urlManifiesto } from "@/lib/api";
import { documentoDeObservaciones } from "@/features/huecos/observaciones";
import type { EstadoExpediente, Hueco } from "@/lib/types";

import { descargasDe, resumenDe, type ClaveDescarga, type Descarga } from "./descargas";

/**
 * Seccion «Descarga»: lo que el analista se lleva del expediente.
 *
 * Antes era una lista de enlaces de texto en un riel de 240 px. Con cuatro
 * archivos que se llaman parecido —dos `.gpm`, un manifiesto, unas
 * observaciones— elegir mal cuesta una importacion a produccion que hay que
 * deshacer, y no habia forma de mirar dentro sin bajarlos primero.
 *
 * Cada tarjeta dice que lleva el archivo antes de abrirlo, y la vista previa
 * ensena el contenido de verdad: el `.gpm` se pide al servidor —es el mismo
 * que se descarga, no una reconstruccion— y las observaciones se arman aqui,
 * que es donde vive su castellano.
 */

/** Acoplado a la duracion de `destello-entrega` en index.css. */
const MS_DESTELLO = 1200;

const ICONO: Record<ClaveDescarga, typeof Download> = {
  gpm_produccion: Package,
  gpm_pruebas: FlaskConical,
  observaciones: FileText,
  manifiesto: FileCode2,
  vistas: ExternalLink,
};

/** «Trámite de Prueba - 2026-09-18», sin barras ni dos puntos. */
function nombreDeArchivo(estado: EstadoExpediente): string {
  const t = (estado.manifiesto as { tramite?: { nombre?: unknown } }).tramite?.nombre;
  const nombre = (typeof t === "string" && t ? t : "expediente").replace(/[/\\:*?"<>|]/g, " ");
  return `${nombre} - ${new Date().toISOString().slice(0, 10)}`;
}

function urlDe(clave: ClaveDescarga, sid: string): string {
  if (clave === "manifiesto") return urlManifiesto(sid);
  if (clave === "vistas") return `/vistas/${sid}`;
  return urlGpm(sid, clave === "gpm_pruebas" ? "pruebas" : "produccion");
}

/** Un `.gpm` viaja en una sola linea a proposito (la forma es byte a byte).
    Leerlo asi es imposible, asi que en la vista previa se sangra — y se dice. */
function comoSeLee(clave: ClaveDescarga, texto: string): string {
  if (clave !== "gpm_produccion" && clave !== "gpm_pruebas") return texto;
  try {
    return JSON.stringify(JSON.parse(texto), null, 2);
  } catch {
    return texto;
  }
}

function pesoDe(texto: string): string {
  const bytes = new Blob([texto]).size;
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}

export default function PanelDescargas({
  sid,
  desbloqueado,
  bloqueantes,
  fraseBloqueo,
  estado,
}: {
  sid: string;
  desbloqueado: boolean;
  bloqueantes: Hueco[];
  fraseBloqueo: (n: number) => string;
  estado: EstadoExpediente;
}) {
  const descargas = descargasDe(estado, desbloqueado, fraseBloqueo(bloqueantes.length));
  const panel = useRef<HTMLElement>(null);

  // Entrar con `/revisar/xxx#entrega` no bajaba a las descargas: cuando el
  // navegador resuelve el ancla, la SPA todavia no ha pintado el panel. Al
  // montar, si el ancla es esta, se baja a mano.
  useEffect(() => {
    if (window.location.hash !== "#entrega") return;
    panel.current?.scrollIntoView();
    panel.current?.focus();
  }, []);
  const [viendo, setViendo] = useState<Descarga | null>(null);
  const [texto, setTexto] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // El aterrizaje desde el menu se senala con un destello que termina solo:
  // un anillo de foco permanente alrededor de toda la seccion parecia error.
  // Se apaga por reloj y no por `animationend`: con movimiento reducido la
  // animacion no corre y ese evento nunca llegaria.
  const [destello, setDestello] = useState(false);
  useEffect(() => {
    if (!destello) return;
    const reloj = setTimeout(() => setDestello(false), MS_DESTELLO);
    return () => clearTimeout(reloj);
  }, [destello]);

  /** Arma el .md en el navegador. No pasa por el servidor: el castellano de
      las observaciones vive en `redactarHueco`, de este lado. */
  function textoDeObservaciones(): string {
    return documentoDeObservaciones(estado);
  }

  function descargarObservaciones() {
    const url = URL.createObjectURL(
      new Blob([textoDeObservaciones()], { type: "text/markdown" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `Observaciones - ${nombreDeArchivo(estado)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function abrirVistaPrevia(d: Descarga) {
    setViendo(d);
    setTexto(null);
    setError(null);
    if (d.clave === "observaciones") {
      setTexto(textoDeObservaciones());
      return;
    }
    try {
      const res = await fetch(urlDe(d.clave, sid));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setTexto(comoSeLee(d.clave, await res.text()));
    } catch {
      setError("No se pudo leer el archivo. Puedes descargarlo de todos modos.");
    }
  }

  function cerrar() {
    setViendo(null);
    setTexto(null);
    setError(null);
  }

  return (
    <section
      ref={panel}
      id="entrega"
      aria-label="Descarga"
      // El salto `#entrega` del menu tiene que dejar el foco aqui: si no, el
      // teclado sigue al principio de la pagina y el boton parece muerto.
      // `focus:` y no `focus-visible:` porque el foco llega por un clic.
      tabIndex={-1}
      data-destello={destello || undefined}
      onFocus={(e) => {
        if (e.target === e.currentTarget) setDestello(true);
      }}
      className="panel-entrega flex flex-col gap-4 scroll-mt-6 rounded-lg border border-border bg-card p-5 focus:outline-none"
    >
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
            Descarga
          </p>
          <h2 className="text-lg font-bold tracking-tight">Lo que te llevas</h2>
          <p className="max-w-prose text-sm text-muted-foreground">
            Mira dentro de cada archivo antes de bajarlo.{" "}
            <span className="font-medium text-foreground">Producción</span> es el que
            se importa de verdad;{" "}
            <span className="font-medium text-foreground">pruebas</span> trae datos de
            ejemplo ya capturados.
          </p>
          <p className="text-xs tabular-nums text-foreground/80">{resumenDe(estado)}</p>
        </div>
        <p
          className={cn(
            "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
            desbloqueado
              ? "bg-emerald-50 text-emerald-800"
              : "bg-destructive/10 text-destructive",
          )}
        >
          {desbloqueado ? null : <Lock aria-hidden className="size-3" />}
          {desbloqueado ? "Listo" : fraseBloqueo(bloqueantes.length)}
        </p>
      </header>

      <ul className="grid min-w-0 grid-cols-[repeat(auto-fill,minmax(min(15.5rem,100%),1fr))] gap-3">
        {descargas.map((d) => {
          const Icono = ICONO[d.clave];
          // Producion y pruebas se llaman casi igual y elegir mal cuesta una
          // importacion que hay que deshacer: el de verdad va con boton lleno;
          // el de pruebas, con contorno y una franja arena que se ve de lejos.
          const secundaria = d.clave === "gpm_pruebas";
          return (
            <li key={d.clave}>
              <div
                data-enfasis={secundaria ? "secundaria" : "primaria"}
                className={cn(
                  "flex h-full flex-col gap-3 rounded-lg border border-border bg-background p-4 transition",
                  secundaria && "border-t-4 border-t-secondary",
                  d.bloqueada
                    ? "opacity-70"
                    : "hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md",
                )}
              >
                <header className="flex items-start gap-3">
                  <span
                    aria-hidden
                    className={cn(
                      "flex size-9 shrink-0 items-center justify-center rounded-md",
                      d.bloqueada
                        ? "bg-muted text-muted-foreground"
                        : "bg-primary/10 text-primary",
                    )}
                  >
                    {d.bloqueada ? <Lock className="size-4" /> : <Icono className="size-4" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold leading-tight">{d.titulo}</h3>
                    <p className="font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
                      {d.formato}
                    </p>
                  </div>
                </header>

                <p className="text-xs leading-relaxed text-foreground/75">{d.proposito}</p>

                {d.detalles.length > 0 ? (
                  <ul className="flex flex-col gap-0.5 text-xs tabular-nums text-foreground">
                    {d.detalles.map((linea) => (
                      <li key={linea}>{linea}</li>
                    ))}
                  </ul>
                ) : null}

                {d.motivo ? (
                  <p className="inline-flex w-fit items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-[0.7rem] font-semibold text-destructive">
                    <Lock aria-hidden className="size-3" />
                    Bloqueado
                  </p>
                ) : null}

                <footer className="mt-auto flex flex-wrap gap-2 pt-1">
                  {d.clave === "vistas" ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      render={
                        <a href={urlDe(d.clave, sid)} target="_blank" rel="noreferrer">
                          Abrir
                        </a>
                      }
                    />
                  ) : (
                    <>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="min-w-[7rem] flex-1"
                        aria-label={`Vista previa de ${d.titulo}`}
                        onClick={() => abrirVistaPrevia(d)}
                      >
                        <Eye aria-hidden />
                        Vista previa
                      </Button>
                      {d.clave === "observaciones" ? (
                        <Button
                          type="button"
                          size="sm"
                          className="flex-1"
                          onClick={descargarObservaciones}
                        >
                          <Download aria-hidden />
                          Descargar
                        </Button>
                      ) : d.bloqueada ? (
                        <Button
                          type="button"
                          variant={secundaria ? "outline" : "default"}
                          size="sm"
                          className="flex-1"
                          disabled
                          // El boton apagado no explica nada por si solo; el
                          // motivo esta en la cabecera y aqui al pasar encima.
                          title={d.motivo ?? undefined}
                        >
                          <Download aria-hidden />
                          Descargar
                        </Button>
                      ) : (
                        <Button
                          variant={secundaria ? "outline" : "default"}
                          size="sm"
                          className="flex-1"
                          render={
                            // El `.gpm` viene con `Content-Disposition` y se
                            // guarda solo; el manifiesto no, y sin esto un
                            // boton que dice «Descargar» abria el YAML en la
                            // pestana. `download` tambien le pone nombre.
                            <a
                              href={urlDe(d.clave, sid)}
                              download={
                                d.clave === "manifiesto"
                                  ? `Manifiesto - ${nombreDeArchivo(estado)}.yaml`
                                  : undefined
                              }
                            >
                              <Download aria-hidden />
                              Descargar
                            </a>
                          }
                        />
                      )}
                    </>
                  )}
                </footer>
              </div>
            </li>
          );
        })}
      </ul>

      {viendo ? (
        <VistaPrevia
          descarga={viendo}
          texto={texto}
          error={error}
          onCerrar={cerrar}
        />
      ) : null}
    </section>
  );
}

function VistaPrevia({
  descarga,
  texto,
  error,
  onCerrar,
}: {
  descarga: Descarga;
  texto: string | null;
  error: string | null;
  onCerrar: () => void;
}) {
  const esGpm = descarga.clave.startsWith("gpm");
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Vista previa de ${descarga.titulo}`}
        onKeyDown={(e) => {
          if (e.key === "Escape") onCerrar();
        }}
        className="flex max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-xl bg-card shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-border p-4">
          <div>
            <h3 className="text-sm font-semibold">{descarga.titulo}</h3>
            <p className="text-xs text-muted-foreground">
              {descarga.formato}
              {texto ? ` · ${pesoDe(texto)}` : null}
              {esGpm && texto
                ? " · mostrado con sangría para leerlo; el archivo va en una sola línea"
                : null}
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            autoFocus
            onClick={onCerrar}
            aria-label="Cerrar vista previa"
          >
            ✕
          </Button>
        </header>
        <div className="min-h-0 flex-1 overflow-auto bg-muted/40 p-4">
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : texto === null ? (
            <p className="text-sm text-muted-foreground">Leyendo el archivo…</p>
          ) : (
            <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-foreground">
              {texto}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
