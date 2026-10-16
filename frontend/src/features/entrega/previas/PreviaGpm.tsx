import { useState } from "react";

import { Button } from "@/components/ui/button";

type Dict = Record<string, unknown>;
const lista = (v: unknown): Dict[] => (Array.isArray(v) ? v.filter((x) => x && typeof x === "object") as Dict[] : []);
const texto = (v: unknown): string => (typeof v === "string" ? v : typeof v === "number" ? String(v) : "");
const si = (v: unknown): boolean => v === "1" || v === 1 || v === true;

/** El tipo de campo como lo diría una persona, no como lo guarda GPM. */
const TIPO: Record<string, string> = {
  text: "Texto", textarea: "Texto largo", select: "Lista", radio: "Opción única", checkbox: "Casillas",
  file: "Archivo", date: "Fecha", date_time: "Fecha", paragraph: "Párrafo", subtitle: "Subtítulo",
  cart: "Carrito", api_ajax: "Consulta a otro sistema", documento: "Documento", hidden: "Oculto",
};

/** Las opciones de un `select` manual viven en `extra.catalog_values` como `valor:Etiqueta|…`. */
function opcionesDe(c: Dict): string[] {
  try {
    const extra = typeof c.extra === "string" ? (JSON.parse(c.extra) as Dict) : (c.extra as Dict | null);
    const crudo = texto(extra?.catalog_values);
    if (!crudo) return [];
    return crudo.split("|").map((par) => par.split(":").slice(1).join(":") || par).filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * El `.gpm` resumido desde su propio JSON: lo que la plataforma va a
 * reconstruir al importarlo. El archivo viaja en una sola línea a propósito
 * (la forma es byte a byte); aquí se lee en tarjetas y, si hace falta,
 * sangrado con «Ver el JSON».
 */
export default function PreviaGpm({ texto: crudo }: { texto: string }) {
  const [verJson, setVerJson] = useState(false);
  let g: Dict | null = null;
  try {
    const v = JSON.parse(crudo) as unknown;
    g = v && typeof v === "object" ? (v as Dict) : null;
  } catch {
    g = null;
  }
  if (!g) {
    return <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed">{crudo}</pre>;
  }

  const formularios = lista(g.Formularios);
  const tareas = lista(g.Tareas);
  const conexiones = lista(g.Conexiones);
  const acciones = lista(g.Acciones);
  const tareaNombre = new Map(tareas.map((t) => [texto(t.id), texto(t.nombre) || texto(t.id)]));
  const formNombre = new Map(formularios.map((f) => [texto(f.id), texto(f.nombre) || texto(f.id)]));
  const rotulo = "font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground";

  return (
    <div className="flex flex-col gap-5 text-sm">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="text-lg font-bold tracking-tight">{texto(g.nombre) || "Trámite sin nombre"}</h3>
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
            {texto(g.homoclave) ? <Dato k="Homoclave" v={texto(g.homoclave)} /> : null}
            {texto(g.tiempo_entrega) ? <Dato k="Tiempo de entrega" v={texto(g.tiempo_entrega)} /> : null}
            {texto(g.costo) && texto(g.costo) !== "0" ? <Dato k="Costo" v={texto(g.costo)} /> : null}
            <Dato k="Formularios" v={String(formularios.length)} />
            <Dato k="Tareas" v={String(tareas.length)} />
            <Dato k="Conexiones" v={String(conexiones.length)} />
            <Dato k="Acciones" v={String(acciones.length)} />
          </dl>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => setVerJson((v) => !v)}>
          {verJson ? "Ver el resumen" : "Ver el JSON"}
        </Button>
      </header>

      {verJson ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            Mostrado con sangría para leerlo; el archivo va en una sola línea.
          </p>
          <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed">
            {JSON.stringify(g, null, 2)}
          </pre>
        </div>
      ) : (
        <>
          <section aria-label="Formularios" className="flex flex-col gap-3">
            <p className={rotulo}>Formularios</p>
            {formularios.length === 0 ? <p className="text-muted-foreground">Sin formularios.</p> : null}
            {formularios.map((f, i) => {
              const campos = lista(f.Campos);
              const titulo = `Formulario ${i + 1} · ${texto(f.nombre) || texto(f.id)}`;
              return (
                <article key={texto(f.id) || i} aria-label={titulo} className="rounded-lg border border-border bg-card p-3">
                  <h4 className="mb-2 text-sm font-semibold">{titulo}</h4>
                  {campos.length === 0 ? (
                    <p className="text-xs text-muted-foreground">Sin campos.</p>
                  ) : (
                    <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                      {campos.map((c, j) => {
                        const opciones = opcionesDe(c);
                        const validacion = texto(c.validacion);
                        const visible = texto(c.dependiente_campo);
                        return (
                          <li key={texto(c.id) || j} className="flex flex-col gap-0.5 rounded-md bg-muted/40 px-2.5 py-2 text-xs">
                            <span className="font-medium text-foreground">{texto(c.etiqueta) || texto(c.nombre)}</span>
                            <span className="font-mono text-[0.6875rem] text-muted-foreground">
                              {texto(c.nombre)} · {TIPO[texto(c.tipo)] ?? texto(c.tipo)}
                              {/required/.test(validacion) ? " · obligatorio" : ""}
                              {si(c.readonly) ? " · solo lectura" : ""}
                            </span>
                            {opciones.length > 0 ? <span className="text-muted-foreground">{opciones.join(", ")}</span> : null}
                            {visible ? <span className="text-muted-foreground">visible si {visible}</span> : null}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </article>
              );
            })}
          </section>

          <section aria-label="Tareas" className="flex flex-col gap-1">
            <p className={rotulo}>Tareas</p>
            {tareas.length === 0 ? <p className="text-muted-foreground">Sin tareas.</p> : null}
            <ul className="flex flex-col gap-1">
              {tareas.map((t, i) => {
                const grupos = lista(t.GruposUsuarios).map((x) => texto(x.nombre)).filter(Boolean);
                const quien = grupos.length > 0 ? grupos.join(", ") : texto(t.asignacion);
                const formularios_ = lista(t.Pasos).map((p) => formNombre.get(texto(p.formulario_id))).filter(Boolean);
                return (
                  <li key={texto(t.id) || i} className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-medium">{texto(t.nombre) || texto(t.id)}</span>
                    {quien ? <span className="text-muted-foreground">{quien}</span> : null}
                    {formularios_.length > 0 ? <span className="text-xs text-muted-foreground">· {formularios_.join(", ")}</span> : null}
                    {si(t.inicial) ? <span className="text-xs text-primary">inicia el trámite</span> : null}
                    {si(t.terminal) ? <span className="text-xs text-primary">lo termina</span> : null}
                  </li>
                );
              })}
            </ul>
          </section>

          <section aria-label="Conexiones" className="flex flex-col gap-1">
            <p className={rotulo}>Conexiones</p>
            {conexiones.length === 0 ? <p className="text-muted-foreground">Sin conexiones.</p> : null}
            <ul className="flex flex-col gap-1">
              {conexiones.map((c, i) => (
                <li key={texto(c.id) || i} className="text-muted-foreground">
                  <span className="text-foreground">
                    {tareaNombre.get(texto(c.tarea_id_origen)) ?? texto(c.tarea_id_origen)} →{" "}
                    {tareaNombre.get(texto(c.tarea_id_destino)) ?? texto(c.tarea_id_destino)}
                  </span>
                  {texto(c.regla) ? <span> · cuando <code className="font-mono text-xs">{texto(c.regla)}</code></span> : null}
                </li>
              ))}
            </ul>
          </section>

          <section aria-label="Acciones" className="flex flex-col gap-1">
            <p className={rotulo}>Acciones</p>
            {acciones.length === 0 ? <p className="text-muted-foreground">Sin acciones.</p> : null}
            <ul className="flex flex-col gap-1">
              {acciones.map((a, i) => (
                <li key={texto(a.id) || i}>
                  <span className="font-medium">{texto(a.nombre) || texto(a.tipo)}</span>
                  <span className="text-muted-foreground">
                    {" "}· {texto(a.tipo)}
                    {texto(a.tarea_id) ? ` · ${texto(a.momento) === "antes" ? "antes de" : "después de"} ${tareaNombre.get(texto(a.tarea_id)) ?? texto(a.tarea_id)}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

function Dato({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-1.5">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-medium">{v}</dd>
    </div>
  );
}
