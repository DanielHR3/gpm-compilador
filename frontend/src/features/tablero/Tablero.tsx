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
import { resumenEnPalabras } from "./resumen";

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

function Seccion({ titulo, nota, accion, children }: { titulo: string; nota?: string; accion?: string; children: ReactNode }) {
  return (
    <section>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            <h2>{titulo}</h2>
          </CardTitle>
          {nota ? <CardDescription>{nota}</CardDescription> : null}
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {children}
          {accion ? (
            <details className="text-xs text-muted-foreground">
              <summary className="cursor-pointer">¿Qué hago con esto?</summary>
              <p className="mt-1 max-w-prose">{accion}</p>
            </details>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}

const LLAVE_GUIA = "gpmc.tablero.guia";

function guiaAbierta(): boolean {
  try {
    return window.localStorage.getItem(LLAVE_GUIA) !== "cerrada";
  } catch {
    return true;
  }
}

function recordarGuia(abierta: boolean) {
  try {
    window.localStorage.setItem(LLAVE_GUIA, abierta ? "abierta" : "cerrada");
  } catch {
    /* sin almacenamiento, la guia simplemente vuelve a salir */
  }
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
  const complejos = datos.niveles.find((n) => n.nivel === "Complejo")?.tramites ?? 0;
  const resumen = resumenEnPalabras(datos);
  // Nombre humano primero; el tecnico en segundo plano, para quien lo necesite.
  const conEtiqueta = (r: { nombre: string; etiqueta?: string; tramites: number; porcentaje: number }) => ({
    ...r,
    nombre: r.etiqueta || r.nombre,
    detalle: r.etiqueta && r.etiqueta !== r.nombre ? r.nombre : undefined,
  });
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

      <details
        open={guiaAbierta()}
        onToggle={(e) => recordarGuia((e.currentTarget as HTMLDetailsElement).open)}
        className="rounded-lg border border-border bg-card px-4 py-3 text-sm"
      >
        <summary className="cursor-pointer font-medium">Cómo leer este tablero</summary>
        <div className="mt-2 flex max-w-prose flex-col gap-2 text-muted-foreground">
          <p>
            Este tablero compara entre sí los trámites que el equipo ha subido al compilador. Se llena solo:
            cada vez que alguien sube un expediente, el trámite entra o se actualiza aquí.
          </p>
          <p>
            Sirve para ver patrones que no se notan trámite por trámite: qué documentos se piden una y otra vez,
            qué datos se capturan en varios lados, en qué se atoran los expedientes y cuáles son los trámites
            más grandes.
          </p>
          <p>
            Cada sección tiene un «¿Qué hago con esto?» con una sugerencia concreta. Los botones de arriba
            filtran todo por dependencia.
          </p>
        </div>
      </details>

      {resumen.length > 0 ? (
        <Card className="border-l-4 border-l-primary py-4">
          <CardContent className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">En resumen</span>
            {resumen.map((f) => (
              <p key={f}>{f}</p>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Indicadores
        cifras={[
          { etiqueta: "Trámites", valor: total, nota: `de ${datos.dependencias.length} dependencias` },
          { etiqueta: "Complejos", valor: complejos, nota: `de ${total} trámites` },
          { etiqueta: "Requisitos distintos", valor: ind.requisitos_distintos, nota: "documentos que piden los trámites" },
          { etiqueta: "Campos por trámite", valor: ind.promedio_campos, nota: "promedio de datos que se capturan" },
          { etiqueta: "Pendientes por trámite", valor: ind.promedio_huecos, nota: "promedio al subir el expediente" },
          { etiqueta: "Consultan otro sistema", valor: ind.con_integracion, nota: "INEGI, SEPOMEX o SIPUBEH" },
        ]}
      />

      <Seccion
        titulo="Requisitos más repetidos"
        nota="Documentos que el ciudadano entrega en más de un trámite, y qué trámite pide cada uno."
        accion="Si un documento se pide en varios trámites, es candidato a pedirse una sola vez y compartirse entre dependencias, o a sustituirse por una consulta a otro sistema (por ejemplo, la CURP en vez de la identificación)."
      >
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

      <Seccion
        titulo="Datos que se capturan en varios trámites"
        nota="Lo que el ciudadano escribe en más de un trámite."
        accion="Estos datos podrían capturarse una sola vez y reutilizarse: son la base para una ficha del ciudadano compartida, o para autollenar con una consulta (CURP, código postal)."
      >
        <div className="flex flex-col gap-3">
          <Barras filas={compartidosTop.map(conEtiqueta)} total={total} />
          {compartidosResto.length > 0 ? (
            <details className="text-xs text-muted-foreground">
              <summary className="cursor-pointer">{compartidosResto.length} más, en menos trámites</summary>
              <ul className="mt-1 columns-2 gap-4 md:columns-3">
                {compartidosResto.map((r) => (
                  <li key={r.nombre} className="break-inside-avoid">
                    {r.etiqueta || r.nombre} · {r.tramites} de {total}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      </Seccion>

      <Seccion
        titulo="Dónde se atoran los expedientes"
        nota="Qué quedó pendiente en cada trámite al subir su expediente, y cuántas veces. Más oscuro, más veces."
        accion="Una columna oscura en casi todos los trámites señala algo que falta en la plantilla del expediente (por ejemplo, la homoclave o el tiempo de respuesta): conviene añadirlo a la plantilla para que deje de faltar. Una fila oscura es un expediente que necesita una segunda pasada."
      >
        <MapaCalor
          titulo="Inconsistencias por trámite"
          filas={datos.matriz_huecos.filas}
          columnas={datos.matriz_huecos.columnas}
          celdas={datos.matriz_huecos.celdas}
          maximo={datos.matriz_huecos.maximo}
          etiquetaColumna={nombreCorto}
          detalleColumna={(c) => c}
        />
      </Seccion>

      <Seccion
        titulo="Complejidad por trámite"
        nota="Qué tan grande es cada trámite: cuántos pasos, pantallas y datos tiene. Bajo: hasta 4 pasos y pocas pantallas. Medio: entre 5 y 8 pasos o consulta a otro sistema. Complejo: más de eso. La escala es orientativa; solo el nivel Bajo se ha medido en tiempo real."
        accion="Un trámite complejo tarda más en modelarse y en probarse. Si hay varios, conviene empezar por los medios para tener resultados pronto, y partir los complejos en etapas."
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
        <Seccion
          titulo="Consultas a otros sistemas"
          nota="Cuántos trámites toman datos de un sistema público en vez de pedírselos al ciudadano."
          accion="Cada consulta ahorra una captura y un error de dedo. Si un dato se captura en varios trámites y existe una consulta para él, conviene usarla."
        >
          <Barras
            total={total}
            filas={datos.catalogos.map((k) => ({
              nombre: k.proveedor && k.descripcion ? `${k.proveedor} · ${k.descripcion}` : k.clave,
              detalle: k.proveedor && k.descripcion ? k.clave : undefined,
              tramites: k.tramites,
              porcentaje: pct(k.tramites, total),
            }))}
          />
        </Seccion>
        <Seccion titulo="Actividad" nota="Cuántos trámites se subieron cada semana, en las últimas doce.">
          <Actividad semanas={datos.actividad} />
        </Seccion>
      </div>
    </div>
  );
}
