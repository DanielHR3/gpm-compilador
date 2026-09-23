import { Card, CardContent } from "@/components/ui/card";

/** Fila de cifras: una tarjeta por indicador, con la cifra grande y su etiqueta. */
export interface Cifra { etiqueta: string; valor: number | string; nota?: string }

export default function Indicadores({ cifras }: { cifras: Cifra[] }) {
  return (
    <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {cifras.map((c) => (
        <li key={c.etiqueta}>
          <Card role="article" aria-label={c.etiqueta} className="h-full py-4">
            <CardContent className="flex flex-col gap-1">
              <span className="text-3xl font-bold leading-none tracking-tight text-primary">{c.valor}</span>
              <span className="text-xs font-medium text-foreground">{c.etiqueta}</span>
              {c.nota ? <span className="text-[0.6875rem] text-muted-foreground">{c.nota}</span> : null}
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}
