import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PantallaVista } from "@/lib/types";

/** El tipo de campo como lo diria una persona, no como lo guarda GPM. */
const TIPO: Record<string, string> = {
  text: "Texto",
  textarea: "Texto largo",
  select: "Lista",
  radio: "Opción única",
  file: "Archivo",
  date: "Fecha",
  date_time: "Fecha y hora",
  paragraph: "Párrafo",
  subtitle: "Subtítulo",
  cart: "Carrito",
  api_ajax: "Consulta a otro sistema",
  documento: "Documento",
};

/**
 * El Diccionario propuesto como lo veria quien llena el tramite: una tarjeta
 * por pantalla y una tarjeta chica por campo. Lo arma el servidor con el
 * extractor de siempre (`vista` en generados.json); aqui solo se pinta.
 */
export default function VistaDiccionario({ pantallas }: { pantallas: PantallaVista[] }) {
  return (
    <div className="flex flex-col gap-4">
      {pantallas.map((p, i) => {
        const titulo = `Pantalla ${i + 1} · ${p.actor} · ${p.nombre}`;
        return (
          <Card key={p.id} role="article" aria-label={titulo} className="py-4">
            <CardHeader>
              <CardTitle className="text-base">{titulo}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {p.campos.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin campos.</p>
              ) : (
                p.campos.map((c, j) => (
                  <div
                    key={`${c.etiqueta}-${j}`}
                    className="flex flex-col gap-1 rounded-md border border-border p-3 text-sm"
                  >
                    <span className="font-medium">
                      {c.etiqueta}
                      {c.obligatorio ? (
                        <span aria-label="obligatorio" className="text-destructive">
                          {" *"}
                        </span>
                      ) : null}
                    </span>
                    <span className="text-muted-foreground">{TIPO[c.tipo] ?? c.tipo}</span>
                    {c.opciones.length > 0 ? <span>{c.opciones.join(" · ")}</span> : null}
                    {c.condicion ? (
                      <span className="text-muted-foreground">Visible solo si {c.condicion}</span>
                    ) : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
