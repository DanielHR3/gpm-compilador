import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Download, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  aceptarVerificados, analizarDocumentos, decidirDestino, ErrorApi, leerDocumentos,
  urlDescargaDocumentos,
} from "@/lib/api";
import type { EstadoDocumentos } from "@/lib/types";

import BarraDestinos from "./BarraDestinos";
import TarjetaDocumento from "./TarjetaDocumento";
import { ORDEN, colorDe, nombreDe } from "./destinos";

/**
 * «Documentos del trámite»: que documentos pedia el tramite, cuales ya no
 * pide y por que. La dependencia entrega el AS-IS, de evaluar sus documentos
 * sale el TO-BE, y este analisis —el corazon de la reingenieria— no se veia
 * en ninguna parte.
 *
 * El agente propone, la verificacion descarta y aqui decide una persona.
 * Solo pinta lo que el servidor devuelve ya contado.
 */
const MS_CONSULTA = 3000;
// 20 minutos: la misma ventana tras la que el servidor da el analisis por muerto.
const MAX_CONSULTAS = 400;

export default function Documentos({ sid }: { sid: string }) {
  const [datos, setDatos] = useState<EstadoDocumentos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const consultas = useRef(0);

  const leer = useCallback(async () => {
    try {
      setDatos(await leerDocumentos(sid));
    } catch {
      setError("No se pudieron abrir los documentos. La sesión expiró o no existe.");
    }
  }, [sid]);

  useEffect(() => {
    void leer();
  }, [leer]);

  // Mientras el agente trabaja se consulta cada 3 s. Se corta con un tope
  // para no dejar una pestaña olvidada preguntando toda la noche.
  useEffect(() => {
    if (datos?.estado !== "analizando") return;
    if (consultas.current++ >= MAX_CONSULTAS) return;
    const reloj = setTimeout(() => void leer(), MS_CONSULTA);
    return () => clearTimeout(reloj);
  }, [datos, leer]);

  async function analizar() {
    setOcupado(true);
    setAviso(null);
    consultas.current = 0;
    try {
      await analizarDocumentos(sid);
      await leer();
    } catch (e) {
      setAviso(e instanceof ErrorApi ? e.error : "No se pudo empezar el análisis.");
    } finally {
      setOcupado(false);
    }
  }

  async function aceptarTodos() {
    setOcupado(true);
    try {
      setDatos(await aceptarVerificados(sid));
    } catch {
      setAviso("No se pudieron aceptar. Inténtalo otra vez.");
    } finally {
      setOcupado(false);
    }
  }

  const volver = (
    <a
      href={`/revisar/${sid}`}
      className="inline-flex items-center gap-1.5 text-sm text-primary underline underline-offset-2"
    >
      <ArrowLeft aria-hidden className="size-3.5" />
      Volver a la revisión
    </a>
  );

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        {volver}
        <p role="alert" className="text-sm text-destructive">{error}</p>
      </div>
    );
  }
  if (!datos) return <p role="status" className="text-sm text-muted-foreground">Abriendo los documentos…</p>;
  if (!datos.disponible) {
    return (
      <div className="flex flex-col gap-4">
        {volver}
        <h1 className="text-xl font-semibold">Documentos del trámite</h1>
        <p className="max-w-prose text-sm">{datos.motivo}</p>
      </div>
    );
  }

  const analizando = datos.estado === "analizando";
  const porAceptar = datos.documentos.filter(
    (d) => d.estado === "propuesto" && !d.veredicto && d.destino !== "sin_destino",
  ).length;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {volver}
        <div className="flex flex-wrap items-center gap-3">
          <a
            href={`/revisar/${sid}/comparativa`}
            className="text-sm text-primary underline underline-offset-2"
          >
            Ver antes y después
          </a>
          <Button
            size="sm"
            variant="outline"
            render={
              <a href={urlDescargaDocumentos(sid)} download>
                <Download aria-hidden />
                Descargar
              </a>
            }
          />
        </div>
      </div>

      <header className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Documentos del trámite</h1>
        <p className="text-2xl font-bold leading-tight tracking-tight text-primary">
          {datos.resumen.titular}
        </p>
        <BarraDestinos resumen={datos.resumen} />
      </header>

      {datos.resumen.simplificacion.length > 0 ? (
        <section aria-label="Cómo se simplificó el trámite" className="flex flex-col gap-3">
          <div>
            <h2 className="text-base font-semibold">Cómo se simplificó el trámite</h2>
            <p className="text-xs text-muted-foreground">
              Solo lo que ya revisó una persona. Lo propuesto y sin revisar no se afirma.
            </p>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {datos.resumen.simplificacion.map((x) => (
              <li key={x.destino} aria-label={x.frase}>
                <Card className="h-full border-l-4 py-3" style={{ borderLeftColor: colorDe(x.destino) }}>
                  <CardContent className="flex flex-col gap-1">
                    <span className="text-sm font-semibold">
                      {x.frase} · {x.documentos.length}
                    </span>
                    <span className="text-sm">{x.documentos.join(", ")}</span>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <Card>
        <CardContent className="flex flex-col gap-3">
          {datos.pruebas ? (
            <p className="rounded-md bg-muted/60 p-2 text-xs">
              Modo de pruebas: al analizar, el AS-IS y el TO-BE de este expediente viajan a Gemini.
            </p>
          ) : null}
          {datos.estado === "error" && datos.motivo_estado ? (
            <p role="alert" className="text-sm text-destructive">{datos.motivo_estado}</p>
          ) : null}
          {aviso ? <p role="alert" className="text-sm text-destructive">{aviso}</p> : null}
          {analizando ? (
            <div role="status" className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Analizando los documentos…</span>
              <ul className="text-xs text-muted-foreground">
                {datos.pasos.map((p, i) => (
                  <li key={`${p.t}-${i}`}>{p.mensaje}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {!datos.puede_analizar && datos.motivo_analizar ? (
            <p className="text-sm">
              {datos.motivo_analizar}{" "}
              <span className="text-muted-foreground">
                Puedes asignar el destino de cada documento a mano.
              </span>
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {datos.puede_analizar && !analizando ? (
              <Button type="button" size="sm" disabled={ocupado} onClick={() => void analizar()}>
                <Sparkles aria-hidden />
                {datos.estado === "sin_analizar" ? "Analizar documentos" : "Volver a analizar"}
              </Button>
            ) : null}
            {porAceptar > 0 && !analizando ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={ocupado}
                onClick={() => void aceptarTodos()}
              >
                Aceptar los {porAceptar} verificados
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2 2xl:grid-cols-3">
        {ORDEN.map((destino) => {
          const suyos = datos.documentos.filter((d) => d.destino === destino);
          if (suyos.length === 0) return null;
          return (
            <section key={destino} aria-label={nombreDe(destino)} className="flex flex-col gap-3">
              <h2 className="text-base font-semibold">
                {nombreDe(destino)} · {suyos.length}
              </h2>
              <ul className="flex flex-col gap-3">
                {suyos.map((d) => (
                  <li key={d.id}>
                    <TarjetaDocumento
                      // La llave cambia con la decision: tras guardar, la
                      // tarjeta arranca de lo que devolvio el servidor.
                      key={`${d.id}|${d.destino}|${d.estado}`}
                      documento={d}
                      onDecidir={async (que, porque) => {
                        setDatos(await decidirDestino(sid, d.id, que, porque));
                      }}
                    />
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>

      {datos.resumen.agregados.length > 0 ? (
        <section aria-label="Documentos que el TO-BE agrega" className="flex flex-col gap-3">
          <div>
            <h2 className="text-base font-semibold">Documentos que el TO-BE agrega</h2>
            <p className="text-xs text-muted-foreground">
              El trámite rediseñado los pide y el AS-IS no los nombraba.
            </p>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {datos.resumen.agregados.map((a) => (
              <li key={a}>
                <Card className="py-3">
                  <CardContent className="text-sm">{a}</CardContent>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
