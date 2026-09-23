/**
 * Columnas por semana en SVG: marcas finas, eje legible, tooltip nativo por
 * columna (<title>) y una lista oculta con cada valor para lectores de
 * pantalla. Sin libreria: es una forma simple y la SPA no carga nada de CDN.
 */
export interface Semana { semana: string; tramites: number }

const ANCHO = 480;
const ALTO = 140;
const MARGEN = { arriba: 8, abajo: 22, izq: 4, der: 4 };

function corta(semana: string): string {
  const m = /W(\d+)$/.exec(semana);
  return m ? `W${m[1]}` : semana;
}

export default function Actividad({ semanas }: { semanas: Semana[] }) {
  const n = semanas.length;
  const maximo = Math.max(1, ...semanas.map((s) => s.tramites));
  const plotAlto = ALTO - MARGEN.arriba - MARGEN.abajo;
  const plotAncho = ANCHO - MARGEN.izq - MARGEN.der;
  const paso = n ? plotAncho / n : plotAncho;
  const anchoBarra = Math.max(6, paso * 0.62);
  const recientes = semanas.slice(-4).reduce((s, x) => s + x.tramites, 0);
  const etiqueta = (i: number) => i === 0 || i === n - 1 || i % 4 === 0;

  return (
    <figure className="flex flex-col gap-2">
      <svg role="img" aria-label="Trámites por semana" viewBox={`0 0 ${ANCHO} ${ALTO}`} className="w-full">
        <line
          x1={MARGEN.izq} x2={ANCHO - MARGEN.der}
          y1={MARGEN.arriba + plotAlto} y2={MARGEN.arriba + plotAlto}
          stroke="var(--border)" strokeWidth={1}
        />
        {semanas.map((s, i) => {
          const h = (s.tramites / maximo) * plotAlto;
          const x = MARGEN.izq + i * paso + (paso - anchoBarra) / 2;
          const y = MARGEN.arriba + plotAlto - h;
          return (
            <g key={s.semana}>
              <rect x={MARGEN.izq + i * paso} y={MARGEN.arriba} width={paso} height={plotAlto} fill="transparent">
                <title>{`${s.semana}: ${s.tramites}`}</title>
              </rect>
              {s.tramites > 0 ? (
                <rect x={x} y={y} width={anchoBarra} height={h} rx={3} fill="var(--viz-4)" pointerEvents="none" />
              ) : null}
              {etiqueta(i) ? (
                <text
                  x={MARGEN.izq + i * paso + paso / 2} y={ALTO - 6}
                  textAnchor="middle" fontSize={10} fill="var(--muted-foreground)"
                >
                  {corta(s.semana)}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <ul className="sr-only">
        {semanas.map((s) => (
          <li key={s.semana} aria-label={`${s.semana}: ${s.tramites}`}>{s.tramites} trámites</li>
        ))}
      </ul>
      <figcaption className="text-xs text-muted-foreground">
        {recientes} en las últimas 4 semanas
      </figcaption>
    </figure>
  );
}
