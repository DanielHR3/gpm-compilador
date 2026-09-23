import { useEffect, useState } from "react";

import {
  Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle,
} from "@/components/ui/card";
import { leerHistorial, urlGpm, type HistorialOut } from "@/lib/api";

/**
 * Seccion «Historial»: los expedientes que hay en el almacen del servidor,
 * del mas reciente al mas viejo. Una tarjeta por tramite (en la SPA no hay
 * tablas): cada una abre la revision (`/revisar/:sid`)
 * o baja el `.gpm` de produccion por la misma descarga del panel de entrega.
 *
 * Hasta el 2026-09-23 esta pagina la pintaba el servidor
 * (`plantillas.historial`), con otro estilo y sin fecha.
 */

const FECHA = new Intl.DateTimeFormat("es-MX", {
  day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
});

function fecha(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : FECHA.format(d);
}

export default function Historial() {
  const [datos, setDatos] = useState<HistorialOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    leerHistorial().then(setDatos).catch(() => setError("No se pudo leer el historial."));
  }, []);

  if (error) return <p role="alert" className="text-sm text-destructive">{error}</p>;
  if (!datos) return <p className="text-sm text-muted-foreground">Cargando…</p>;

  return (
    <section className="flex flex-col gap-4 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Historial</h1>
        <p className="text-sm text-muted-foreground">
          Trámites procesados en este servidor. Las sesiones sin actividad en 7 días se borran solas.
        </p>
      </header>
      {datos.tramites.length === 0 ? (
        <p className="text-sm text-muted-foreground">Todavía no hay ningún trámite procesado.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {datos.tramites.map((t) => (
            <li key={t.sid}>
              <Card role="article" aria-label={t.nombre} className="py-4">
                <CardHeader className="gap-1">
                  <CardTitle className="text-base">
                    <a href={`/revisar/${t.sid}`} className="text-primary underline underline-offset-2">
                      {t.nombre}
                    </a>
                  </CardTitle>
                  <CardDescription>{t.dependencia}</CardDescription>
                  <CardAction>
                    <a href={urlGpm(t.sid)} className="text-sm text-primary underline underline-offset-2">
                      Descargar .gpm
                    </a>
                  </CardAction>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  Última actividad: {fecha(t.modificado)}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
