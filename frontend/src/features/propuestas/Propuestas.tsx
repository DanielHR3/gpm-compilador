import { useCallback, useEffect, useRef, useState } from "react";

import { decidirDocumento, ErrorApi, leerGenerados, subirDocumento } from "@/lib/api";
import type {
  ClaveDocumento,
  EstadoExpediente,
  GeneradosOut,
  ResultadoDecision,
} from "@/lib/types";

import TarjetaPropuesta from "./TarjetaPropuesta";

type Props = { sid: string; onListo: (est: EstadoExpediente) => void };

/** Cada cuanto se pregunta por el estado mientras genera. */
const MS_CONSULTA = 3000;
/**
 * Tope: 3 minutos. Hasta cuatro llamadas al modelo caben de sobra; pasado eso,
 * algo se colgo y la persona debe recargar (el servidor conserva lo que haya).
 */
const MAX_CONSULTAS = 60;

/**
 * Fase 3: el Diccionario y el TO-BE que el compilador propuso desde el AS-IS.
 * Se decide por documento; cuando los dos quedan resueltos el servidor
 * devuelve el expediente ya extraido y se entra al wizard de siempre.
 */
export default function Propuestas({ sid, onListo }: Props) {
  const [g, setG] = useState<GeneradosOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [agotado, setAgotado] = useState(false);
  const consultas = useRef(0);

  useEffect(() => {
    let vivo = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const consultar = async () => {
      try {
        const r = await leerGenerados(sid);
        if (!vivo) return;
        setG(r);
        if (r.estado === "generando") {
          if (consultas.current++ < MAX_CONSULTAS) timer = setTimeout(consultar, MS_CONSULTA);
          else setAgotado(true);
        }
      } catch {
        if (vivo) setError("No se pudo consultar el estado de las propuestas.");
      }
    };
    void consultar();
    return () => {
      vivo = false;
      if (timer) clearTimeout(timer);
    };
  }, [sid]);

  const aplicar = useCallback(
    (r: ResultadoDecision) => {
      if (r.tipo === "expediente") onListo(r.estado);
      else setG(r.generados);
    },
    [onListo],
  );

  const conError = async (fn: () => Promise<ResultadoDecision>) => {
    setError(null);
    setOcupado(true);
    try {
      aplicar(await fn());
    } catch (e) {
      if (e instanceof ErrorApi) setError(e.error || e.message);
      else throw e;
    } finally {
      setOcupado(false);
    }
  };

  const decidir =
    (clave: ClaveDocumento) =>
    (decision: "aceptada" | "corregida" | "declinada", textoFinal?: string) =>
      conError(() => decidirDocumento(sid, clave, decision, textoFinal));
  const subir = (clave: ClaveDocumento) => (archivo: File) =>
    conError(() => subirDocumento(sid, clave, archivo));

  const nombre = g?.nombre ?? "Trámite sin nombre";

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">{nombre}</h1>
        <p className="text-sm text-muted-foreground">
          {g === null
            ? "Consultando…"
            : g.estado === "generando"
              ? "Generando la propuesta…"
              : g.estado === "listo"
                ? "Propuesta lista para revisar"
                : g.estado === "error"
                  ? "No se pudo generar la propuesta"
                  : "Sin licencia para generar"}
        </p>
      </header>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {g?.estado === "generando" ? (
        <div className="flex flex-col gap-1 rounded-md border border-border bg-card p-4 text-sm">
          <p>
            El compilador está redactando el Diccionario y el TO-BE a partir del AS-IS. Suele
            tardar uno o dos minutos.
          </p>
          <p className="text-muted-foreground">Puedes cerrar y volver: la liga guarda el avance.</p>
          {agotado ? (
            <p role="alert" className="text-destructive">
              Sigue tardando más de lo normal. Recarga la página en un momento.
            </p>
          ) : null}
        </div>
      ) : null}

      {g && g.estado !== "generando" ? (
        <>
          {g.motivo ? <p className="text-sm text-foreground">{g.motivo}</p> : null}
          <div className="grid items-start gap-6 lg:grid-cols-2">
            <TarjetaPropuesta
              titulo="Diccionario de Datos"
              clave="diccionario"
              documento={g.diccionario}
              onDecidir={decidir("diccionario")}
              onSubir={subir("diccionario")}
              ocupado={ocupado}
            />
            <TarjetaPropuesta
              titulo="Propuesta TO-BE"
              clave="tobe"
              documento={g.tobe}
              onDecidir={decidir("tobe")}
              onSubir={subir("tobe")}
              ocupado={ocupado}
            />
          </div>
        </>
      ) : null}
    </section>
  );
}
