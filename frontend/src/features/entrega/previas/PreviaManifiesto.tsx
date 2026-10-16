import VistaDiccionario from "@/features/propuestas/VistaDiccionario";
import type { CampoVista, PantallaVista } from "@/lib/types";

type Dict = Record<string, unknown>;
const lista = (v: unknown): Dict[] => (Array.isArray(v) ? v.filter((x) => x && typeof x === "object") as Dict[] : []);
const texto = (v: unknown): string => (typeof v === "string" ? v : typeof v === "number" ? String(v) : "");

/** `{campo, igual}` → «campo = valor», como lo lee una persona. */
function condicionEnPalabras(c: unknown): string | null {
  if (!c || typeof c !== "object") return null;
  const d = c as Dict;
  const campo = texto(d.campo);
  if (!campo) return null;
  if ("igual" in d) return `${campo} = ${texto(d.igual)}`;
  if ("distinto" in d) return `${campo} ≠ ${texto(d.distinto)}`;
  if (Array.isArray(d.y)) return d.y.map(condicionEnPalabras).filter(Boolean).join(" y ");
  return campo;
}

/** Las pantallas del manifiesto, en la forma que ya pinta `VistaDiccionario`. */
export function pantallasDelManifiesto(manifiesto: Dict): PantallaVista[] {
  const actores = new Map(lista(manifiesto.actores).map((a) => [texto(a.id), texto(a.nombre) || texto(a.id)]));
  return lista(manifiesto.pantallas).map((p, i) => ({
    id: texto(p.id) || `p${i + 1}`,
    nombre: texto(p.nombre),
    actor: actores.get(texto(p.actor)) ?? texto(p.actor),
    campos: lista(p.campos).map((c): CampoVista => ({
      etiqueta: texto(c.etiqueta) || texto(c.nombre),
      tipo: texto(c.tipo) || (c.solo_lectura ? "paragraph" : "text"),
      obligatorio: c.obligatorio === true,
      opciones: lista(c.catalogo).map((o) => texto(o.etiqueta) || texto(o.valor)).filter(Boolean),
      condicion: condicionEnPalabras(c.condicion_visible),
    })),
  }));
}

/**
 * El manifiesto como lo leería una persona, sin YAML: el trámite, quién
 * interviene, cada pantalla con sus campos (la misma tarjeta que Propuestas)
 * y el flujo en palabras. El archivo que se descarga sigue siendo el YAML.
 */
export default function PreviaManifiesto({ manifiesto }: { manifiesto: Dict }) {
  const tramite = (manifiesto.tramite ?? {}) as Dict;
  const ruts = (tramite.ruts ?? {}) as Dict;
  const actores = lista(manifiesto.actores);
  const nombres = new Map(actores.map((a) => [texto(a.id), texto(a.nombre) || texto(a.id)]));
  const flujo = (manifiesto.flujo ?? {}) as Dict;
  const tareas = lista(flujo.tareas);
  const conexiones = lista(flujo.conexiones);
  const tareaNombre = new Map(tareas.map((t) => [texto(t.id), texto(t.nombre) || texto(t.id)]));
  const pantallas = pantallasDelManifiesto(manifiesto);
  const rotulo = "font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground";

  return (
    <div className="flex flex-col gap-5 text-sm">
      <header className="flex flex-col gap-1">
        <h3 className="text-lg font-bold tracking-tight">{texto(tramite.nombre) || "Trámite sin nombre"}</h3>
        {texto(tramite.dependencia) ? <p className="text-muted-foreground">{texto(tramite.dependencia)}</p> : null}
        <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-xs">
          {texto(tramite.homoclave) ? <Dato k="Homoclave" v={texto(tramite.homoclave)} /> : null}
          {texto(ruts.tiempo_entrega) ? <Dato k="Tiempo de entrega" v={texto(ruts.tiempo_entrega)} /> : null}
          {texto(ruts.costo) ? <Dato k="Costo" v={texto(ruts.costo)} /> : null}
          {texto(ruts.type_of_person) ? <Dato k="Persona" v={texto(ruts.type_of_person)} /> : null}
        </dl>
      </header>

      {actores.length > 0 ? (
        <section aria-label="Actores" className="flex flex-col gap-1">
          <p className={rotulo}>Actores</p>
          <ul className="flex flex-wrap gap-2">
            {actores.map((a) => (
              <li key={texto(a.id)} className="rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-xs">
                {texto(a.nombre) || texto(a.id)}
                {texto(a.tipo) ? <span className="text-muted-foreground"> · {texto(a.tipo)}</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-label="Pantallas" className="flex flex-col gap-2">
        <p className={rotulo}>Pantallas · {pantallas.length}</p>
        {pantallas.length === 0 ? <p className="text-muted-foreground">Sin pantallas.</p> : <VistaDiccionario pantallas={pantallas} />}
      </section>

      {tareas.length > 0 || conexiones.length > 0 ? (
        <section aria-label="Flujo" className="flex flex-col gap-1">
          <p className={rotulo}>Flujo · {tareas.length} tareas · {conexiones.length} conexiones</p>
          <ul className="flex flex-col gap-1">
            {tareas.map((t) => (
              <li key={texto(t.id)} className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-medium">{texto(t.nombre) || texto(t.id)}</span>
                <span className="text-muted-foreground">{nombres.get(texto(t.actor)) ?? texto(t.actor)}</span>
                {t.inicial ? <span className="text-xs text-primary">inicia el trámite</span> : null}
                {t.terminal ? <span className="text-xs text-primary">lo termina</span> : null}
              </li>
            ))}
            {conexiones.map((c, i) => {
              const cuando = condicionEnPalabras(c.cuando);
              return (
                <li key={`c${i}`} className="text-muted-foreground">
                  {tareaNombre.get(texto(c.de)) ?? texto(c.de)} → {tareaNombre.get(texto(c.a)) ?? texto(c.a)}
                  {cuando ? <span> · cuando {cuando}</span> : null}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
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
