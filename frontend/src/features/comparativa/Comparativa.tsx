import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  analizarComparativa, declararMetrica, descartarMejora, leerComparativa,
  urlDocumentoComparativa,
} from "@/lib/api";
import type { ComparativaOut, MetricaComparada, ValorComparado } from "@/lib/types";

import CapturaMetrica from "./CapturaMetrica";
import ElementosRediseno from "./ElementosRediseno";
import EstadoAnalisis from "./EstadoAnalisis";
import EvidenciaPropuesta from "./EvidenciaPropuesta";
import GraficaSimplificacion from "./GraficaSimplificacion";
import PuntosDeMejora from "./PuntosDeMejora";
import ResumenLlano from "./ResumenLlano";
import { etiquetaDestino, etiquetaOrigen, textoCambio, tituloVeredicto } from "./formato";

/**
 * «Antes y después»: la evidencia de que un tramite si tuvo reingenieria. La
 * pidio Simplificacion el 2026-09-28; es de uso interno.
 *
 * Solo pinta lo que `GET …/comparativa` devuelve ya contado. Todo en tarjetas:
 * en la SPA no hay tablas. Cada cifra lleva su origen a la vista, porque una
 * cifra sin origen no sirve de evidencia.
 *
 * Desde el 2026-10-01 la pagina llega completa: la primera vez que se abre,
 * un agente busca en el AS-IS y el TO-BE la evidencia de los lados que el
 * compilador no supo contar y propone que mas se puede simplificar. Lo que
 * propone va rotulado y con sus frases a la vista.
 */
