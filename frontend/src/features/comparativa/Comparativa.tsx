import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeft, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { declararMetrica, leerComparativa, urlDocumentoComparativa } from "@/lib/api";
import type { ComparativaOut, MetricaComparada, ValorComparado } from "@/lib/types";

import CapturaMetrica from "./CapturaMetrica";
import GraficaSimplificacion from "./GraficaSimplificacion";
import { etiquetaDestino, etiquetaOrigen, textoCambio, tituloVeredicto } from "./formato";

/**
 * «Antes y después»: la evidencia de que un tramite si tuvo reingenieria. La
 * pidio Simplificacion el 2026-09-28; es de uso interno.
 *
 * Solo pinta lo que `GET …/comparativa` devuelve ya contado. Todo en tarjetas:
 * en la SPA no hay tablas. Cada cifra lleva su origen a la vista, porque una
 * cifra sin origen no sirve de evidencia.
 */

function Seccion({ titulo, nota, children }: { titulo: string; nota?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-base font-semibold">{titulo}</h2>
        {nota ? <p className="text-xs text-muted-foreground">{nota}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Lado({ rotulo, valor }: { rotulo: string; valor: ValorComparado }) {
  return (
    <div className="flex flex-1 flex-col">
      <span className="text-[0.6875rem] uppercase tracking-wide text-muted-foreground">{rotulo}</span>
      <span className="text-xl font-bold leading-tight">
        {valor.origen === "sin_dato" ? "—" : valor.texto}
      </span>
      <span className="text-[0.6875rem] text-muted-foreground">{etiquetaOrigen(valor.origen)}</span>
    </div>
  );
}

function TarjetaMetrica({
  metrica,
  onGuardar,
}: {
  metrica: MetricaComparada;
  onGuardar: (antes: string, despues: string) => Promise<void>;
}) {
  const falta = metrica.antes.origen === "sin_dato" || metrica.despues.origen === "sin_dato";
  const declarada = metrica.antes.origen === "declarado" || metrica.despues.origen === "declarado";
  // Una cifra contada tambien se puede corregir: el lector del AS-IS puede
  // contar mal un documento con forma rara. Va plegado para no llenar de
  // formularios las tarjetas que ya estan bien.
  const [corrigiendo, setCorrigiendo] = useState(false);
  const sinComparar =
    metrica.porcentaje === null &&
    metrica.antes.numero !== null &&
    metrica.despues.numero !== null &&
    metrica.antes.unidad !== metrica.despues.unidad;
  return (
    <Card role="article" aria-label={metrica.nombre} className="h-full">
      <CardHeader>
        <CardTitle className="text-sm">{metrica.nombre}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex gap-4">
          <Lado rotulo="Antes" valor={metrica.antes} />
          <Lado rotulo="Después" valor={metrica.despues} />
        </div>
        {metrica.porcentaje !== null ? (
          <p className="text-sm font-semibold tabular-nums">{textoCambio(metrica.porcentaje)}</p>
        ) : null}
        {sinComparar ? (
          <p className="text-xs text-muted-foreground">
            No se compara: las unidades no coinciden. Escribe los dos lados con la misma unidad.
          </p>
        ) : null}
        {!falta && !declarada && !corrigiendo ? (
          <Button type="button" size="sm" variant="ghost" className="self-start"
                  onClick={() => setCorrigiendo(true)}>
            Corregir
          </Button>
        ) : null}
        {falta || declarada || corrigiendo ? (
          // La llave cambia con el valor: tras guardar, el formulario arranca
          // de lo que el servidor devolvio y no de lo que quedo tecleado.
          <CapturaMetrica
            key={`${metrica.antes.texto}|${metrica.despues.texto}`}
            metrica={metrica}
            onGuardar={onGuardar}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function Puntos({ etiqueta, lado, puntos }: { etiqueta: string; lado: string; puntos: string[] }) {
  return (
    <ol className="flex flex-col gap-2">
      {puntos.map((p, i) => (
        <li key={`${i}-${p}`}>
          <Card role="article" aria-label={`${etiqueta} ${i + 1} de ${lado}`} className="py-3">
            <CardContent className="text-sm">{p}</CardContent>
          </Card>
        </li>
      ))}
    </ol>
  );
}

export default function Comparativa({ sid }: { sid: string }) {
  const [datos, setDatos] = useState<ComparativaOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    leerComparativa(sid)
      .then((c) => vivo && setDatos(c))
      .catch(() => vivo && setError("No se pudo abrir la comparativa. La sesión expiró o no existe."));
    return () => {
      vivo = false;
    };
  }, [sid]);

  const volver = (
    <a href={`/revisar/${sid}`}
       className="inline-flex items-center gap-1.5 text-sm text-primary underline underline-offset-2">
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
  if (!datos) return <p className="text-sm text-muted-foreground">Armando la comparativa…</p>;
  if (!datos.disponible) {
    return (
      <div className="flex flex-col gap-4">
        {volver}
        <h1 className="text-xl font-semibold">Antes y después</h1>
        <p className="max-w-prose text-sm">{datos.motivo}</p>
      </div>
    );
  }

  const tareas = datos.tareas_despues.map((t) => (t.actor ? `${t.nombre} · ${t.actor}` : t.nombre));

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {volver}
        <Button
          size="sm"
          render={
            <a href={urlDocumentoComparativa(sid)} download>
              <Download aria-hidden />
              Descargar documento
            </a>
          }
        />
      </div>

      <header className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold">Antes y después</h1>
        <p className="text-sm text-muted-foreground">{datos.tramite}</p>
      </header>

      <Card className="border-l-4 border-l-primary">
        <CardContent className="flex flex-col gap-1">
          <span className="text-lg font-bold">{tituloVeredicto(datos.veredicto)}</span>
          <p className="max-w-prose text-sm">{datos.frase}</p>
        </CardContent>
      </Card>

      <Seccion titulo="Porcentaje de simplificación"
               nota="Promedio de las métricas que tienen número en los dos lados.">
        <Card>
          <CardContent>
            <GraficaSimplificacion comparativa={datos} />
          </CardContent>
        </Card>
      </Seccion>

      <Seccion titulo="Métricas"
               nota={`Cada cifra dice de dónde salió. Campos que se llenan solos por consulta en línea: ${datos.autollenados}.`}>
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {datos.metricas.map((m) => (
            <li key={m.clave}>
              <TarjetaMetrica
                metrica={m}
                onGuardar={async (antes, despues) => {
                  setDatos(await declararMetrica(sid, m.clave, antes, despues));
                }}
              />
            </li>
          ))}
        </ul>
      </Seccion>

      {datos.requisitos.length > 0 ? (
        <Seccion titulo="Requisitos, uno por uno"
                 nota="«Sin destino» quiere decir que el TO-BE no lo conserva ni dice que lo elimina.">
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {datos.requisitos.map((r) => (
              <li key={`${r.destino}-${r.nombre}`}>
                <Card role="article" aria-label={r.nombre} className="h-full py-4">
                  <CardContent className="flex flex-col gap-1">
                    <span className="text-sm font-medium">{r.nombre}</span>
                    <span className="text-xs font-semibold">{etiquetaDestino(r.destino)}</span>
                    {r.fundamento ? (
                      <span className="text-xs text-muted-foreground">{r.fundamento}</span>
                    ) : null}
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        </Seccion>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Seccion titulo="Pasos de antes">
          {datos.pasos_antes.length > 0 ? (
            <Puntos etiqueta="Paso" lado="antes" puntos={datos.pasos_antes} />
          ) : (
            <p className="text-sm text-muted-foreground">El AS-IS no trae pasos que se puedan leer.</p>
          )}
        </Seccion>
        <Seccion titulo="Tareas de después">
          <Puntos etiqueta="Tarea" lado="después" puntos={tareas} />
        </Seccion>
      </div>

      {(
        [
          ["Fricciones del proceso actual", datos.fricciones, undefined],
          ["Cambios concretos frente al AS-IS", datos.cambios, undefined],
          ["Lo que se eliminó", datos.eliminaciones, undefined],
          ["Impacto estimado", datos.impacto, "Estimación cualitativa del equipo, no un dato medido."],
          ["Por confirmar", datos.huecos.map((h) => h.mensaje), undefined],
        ] as const
      ).map(([titulo, puntos, nota]) =>
        puntos.length > 0 ? (
          <Seccion key={titulo} titulo={titulo} nota={nota}>
            <ul className="flex flex-col gap-2">
              {puntos.map((p, i) => (
                <li key={`${i}-${p}`}>
                  <Card className="py-3">
                    <CardContent className="text-sm">{p}</CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          </Seccion>
        ) : null,
      )}
    </div>
  );
}
