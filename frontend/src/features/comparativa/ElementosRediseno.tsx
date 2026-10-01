import { Card, CardContent } from "@/components/ui/card";
import type { ElementoRediseno, ResumenElementos } from "@/lib/types";

import { ORDEN_ELEMENTOS, colorDeClase, nombreDeClase } from "./formato";

/**
 * «Qué pasó con cada elemento del trámite»: la tabla «Analisis de eliminacion»
 * del TO-BE, fila por fila. Es la palabra del equipo: la decision y el
 * fundamento van tal como los escribieron, y la clase solo cuenta y colorea.
 *
 * Parte de un todo en CSS y tokens, igual que `BarraDestinos`: la leyenda esta
 * siempre y cada entrada lleva su cuenta escrita, porque el color no es el
 * unico portador.
 */
export default function ElementosRediseno({
  elementos,
  resumen,
}: {
  elementos: ElementoRediseno[];
  resumen: ResumenElementos;
}) {
  const tramos = ORDEN_ELEMENTOS.map((c) => ({ clase: c, n: resumen[c] ?? 0 })).filter(
    (t) => t.n > 0,
  );

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-2">
          <div
            role="img"
            aria-label="Elementos del trámite por decisión"
            className="flex h-7 w-full gap-0.5 overflow-hidden rounded-md"
          >
            {tramos.map((t) => (
              <div
                key={t.clase}
                title={`${nombreDeClase(t.clase)}: ${t.n}`}
                style={{ width: `${(100 * t.n) / resumen.total}%`, background: colorDeClase(t.clase) }}
              />
            ))}
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {tramos.map((t) => (
              <li key={t.clase} aria-label={`${nombreDeClase(t.clase)}: ${t.n}`}
                  className="flex items-center gap-1.5">
                <span aria-hidden className="inline-block size-2.5 rounded-sm"
                      style={{ background: colorDeClase(t.clase) }} />
                {nombreDeClase(t.clase)} · {t.n}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {ORDEN_ELEMENTOS.flatMap((clase) =>
          elementos
            .filter((e) => e.clase === clase)
            .map((e, i) => (
              <li key={`${clase}-${i}-${e.nombre}`}>
                <Card role="article" aria-label={e.nombre} className="h-full py-4"
                      style={{ borderLeft: `4px solid ${colorDeClase(clase)}` }}>
                  <CardContent className="flex flex-col gap-1">
                    <span className="text-[0.6875rem] uppercase tracking-wide text-muted-foreground">
                      {nombreDeClase(clase)}
                    </span>
                    <span className="text-sm font-medium">{e.nombre}</span>
                    <span className="text-sm font-semibold">{e.decision || "Sin respuesta"}</span>
                    {e.fundamento ? (
                      <span className="text-xs text-muted-foreground">{e.fundamento}</span>
                    ) : null}
                  </CardContent>
                </Card>
              </li>
            )),
        )}
      </ul>
    </div>
  );
}
