import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { leerTablero, type TableroOut } from "@/lib/api";

import Barras from "./Barras";
import { nombreCorto } from "./codigos";

/**
 * Seccion «Tablero»: agregados entre tramites para Simplificacion. Solo pinta
 * lo que `GET /api/v1/tablero` devuelve ya contado; el filtro por dependencia
 * vuelve a pedirlo. Todo en tarjetas: en la SPA no hay tablas.
 */

const FECHA = new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "long", year: "numeric" });

function pct(n: number, total: number): number {
  return total ? Math.round((100 * n) / total) : 0;
}

function Seccion({ titulo, nota, children }: { titulo: string; nota?: string; children: ReactNode }) {
  return (
    <section>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            <h2>{titulo}</h2>
          </CardTitle>
          {nota ? <CardDescription>{nota}</CardDescription> : null}
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </section>
  );
}

export default function Tablero() {
  const [datos, setDatos] = useState<TableroOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dependencia, setDependencia] = useState<string | undefined>(undefined);
  // Las dependencias del filtro se fijan con la primera respuesta (sin
  // filtro): si salieran de la respuesta filtrada, elegir una borraria las demas.
  const [todas, setTodas] = useState<string[] | null>(null);

  useEffect(() => {
    leerTablero(dependencia)
      .then((d) => {
        setDatos(d);
        setTodas((t) => t ?? d.dependencias.map((x) => x.nombre));
      })
      .catch(() => setError("No se pudo leer el tablero."));
  }, [dependencia]);

  if (error) return <p role="alert" className="text-sm text-destructive">{error}</p>;
  if (!datos) return <p className="text-sm text-muted-foreground">Cargando…</p>;

  const total = datos.total_tramites;
  const ultimo = datos.ultimo_registro ? FECHA.format(new Date(datos.ultimo_registro)) : null;
  const maxSemana = Math.max(1, ...datos.actividad.map((a) => a.tramites));

  return (
    <div className="flex flex-col gap-4 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Tablero</h1>
        <p className="text-sm text-muted-foreground">
          {total} trámites de {(todas ?? datos.dependencias).length} dependencias
          {ultimo ? `, último registrado el ${ultimo}` : ""}.
        </p>
      </header>

      {todas && todas.length > 0 ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Dependencia">
          <Button size="sm" variant={dependencia ? "outline" : "default"} onClick={() => setDependencia(undefined)}>
            Todas
          </Button>
          {todas.map((d) => (
            <Button key={d} size="sm" variant={dependencia === d ? "default" : "outline"} onClick={() => setDependencia(d)}>
              {d}
            </Button>
          ))}
        </div>
      ) : null}

      {total === 0 ? (
        <p className="text-sm text-muted-foreground">
          Todavía no hay nada que mostrar: el tablero se llena solo al extraer expedientes.
        </p>
      ) : null}

      <Seccion titulo="Requisitos más repetidos" nota="Documentos que el ciudadano entrega en más de un trámite.">
        <Barras filas={datos.requisitos} total={total} />
      </Seccion>

      <Seccion titulo="Datos que se capturan en varios trámites" nota="Estos datos podrían capturarse una sola vez.">
        <Barras filas={datos.campos_compartidos} total={total} />
      </Seccion>

      <Seccion titulo="Dónde se atoran los expedientes" nota="En cuántos trámites sale cada inconsistencia al extraer.">
        <Barras
          total={total}
          filas={datos.huecos.map((h) => ({
            nombre: nombreCorto(h.codigo),
            tramites: h.tramites,
            porcentaje: pct(h.tramites, total),
            detalle: `${h.codigo} · ${h.total} en total`,
          }))}
        />
      </Seccion>

      <Seccion
        titulo="Complejidad por trámite"
        nota="La escala del estimador no está calibrada: solo el nivel Bajo tiene medición real."
      >
        {datos.complejidad.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nada que contar todavía.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {datos.complejidad.map((c) => (
              <li key={c.clave}>
                <Card role="article" aria-label={c.nombre} className="py-4">
                  <CardHeader className="gap-1">
                    <CardTitle className="text-base">{c.nombre}</CardTitle>
                    <CardDescription>
                      {c.dependencia} · Nivel <strong>{c.nivel}</strong>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>Pasos {c.metricas.tareas}</span>
                    <span>Bifurcaciones {c.metricas.bifurcaciones}</span>
                    <span>Pantallas {c.metricas.vistas}</span>
                    <span>Campos {c.metricas.campos}</span>
                    <span>Acciones {c.metricas.acciones}</span>
                    <span>Integraciones {c.metricas.integraciones}</span>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </Seccion>

      <div className="grid gap-4 md:grid-cols-2">
        <Seccion titulo="Integraciones" nota="Cuántos trámites usan cada endpoint público.">
          <Barras
            total={total}
            filas={datos.catalogos.map((k) => ({
              nombre: k.clave,
              tramites: k.tramites,
              porcentaje: pct(k.tramites, total),
            }))}
          />
        </Seccion>
        <Seccion titulo="Actividad" nota="Trámites registrados por semana, últimas doce.">
          <ul className="flex h-24 items-end gap-1" aria-label="Trámites por semana">
            {datos.actividad.map((a) => (
              <li
                key={a.semana}
                aria-label={`${a.semana}: ${a.tramites}`}
                title={`${a.semana}: ${a.tramites}`}
                className="flex-1 rounded-t bg-primary/80"
                style={{ height: `${Math.max(4, (100 * a.tramites) / maxSemana)}%` }}
              />
            ))}
          </ul>
        </Seccion>
      </div>
    </div>
  );
}
