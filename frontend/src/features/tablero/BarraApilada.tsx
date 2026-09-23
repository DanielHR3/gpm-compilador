import { colorDe, tintaDe } from "./escala";

/**
 * Parte-de-un-todo en una barra horizontal apilada, con etiqueta directa en
 * cada segmento que cabe y leyenda siempre presente. Los niveles son una
 * escala ordenada, asi que el color es secuencial: mas alto, mas oscuro.
 */
export interface Segmento { nombre: string; valor: number }

const PASO_POR_POSICION = [5, 3, 1, 2, 4];

export default function BarraApilada({ titulo, segmentos }: { titulo: string; segmentos: Segmento[] }) {
  const total = segmentos.reduce((s, x) => s + x.valor, 0);
  if (total === 0) {
    return <p className="text-sm text-muted-foreground">Nada que contar todavía.</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      <div role="img" aria-label={titulo} className="flex h-7 w-full gap-0.5 overflow-hidden rounded-md">
        {segmentos.map((s, i) => {
          const pct = (100 * s.valor) / total;
          if (pct === 0) return null;
          const paso = PASO_POR_POSICION[i % PASO_POR_POSICION.length];
          return (
            <div
              key={s.nombre}
              title={`${s.nombre}: ${s.valor} (${Math.round(pct)}%)`}
              className="flex items-center justify-center overflow-hidden text-xs font-medium"
              style={{ width: `${pct}%`, background: colorDe(paso), color: tintaDe(paso) }}
            >
              {pct >= 12 ? s.nombre : ""}
            </div>
          );
        })}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {segmentos.map((s, i) => (
          <li key={s.nombre} aria-label={`${s.nombre}: ${s.valor} (${Math.round((100 * s.valor) / total)}%)`} className="flex items-center gap-1.5">
            <span aria-hidden className="inline-block size-2.5 rounded-sm" style={{ background: colorDe(PASO_POR_POSICION[i % PASO_POR_POSICION.length]) }} />
            {s.nombre} · {s.valor}
          </li>
        ))}
      </ul>
    </div>
  );
}
