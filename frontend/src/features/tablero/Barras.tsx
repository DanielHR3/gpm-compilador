/**
 * Barras horizontales en CSS con los tokens del sistema. Sin libreria de
 * graficas: la SPA no carga nada de CDN y esto se lee igual en un telefono.
 */
export interface FilaBarra {
  nombre: string;
  tramites: number;
  porcentaje: number;
  detalle?: string;
}

export default function Barras({ filas, total }: { filas: FilaBarra[]; total: number }) {
  if (filas.length === 0) {
    return <p className="text-sm text-muted-foreground">Nada que contar todavía.</p>;
  }
  return (
    <ul className="flex flex-col gap-3">
      {filas.map((f) => (
        <li key={f.nombre} aria-label={f.nombre} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate font-medium">{f.nombre}</span>
            <span className="shrink-0 text-muted-foreground">
              {f.tramites} de {total} · {f.porcentaje}%
            </span>
          </div>
          <div
            role="meter"
            aria-label={f.nombre}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={f.porcentaje}
            className="h-2 w-full overflow-hidden rounded-full bg-muted"
          >
            <div className="h-full rounded-full bg-primary" style={{ width: `${f.porcentaje}%` }} />
          </div>
          {f.detalle ? <span className="text-xs text-muted-foreground">{f.detalle}</span> : null}
        </li>
      ))}
    </ul>
  );
}