const MS_CONSULTA = 2500;
// 20 minutos: la misma ventana tras la que el servidor da el analisis por muerto.
const MAX_CONSULTAS = 480;

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
  agente,
  onGuardar,
}: {
  metrica: MetricaComparada;
  /** En que va el agente: mientras busca no se pide captura; si ya busco, se dice. */
  agente: "sin_agente" | "buscando" | "termino";
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
        {metrica.propuesta_antes ? (
          <EvidenciaPropuesta lado="antes" propuesta={metrica.propuesta_antes} />
        ) : null}
        {metrica.propuesta_despues ? (
          <EvidenciaPropuesta lado="después" propuesta={metrica.propuesta_despues} />
        ) : null}
        {falta && agente === "buscando" ? (
          <p className="text-xs text-muted-foreground">
            El agente está buscando este dato en el expediente…
          </p>
        ) : null}
        {falta && agente === "termino" && !declarada ? (
          <p className="text-xs text-muted-foreground">
            El expediente no trae evidencia de este dato. Si lo conoces, escríbelo aquí.
          </p>
        ) : null}
        {!falta && !declarada && !corrigiendo ? (
          <Button type="button" size="sm" variant="ghost" className="self-start"
                  onClick={() => setCorrigiendo(true)}>
            Corregir
          </Button>
        ) : null}
        {(falta && agente !== "buscando") || declarada || corrigiendo ? (
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
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const consultas = useRef(0);
  const lanzado = useRef(false);

  useEffect(() => {
    let vivo = true;
    leerComparativa(sid)
      .then((c) => vivo && setDatos(c))
      .catch(() => vivo && setError("No se pudo abrir la comparativa. La sesión expiró o no existe."));
    return () => {
      vivo = false;
    };
  }, [sid]);

  const analizar = useCallback(async () => {
    setOcupado(true);
    setAviso(null);
    consultas.current = 0;
    try {
      await analizarComparativa(sid);
      setDatos(await leerComparativa(sid));
    } catch {
      setAviso("No se pudo empezar el análisis. La comparativa muestra lo que contó el compilador.");
    } finally {
      setOcupado(false);
    }
  }, [sid]);

  // La primera vez que alguien abre la comparativa de un expediente, el agente
  // corre solo (decision del 2026-10-01: la pagina tiene que llegar completa).
  // Una sola vez por montaje: un fallo no se reintenta en bucle.
  const estado = datos?.disponible ? datos.analisis : undefined;
  useEffect(() => {
    if (!estado || lanzado.current) return;
    if (estado.estado !== "sin_analizar" || !estado.puede_analizar) return;
    lanzado.current = true;
    void analizar();
  }, [estado, analizar]);

  // Mientras el agente trabaja se consulta cada 2.5 s, con un tope para no
  // dejar una pestaña olvidada preguntando toda la noche.
  useEffect(() => {
    if (estado?.estado !== "analizando") return;
    if (consultas.current++ >= MAX_CONSULTAS) return;
    const reloj = setTimeout(() => {
      leerComparativa(sid).then(setDatos).catch(() => undefined);
    }, MS_CONSULTA);
    return () => clearTimeout(reloj);
  }, [datos, estado, sid]);

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
  const analisis = datos.analisis;
  // «termino» solo si de verdad busco: tras un fallo no se puede decir que el
  // expediente no trae el dato, solo que no se pudo buscar.
  const agente =
    analisis?.estado === "lista"
      ? "termino"
      : analisis?.estado === "analizando" ||
          (analisis?.estado === "sin_analizar" && analisis.puede_analizar)
        ? "buscando"
        : "sin_agente";
  const mejoras = datos.mejoras ?? [];
  const elementos = datos.elementos ?? [];
  // El aviso solo aparece cuando hay algo que decir.
  const hayAviso =
    analisis !== undefined &&
    (analisis.estado !== "sin_analizar" || !analisis.puede_analizar || aviso !== null);

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

      {hayAviso && analisis ? (
        <EstadoAnalisis analisis={analisis} ocupado={ocupado} aviso={aviso}
                        onAnalizar={() => void analizar()} />
      ) : null}

      <Card className="border-l-4 border-l-primary">
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-lg font-bold">{tituloVeredicto(datos.veredicto)}</span>
            <p className="max-w-prose text-sm">{datos.frase}</p>
          </div>
          <ResumenLlano lineas={datos.resumen ?? []} />
        </CardContent>
      </Card>

      {elementos.length > 0 && datos.resumen_elementos ? (
        <Seccion titulo="Qué pasó con cada elemento del trámite"
                 nota="La tabla «Análisis de eliminación» del TO-BE, tal como la escribió el equipo.">
          <ElementosRediseno elementos={elementos} resumen={datos.resumen_elementos} />
        </Seccion>
      ) : null}

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
                agente={agente}
                onGuardar={async (antes, despues) => {
                  setDatos(await declararMetrica(sid, m.clave, antes, despues));
                }}
              />
            </li>
          ))}
        </ul>
      </Seccion>

      {mejoras.length > 0 ? (
        <Seccion titulo="Qué más se puede simplificar"
                 nota="Propuestas del agente sobre el trámite ya rediseñado. Cada una se apoya en una frase del expediente o en un documento que se sigue pidiendo; decide el equipo.">
          <PuntosDeMejora
            mejoras={mejoras}
            onDescartar={async (id, descartada) => {
              setDatos(await descartarMejora(sid, id, descartada));
            }}
          />
        </Seccion>
      ) : null}

      <Card>
        <CardContent className="flex flex-col gap-2">
          <span className="text-sm font-semibold">Documentos del trámite</span>
          <p className="text-sm">
            {datos.documentos
              ? datos.documentos.titular
              : "Revisa qué pasó con cada documento que pedía el trámite."}
          </p>
          {datos.documentos && datos.documentos.simplificacion.length > 0 ? (
            <ul className="flex flex-col gap-1 text-sm">
              {datos.documentos.simplificacion.map((x) => (
                <li key={x.destino}>
                  <strong>{x.frase}:</strong> {x.documentos.join(", ")}
                </li>
              ))}
            </ul>
          ) : null}
          <a
            href={`/revisar/${sid}/documentos`}
            className="self-start text-sm text-primary underline underline-offset-2"
          >
            Ver documentos del trámite
          </a>
        </CardContent>
      </Card>

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
