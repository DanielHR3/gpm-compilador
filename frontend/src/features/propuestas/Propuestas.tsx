import { useCallback, useEffect, useRef, useState } from "react";

import AvisoModoPruebas, { useModoPruebas } from "@/components/AvisoModoPruebas";
import MigasDePan from "@/components/MigasDePan";
import { decidirDocumento, ErrorApi, leerGenerados, subirDocumento } from "@/lib/api";
import { migas } from "@/lib/rutas";
import type {
  ClaveDocumento,
  EstadoExpediente,
  GeneradosOut,
  ResultadoDecision,
  PasoGenerado,
} from "@/lib/types";

import TarjetaPropuesta from "./TarjetaPropuesta";

type Props = { sid: string; onListo: (est: EstadoExpediente) => void };

/** Cada cuanto se pregunta por el estado mientras genera. */
const MS_CONSULTA = 3000;
/**
 * Tope: 10 minutos. Un TO-BE largo puede tardar mas de un minuto por llamada
 * (visto con Gemini el 2026-09-24), con hasta tres intentos por documento y
 * una ronda de mejora. El servidor da por interrumpida una generacion a los
 * 20 minutos; pasado este tope la persona ve «recarga» y el estado sigue en
 * el servidor.
 */
const MAX_CONSULTAS = 200;

/**
 * Fase 3: el Diccionario y el TO-BE que el compilador propuso desde el AS-IS.
 * Se decide por documento; cuando los dos quedan resueltos el servidor
 * devuelve el expediente ya extraido y se entra al wizard de siempre.
 */
/** La hora de un paso, corta y en la zona del navegador. */
function horaDe(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

/**
 * Lo que el agente va haciendo, tal como lo cuenta el servidor. El ultimo
 * paso es el que esta en curso: el que sigue no se anuncia hasta que arranca.
 */
function PasosDelAgente({ pasos }: { pasos: PasoGenerado[] }) {
  if (pasos.length === 0) {
    return <p className="text-muted-foreground">Arrancando… en unos segundos aparece aquí lo que va haciendo.</p>;
  }
  return (
    <ol aria-label="Lo que va haciendo el agente" className="flex flex-col gap-1 border-l-2 border-primary/40 pl-3">
      {pasos.map((p, i) => {
        const actual = i === pasos.length - 1;
        return (
          <li key={`${p.t}-${i}`} className={actual ? "text-foreground" : "text-muted-foreground"}>
            <span className="mr-2 tabular-nums text-xs">{horaDe(p.t)}</span>
            <span>{p.mensaje}</span>
            {actual ? (
              <span className="ml-2 text-xs font-medium text-primary" aria-live="polite">en curso…</span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export default function Propuestas({ sid, onListo }: Props) {
  const [g, setG] = useState<GeneradosOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [agotado, setAgotado] = useState(false);
  const consultas = useRef(0);
  const pruebas = useModoPruebas();

  useEffect(() => {
    let vivo = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const consultar = async () => {
      let seguir = false;
      try {
        const r = await leerGenerados(sid);
        if (!vivo) return;
        setG(r);
        setError(null);
        seguir = r.estado === "generando";
      } catch {
        if (!vivo) return;
        // Un fallo pasajero (red, reinicio del servicio) no detiene la
        // consulta: sin esto la persona quedaba atorada hasta recargar.
        setError("No se pudo consultar el estado de las propuestas; se vuelve a intentar.");
        seguir = true;
      }
      if (!seguir) return;
      if (consultas.current++ < MAX_CONSULTAS) timer = setTimeout(consultar, MS_CONSULTA);
      else setAgotado(true);
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
      if (!(e instanceof ErrorApi)) throw e;
      setError(e.error || e.message);
      // El servidor pudo guardar la decision antes de fallar (un 422 del
      // extractor llega DESPUES de escribir `aceptada`). Se relee para que
      // las tarjetas muestren lo que de verdad quedo, no lo de antes.
      try {
        setG(await leerGenerados(sid));
      } catch {
        // Si tampoco se puede leer, se queda lo que habia y el aviso de arriba.
      }
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

  const tarjeta = (clave: ClaveDocumento) => (
    <TarjetaPropuesta
      key={clave}
      titulo={clave === "diccionario" ? "Diccionario de Datos" : "Propuesta TO-BE"}
      clave={clave}
      documento={g ? g[clave] : null}
      onDecidir={decidir(clave)}
      onSubir={subir(clave)}
      ocupado={ocupado}
    />
  );

  const nombre = g?.nombre ?? "Trámite sin nombre";
  const hay = g?.insumos ?? { diccionario: false, tobe: false };
  // Un documento por pantalla: primero el Diccionario, despues el TO-BE. Se
  // decide por lo que ya tiene archivo en la sesion, asi una recarga abre en
  // el paso correcto aunque el Diccionario se haya declinado y subido.
  const paso: "diccionario" | "tobe" = hay.diccionario ? "tobe" : "diccionario";
  // Sin propuesta (error, sin licencia) o con los dos ya resueltos (un 422
  // del extractor): las dos tarjetas, para poder subir encima de cualquiera.
  const ambos = !g?.diccionario || !g?.tobe || (hay.diccionario && hay.tobe);

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <MigasDePan tramos={migas(!g || ambos ? "carga" : paso, "as_is")} />
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

      {pruebas ? <AvisoModoPruebas /> : null}

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {g?.estado === "generando" ? (
        <div className="flex flex-col gap-3 rounded-md border border-border bg-card p-4 text-sm">
          <p>
            El compilador está redactando el Diccionario y el TO-BE a partir del AS-IS. Suele tardar de dos a cinco minutos.
          </p>
          <PasosDelAgente pasos={g.pasos ?? []} />
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
          {ambos ? (
            <div className="grid items-start gap-6 lg:grid-cols-2">
              {tarjeta("diccionario")}
              {tarjeta("tobe")}
            </div>
          ) : (
            tarjeta(paso)
          )}
        </>
      ) : null}
    </section>
  );
}
