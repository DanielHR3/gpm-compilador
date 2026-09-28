import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Destino, DocumentoTramite } from "@/lib/types";

import { DESTINOS, colorDe, estadoEnPalabras, nombreDe, veredictoEnPalabras } from "./destinos";

/**
 * Un documento que pedia el tramite y que paso con el.
 *
 * Las citas son texto literal del AS-IS y del TO-BE; el motivo es redaccion,
 * y dice de quien. Cambiar destino es un selector y no arrastrar: funciona
 * con teclado y en telefono.
 */
function Cita({ rotulo, texto }: { rotulo: string; texto: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[0.6875rem] uppercase tracking-wide text-muted-foreground">{rotulo}</span>
      <blockquote className="border-l-2 border-border pl-2 text-xs">{texto}</blockquote>
    </div>
  );
}

export default function TarjetaDocumento({
  documento: d,
  onDecidir,
}: {
  documento: DocumentoTramite;
  onDecidir: (destino: Destino, motivo: string) => Promise<void>;
}) {
  const id = useId();
  const propuesto = d.destino === "sin_destino" ? "" : d.destino;
  const [destino, setDestino] = useState<Destino | "">(propuesto);
  const [motivo, setMotivo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Lo ya decidido va compacto: con diez documentos, diez formularios
  // abiertos tapaban lo que importa, que es que paso con cada uno.
  const [abierto, setAbierto] = useState(d.estado === "propuesto");
  const cambio = destino !== propuesto || motivo.trim() !== "";
  const sinFundamento = d.destino === "elimina" && !d.cita_to_be && d.estado !== "propuesto";

  async function guardar(que: Destino, porque: string) {
    setGuardando(true);
    setError(null);
    try {
      await onDecidir(que, porque);
      setMotivo("");
    } catch {
      setError("No se pudo guardar. Lo que elegiste sigue aquí; inténtalo otra vez.");
    } finally {
      setGuardando(false);
    }
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    if (destino) void guardar(destino, motivo.trim());
  }

  return (
    <Card
      role="article"
      aria-label={d.nombre}
      className="h-full border-l-4"
      style={{ borderLeftColor: colorDe(d.destino) }}
    >
      <CardHeader>
        <CardTitle className="text-sm">{d.nombre}</CardTitle>
        <p className="text-xs font-semibold">{nombreDe(d.destino)}</p>
        <p className="text-xs text-muted-foreground">
          {estadoEnPalabras(d.estado)}
          {d.confianza && d.estado === "propuesto" ? ` · Confianza ${d.confianza}` : ""}
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {d.cita_as_is ? (
          <Cita rotulo="En el AS-IS" texto={d.cita_as_is} />
        ) : (
          <p className="text-xs text-muted-foreground">El AS-IS no lo nombra; lo dice el TO-BE.</p>
        )}
        {d.cita_to_be ? <Cita rotulo="En el TO-BE" texto={d.cita_to_be} /> : null}
        {d.campo ? (
          <p className="text-xs text-muted-foreground">
            Campo del trámite: <code>@@{d.campo}</code>
          </p>
        ) : null}
        {d.veredicto ? (
          <p className="rounded-md bg-muted/60 p-2 text-xs">{veredictoEnPalabras(d.veredicto)}</p>
        ) : null}
        {sinFundamento ? (
          <p className="rounded-md bg-muted/60 p-2 text-xs">
            <strong>Eliminado sin fundamento:</strong> el TO-BE no dice por qué dejó de pedirse.
          </p>
        ) : null}
        {d.motivo ? (
          <p className="text-xs">
            <span className="text-muted-foreground">
              {d.motivo_de === "ia" ? "Redacción de la IA" : "Motivo que escribió el analista"}:
            </span>{" "}
            {d.motivo}
          </p>
        ) : null}

        {!abierto ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="self-start"
            onClick={() => setAbierto(true)}
          >
            Cambiar destino
          </Button>
        ) : null}
        {abierto ? (
        <form onSubmit={enviar} className="flex flex-col gap-2 border-t border-border/60 pt-3">
          <label htmlFor={`${id}-destino`} className="flex flex-col gap-1 text-xs">
            Destino
            <select
              id={`${id}-destino`}
              value={destino}
              onChange={(e) => setDestino(e.target.value as Destino | "")}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="" disabled>
                Elige qué pasó con este documento
              </option>
              {DESTINOS.map((x) => (
                <option key={x} value={x}>
                  {nombreDe(x)}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor={`${id}-motivo`} className="flex flex-col gap-1 text-xs">
            Motivo (opcional)
            <textarea
              id={`${id}-motivo`}
              value={motivo}
              maxLength={300}
              rows={2}
              onChange={(e) => setMotivo(e.target.value)}
              className="rounded-md border border-input bg-background px-2 py-1 text-sm"
            />
          </label>
          {error ? (
            <p role="alert" className="text-xs text-destructive">
              {error}
            </p>
          ) : null}
          <div className="flex gap-2">
            {d.estado === "propuesto" && propuesto && !cambio ? (
              <Button
                type="button"
                size="sm"
                className="flex-1"
                disabled={guardando}
                onClick={() => void guardar(propuesto, "")}
              >
                Aceptar
              </Button>
            ) : null}
            <Button
              type="submit"
              size="sm"
              variant="outline"
              className="flex-1"
              disabled={guardando || !destino || !cambio}
            >
              {guardando ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </form>
        ) : null}
      </CardContent>
    </Card>
  );
}
