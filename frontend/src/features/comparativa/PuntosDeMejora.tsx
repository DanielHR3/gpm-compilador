import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { MejoraTramite } from "@/lib/types";

import { accionEnPalabras, fuenteEnPalabras, requiereEnPalabras, tipoDeMejora } from "./formato";

/**
 * «Qué más se puede simplificar»: lo que el tramite ya rediseñado todavia le
 * pide al ciudadano o al funcionario. Lo propone el agente y el servidor solo
 * deja pasar lo que se apoya en una frase del expediente o en un documento
 * que se sigue pidiendo. Decide el equipo: un punto se puede descartar, y un
 * descarte sobrevive a «Volver a analizar».
 */
function Tarjeta({
  mejora,
  onDescartar,
}: {
  mejora: MejoraTramite;
  onDescartar: (id: string, descartada: boolean) => Promise<void>;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requiere = requiereEnPalabras(mejora.requiere);

  async function alternar() {
    setOcupado(true);
    setError(null);
    try {
      await onDescartar(mejora.id, !mejora.descartada);
    } catch {
      setError("No se pudo guardar. Inténtalo otra vez.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Card role="article" aria-label={mejora.titulo}
          className={mejora.descartada ? "h-full opacity-70" : "h-full"}>
      <CardContent className="flex h-full flex-col gap-2">
        <span className="text-[0.6875rem] uppercase tracking-wide text-muted-foreground">
          {tipoDeMejora(mejora.tipo)}
          {accionEnPalabras(mejora.accion) ? ` · ${accionEnPalabras(mejora.accion)}` : ""}
          {mejora.descartada ? " · Descartado" : ""}
        </span>
        <span className="text-sm font-semibold">{mejora.titulo}</span>
        {mejora.descartada ? null : (
          <>
            <p className="text-sm">{mejora.propuesta}</p>
            {mejora.beneficio ? (
              <p className="text-sm">
                <span className="font-medium">Qué se gana: </span>
                {mejora.beneficio}
              </p>
            ) : null}
            <div className="flex flex-col gap-1 border-l-2 border-border pl-3 text-xs text-muted-foreground">
              {mejora.etiqueta_campo ? (
                <span>
                  Documento que se sigue pidiendo:{" "}
                  <span className="font-medium text-foreground">{mejora.etiqueta_campo}</span>
                </span>
              ) : null}
              {mejora.cita ? (
                <span>
                  {fuenteEnPalabras(mejora.fuente)}: «{mejora.cita}»
                </span>
              ) : null}
            </div>
            {requiere ? <span className="text-xs font-medium">{requiere}</span> : null}
          </>
        )}
        {error ? <p role="alert" className="text-xs text-destructive">{error}</p> : null}
        <Button type="button" size="sm" variant="ghost" className="mt-auto self-start"
                disabled={ocupado} onClick={() => void alternar()}>
          {mejora.descartada ? "Restaurar" : "Descartar"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function PuntosDeMejora({
  mejoras,
  onDescartar,
}: {
  mejoras: MejoraTramite[];
  onDescartar: (id: string, descartada: boolean) => Promise<void>;
}) {
  // Lo descartado va al final: sigue a la vista para poder restaurarlo, pero
  // no se mezcla con lo que el equipo todavia tiene que leer.
  const orden = [...mejoras.filter((m) => !m.descartada), ...mejoras.filter((m) => m.descartada)];
  return (
    <ul className="grid gap-3 lg:grid-cols-2">
      {orden.map((m) => (
        <li key={m.id}>
          <Tarjeta mejora={m} onDescartar={onDescartar} />
        </li>
      ))}
    </ul>
  );
}
