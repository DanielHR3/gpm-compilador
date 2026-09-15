import { resumirManifiesto } from "./resumen";

/**
 * Lo que el compilador entendió del expediente, devuelto al analista.
 *
 * Quien documenta un trámite en Simplificación no tenía forma de saber si la
 * herramienta leyó bien su Diccionario: los huecos solo cuentan lo que falló.
 * Esta tarjeta cuenta lo que salió bien —«de tu documento salieron 13
 * pantallas, 87 campos, 36 tareas»— y luego la consecuencia: cuántos días de
 * desarrollo cuesta construirlo.
 *
 * Una sola superficie, no cuatro tarjetas iguales: las cifras son un mismo
 * hecho visto por partes, y trocearlas en tarjetas gemelas las igualaría en
 * peso con el resto de la pantalla.
 */
function Cifra({
  valor,
  unidad,
  detalle,
}: {
  valor: number;
  unidad: string;
  detalle?: string;
}) {
  return (
    <figure
      aria-label={`${valor} ${unidad}`}
      className="m-0 flex min-w-24 flex-col gap-0.5"
    >
      <span className="font-heading text-3xl leading-none font-semibold tabular-nums text-foreground">
        {valor}
      </span>
      <figcaption className="text-sm text-muted-foreground">
        {unidad}
        {detalle ? (
          <span className="block text-xs text-muted-foreground/80">{detalle}</span>
        ) : null}
      </figcaption>
    </figure>
  );
}

export default function ResumenExpediente({
  manifiesto,
  estimacion,
}: {
  manifiesto: Record<string, unknown>;
  estimacion: Record<string, unknown>;
}) {
  const r = resumirManifiesto(manifiesto);
  const nivel = typeof estimacion?.nivel === "string" ? estimacion.nivel : null;
  const dias =
    typeof estimacion?.dias === "string" || typeof estimacion?.dias === "number"
      ? String(estimacion.dias)
      : null;

  const plural = (n: number, uno: string, varios: string) =>
    n === 1 ? uno : varios;

  return (
    <section
      aria-label="Resumen del expediente"
      className="flex flex-col gap-5 rounded-xl border border-border bg-card p-6"
    >
      <div className="flex flex-col gap-1">
        <h2 className="font-heading text-xl font-bold tracking-tight text-foreground">
          {r.nombre ?? "Trámite sin nombre confirmado"}
        </h2>
        {r.dependencia ? (
          <p className="text-sm text-muted-foreground">{r.dependencia}</p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-x-10 gap-y-5">
        <Cifra
          valor={r.pantallas}
          unidad={plural(r.pantallas, "pantalla", "pantallas")}
        />
        <Cifra
          valor={r.campos}
          unidad={plural(r.campos, "campo", "campos")}
          detalle={
            r.condicionales > 0
              ? `${r.condicionales} ${plural(r.condicionales, "condicional", "condicionales")}`
              : undefined
          }
        />
        <Cifra
          valor={r.tareas}
          unidad={plural(r.tareas, "tarea", "tareas")}
          detalle={
            r.decisiones > 0
              ? `${r.decisiones} ${plural(r.decisiones, "decisión", "decisiones")}`
              : undefined
          }
        />
        <Cifra
          valor={r.actores}
          unidad={plural(r.actores, "responsable", "responsables")}
        />
      </div>

      {dias || nivel ? (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-border pt-4">
          <span className="text-sm text-muted-foreground">Construirlo toma</span>
          {dias ? (
            <span className="font-heading text-lg font-semibold text-primary">
              {dias}
            </span>
          ) : null}
          {/* El nivel va solo: el backend lo escribe como adjetivo («Complejo»)
              y anteponerle «complejidad» daba «complejidad complejo». */}
          {nivel ? (
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              {nivel}
            </span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
