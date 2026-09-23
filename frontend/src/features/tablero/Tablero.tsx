import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { leerTablero, type TableroOut } from "@/lib/api";

import Actividad from "./Actividad";
import BarraApilada from "./BarraApilada";
import Barras from "./Barras";
import Indicadores from "./Indicadores";
import MapaCalor from "./MapaCalor";
import { nombreCorto } from "./codigos";

/**
 * Seccion «Tablero»: agregados entre tramites para Simplificacion. Solo pinta
 * lo que `GET /api/v1/tablero` devuelve ya contado; el filtro por dependencia
 * vuelve a pedirlo. Todo en tarjetas: en la SPA no hay tablas. Las graficas
 * son SVG/CSS con la rampa `--viz-*` validada; ninguna lectura depende solo
 * del color (valor escrito, lista alterna, leyenda).
 */

const TOPE_LISTA = 12;
const FECHA = new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "long", year: "numeric" });
const METRICAS: { clave: string; etiqueta: string }[] = [
  { clave: "tareas", etiqueta: "Pasos" },
  { clave: "bifurcaciones", etiqueta: "Bifurcaciones" },
  { clave: "vistas", etiqueta: "Pantallas" },
  { clave: "campos", etiqueta: "Campos" },
  { clave: "acciones", etiqueta: "Acciones" },
  { clave: "integraciones", etiqueta: "Integraciones" },
];

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
  const ind = datos.indicadores;
  // «Mas repetidos» son los de dos o mas tramites; los de uno solo se pliegan
  // (con diez tramites salian 36 renglones de «1 de 10», y la matriz una fila
  // por documento). La matriz cruza solo los repetidos, por lo mismo.
  const repetidos = datos.requisitos.filter((r) => r.tramites >= 2);
  const unicos = datos.requisitos.filter((r) => r.tramites < 2);
  const filasRepetidas = new Set(repetidos.map((r) => r.nombre));
  // Con diez tramites, «compartidos» son decenas de campos a «2 de 10»: se
  // enseñan los doce mas compartidos y el resto se pliega.
  const compartidosTop = datos.campos_compartidos.slice(0, TOPE_LISTA);
  const compartidosResto = datos.campos_compartidos.slice(TOPE_LISTA);
  const matrizRequisitos = {
    filas: datos.matriz_requisitos.filas.filter((f) => filasRepetidas.has(f)),
    columnas: datos.matriz_requisitos.columnas,
    celdas: datos.matriz_requisitos.celdas.filter((_, i) => filasRepetidas.has(datos.matriz_requisitos.filas[i])),
  };

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

      <Indicadores
        cifras={[
          { etiqueta: "Trámites", valor: total },
          { etiqueta: "Dependencias", valor: datos.dependencias.length },
          { etiqueta: "Requisitos distintos", valor: ind.requisitos_distintos },
          { etiqueta: "Campos por trámite", valor: ind.promedio_campos, nota: "promedio" },
          { etiqueta: "Inconsistencias por trámite", valor: ind.promedio_huecos, nota: "promedio al extraer" },
          { etiqueta: "Con integración", valor: ind.con_integracion, nota: "usan un endpoint público" },
        ]}
      />

      <Seccion titulo="Requisitos más repetidos" nota="Documentos que el ciudadano entrega en más de un trámite, y qué trámite pide cada uno.">
        <div className="flex flex-col gap-6">
          {repetidos.length === 0 && unicos.length > 0 ? (
            <p className="text-sm text-muted-foreground">Ningún requisito se repite todavía entre trámites.</p>
          ) : (
            <Barras filas={repetidos} total={total} />
          )}
          {unicos.length > 0 ? (
            <details className="text-xs text-muted-foreground">
              <summary className="cursor-pointer">
                {unicos.length} más aparecen en un solo trámite
              </summary>
              <ul className="mt-1 columns-2 gap-4 md:columns-3">
                {unicos.map((r) => (
                  <li key={r.nombre} className="break-inside-avoid">{r.nombre}</li>
                ))}
              </ul>
            </details>
          ) : null}
          <MapaCalor
            titulo="Requisitos por trámite"
            modo="presencia"
            filas={matrizRequisitos.filas}
            columnas={matrizRequisitos.columnas}
            celdas={matrizRequisitos.celdas}
          />
        </div>
      </Seccion>

      <Seccion titulo="Datos que se capturan en varios trámites" nota="Estos datos podrían capturarse una sola vez.">
        <div className="flex flex-col gap-3">
          <Barras filas={compartidosTop} total={total} />
          {compartidosResto.length > 0 ? (
            <details className="text-xs text-muted-foreground">
              <summary className="cursor-pointer">{compartidosResto.length} más, en menos trámites</summary>
              <ul className="mt-1 columns-2 gap-4 md:columns-3">
                {compartidosResto.map((r) => (
                  <li key={r.nombre} className="break-inside-avoid">
                    {r.nombre} · {r.tramites} de {total}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      </Seccion>

      <Seccion titulo="Dónde se atoran los expedientes" nota="Cuántas veces sale cada inconsistencia en cada trámite, al extraer. Más oscuro, más veces.">
        <MapaCalor
          titulo="Inconsistencias por trámite"
          filas={datos.matriz_huecos.filas}
          columnas={datos.matriz_huecos.columnas}
          celdas={datos.matriz_huecos.celdas}
          maximo={datos.matriz_huecos.maximo}
          etiquetaColumna={nombreCorto}
          subtituloColumna={(c) => c}
        />
      </Seccion>

      <Seccion
        titulo="Complejidad por trámite"
        nota="La escala del estimador no está calibrada: solo el nivel Bajo tiene medición real."
      >
        <div className="flex flex-col gap-5">
          <BarraApilada
            titulo="Nivel de complejidad"
            segmentos={datos.niveles.map((n) => ({ nombre: n.nivel, valor: n.tramites }))}
          />
          {datos.complejidad.length === 0 ? null : (
            <ul className="grid gap-3 md:grid-cols-2">
              {datos.complejidad.map((c) => (
                <li key={c.clave}>
                  <Card role="article" aria-label={c.nombre} className="h-full py-4">
                    <CardHeader className="gap-1">
                      <CardTitle className="text-base">{c.nombre}</CardTitle>
                      <CardDescription>
                        {c.dependencia} · Nivel <strong>{c.nivel}</strong>
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ul className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                        {METRICAS.map((m) => {
                          const v = Number((c.metricas as Record<string, number>)[m.clave] ?? 0);
                          const max = Math.max(1, datos.metricas_max[m.clave] ?? 0);
                          return (
                            <li key={m.clave} className="flex flex-col gap-1">
                              <div className="flex justify-between text-muted-foreground">
                                <span>{m.etiqueta}</span>
                                <span className="font-medium text-foreground">{v}</span>
                              </div>
                              <div
                                role="meter"
                                aria-label={m.etiqueta}
                                aria-valuemin={0}
                                aria-valuemax={max}
                                aria-valuenow={v}
                                title={`${m.etiqueta}: ${v} de ${max} (máximo entre trámites)`}
                                className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                              >
                                <div className="h-full rounded-full" style={{ width: `${(100 * v) / max}%`, background: "var(--viz-3)" }} />
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>
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
          <Actividad semanas={datos.actividad} />
        </Seccion>
      </div>
    </div>
  );
}
