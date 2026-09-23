import { colorDe, pasoDe, tintaDe } from "./escala";

/**
 * Mapa de calor sobre una rejilla CSS (no una <table>): una celda por cruce,
 * con el valor escrito encima —el color nunca es la unica lectura— y la misma
 * informacion como lista plegada, para quien no lee color o imprime.
 */
interface Props {
  titulo: string;
  filas: string[];
  columnas: string[];
  celdas: number[][];
  maximo?: number;
  /** «cuenta» pinta la magnitud; «presencia» solo si/no. */
  modo?: "cuenta" | "presencia";
  etiquetaFila?: (f: string) => string;
  etiquetaColumna?: (c: string) => string;
  /** Segunda linea bajo la cabecera de columna (p. ej. el codigo). */
  subtituloColumna?: (c: string) => string | null;
}

export default function MapaCalor({
  titulo, filas, columnas, celdas, maximo, modo = "cuenta",
  etiquetaFila = (f) => f, etiquetaColumna = (c) => c, subtituloColumna = () => null,
}: Props) {
  if (filas.length === 0 || columnas.length === 0) {
    return <p className="text-sm text-muted-foreground">Nada que cruzar todavía.</p>;
  }
  const tope = modo === "presencia" ? 1 : (maximo ?? Math.max(0, ...celdas.flat()));
  const texto = (v: number) => (modo === "presencia" ? (v ? "sí" : "no") : String(v));
  // Ancho minimo por columna: con veinte inconsistencias las cabeceras se
  // pisaban; el contenedor ya desplaza en horizontal.
  const columnasCss = `minmax(9rem, 1.4fr) repeat(${columnas.length}, minmax(4.5rem, 1fr))`;

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto">
        <div role="grid" aria-label={titulo} className="grid gap-0.5 text-xs" style={{ gridTemplateColumns: columnasCss }}>
          <div role="row" className="contents">
            {/* La esquina tiene que OCUPAR su celda: con `sr-only` (posicion
                absoluta) la rejilla entera se corre una columna y las etiquetas
                de fila acaban a la derecha. */}
            <div role="columnheader" aria-label="Fila" className="min-h-4" />
            {columnas.map((c) => (
              <div key={c} role="columnheader" className="flex flex-col justify-end px-1 pb-1 text-center leading-tight break-words hyphens-auto">
                <span className="font-medium">{etiquetaColumna(c)}</span>
                {subtituloColumna(c) ? (
                  <span className="font-mono text-[0.625rem] text-muted-foreground">{subtituloColumna(c)}</span>
                ) : null}
              </div>
            ))}
          </div>
          {filas.map((f, i) => (
            <div key={f} role="row" className="contents">
              <div role="rowheader" className="truncate py-2 pr-2 font-medium" title={etiquetaFila(f)}>
                {etiquetaFila(f)}
              </div>
              {columnas.map((c, j) => {
                const v = celdas[i]?.[j] ?? 0;
                const paso = modo === "presencia" ? (v ? 5 : 0) : pasoDe(v, tope);
                return (
                  <div
                    key={c}
                    role="gridcell"
                    aria-label={`${etiquetaFila(f)} · ${etiquetaColumna(c)}: ${texto(v)}`}
                    title={`${etiquetaFila(f)} · ${etiquetaColumna(c)}: ${texto(v)}`}
                    data-paso={paso}
                    className="flex h-9 items-center justify-center rounded-sm transition-colors"
                    style={{ background: colorDe(paso), color: tintaDe(paso) }}
                  >
                    {v ? (modo === "presencia" ? "●" : v) : ""}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      {modo === "cuenta" && tope > 0 ? (
        <div role="img" aria-label={`Escala: de 1 a ${tope}`} className="flex items-center gap-1.5 self-end text-[0.6875rem] text-muted-foreground">
          <span>1</span>
          {[1, 2, 3, 4, 5].map((p) => (
            <span key={p} aria-hidden className="inline-block h-2.5 w-4 rounded-sm" style={{ background: colorDe(p) }} />
          ))}
          <span>{tope}</span>
        </div>
      ) : null}
      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer">Ver como lista</summary>
        <ul className="mt-1 flex flex-col gap-0.5">
          {filas.flatMap((f, i) =>
            columnas
              .map((c, j) => ({ c, v: celdas[i]?.[j] ?? 0 }))
              .filter(({ v }) => v > 0)
              .map(({ c, v }) => (
                <li key={`${f}-${c}`}>
                  {etiquetaFila(f)} · {etiquetaColumna(c)}: {texto(v)}
                </li>
              )),
          )}
        </ul>
      </details>
    </div>
  );
}
