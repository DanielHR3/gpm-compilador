import { useState } from "react";
import { Check, Eye, Lightbulb, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { camposDelManifiesto, resolverDic08 } from "@/lib/api";
import type { Condicion, Hueco, Propuesta } from "@/lib/types";

import {
  describirCondicion,
  ejemploDeVisibilidad,
  leerMensajeVisibilidad,
  pistaDeCodigo,
} from "../lenguaje";
import { useAccion } from "../useAccion";

import ConstructorRegla from "./ConstructorRegla";
import DetalleTecnico from "./DetalleTecnico";

/**
 * Control para `DIC-08`: el Diccionario declaró una condición de visibilidad
 * que el parser no supo traducir, y hay que armarla a mano.
 *
 * La tarjeta está escrita para quien documenta el trámite, no para quien
 * programa el compilador: encabeza con una pregunta, nombra el campo por la
 * etiqueta que ve el ciudadano y lee la regla armada como frase para que se
 * pueda comprobar. El código del hueco, el nombre interno del campo y la frase
 * cruda del Diccionario siguen ahí, plegados: hacen falta para rastrear y
 * reportar, pero no para decidir.
 *
 * Con `propuesta` (Fase 2, generador de IA) el constructor arranca prellenado
 * y aparecen Aceptar / Corregir / Descartar con la cita de dónde salió. La
 * escritura sigue siendo `resolverDic08`; `onDecision` solo anota, después.
 */
export default function ControlVisibilidad({
  hueco,
  sid,
  manifiesto,
  onResuelto,
  propuesta = null,
  onDecision,
  onReconocer,
}: {
  hueco: Hueco;
  sid: string;
  manifiesto: Record<string, unknown>;
  onResuelto: (resp: { manifiesto: Record<string, unknown>; huecos: Hueco[] }) => void;
  /** Propuesta del generador de IA para este campo, si la hay. */
  propuesta?: Propuesta | null;
  /** Anota qué se hizo con la propuesta. Se llama DESPUÉS de resolver. */
  onDecision?: (
    decision: "aceptada" | "corregida" | "descartada",
    condicionFinal?: Condicion,
  ) => Promise<void>;
  /** Mueve el dato a la plataforma. Sin esto la salida no se dibuja. */
  onReconocer?: () => void | Promise<void>;
}) {
  // Con propuesta el constructor arranca prellenado; `descartada` la retira y
  // vuelve al modo manual de siempre.
  const [activa, setActiva] = useState<Propuesta | null>(propuesta);
  const [condicion, setCondicion] = useState<Condicion | null>(propuesta?.condicion ?? null);
  const [editando, setEditando] = useState(false);
  const { ejecutar, guardando, error } = useAccion();
  const campos = camposDelManifiesto(manifiesto);
  const leido = leerMensajeVisibilidad(hueco.mensaje);
  const frase = describirCondicion(condicion, campos);
  const pista = pistaDeCodigo(hueco.codigo);
  // Un ejemplo con los campos de este expediente se lee de una vez; el de
  // PISTAS habla de otro tramite y solo sirve cuando no hay con que armarlo.
  const ejemplo = ejemploDeVisibilidad(campos, leido) ?? pista?.ejemplo ?? null;

  const resolver = async (cond: Condicion) => {
    const resp = await resolverDic08(sid, hueco.ubicacion, cond);
    onResuelto(resp);
  };

  const guardar = async () => {
    if (!condicion) return;
    await ejecutar(async () => {
      await resolver(condicion);
      // Si venía de una propuesta y se editó, es "corregida". Si el registro
      // falla, la resolución ya quedó: no se deshace nada.
      if (activa && onDecision) await onDecision("corregida", condicion);
    });
  };

  const aceptar = async () => {
    if (!activa?.condicion) return;
    const cond = activa.condicion;
    await ejecutar(async () => {
      await resolver(cond);
      if (onDecision) await onDecision("aceptada", undefined);
    });
  };

  const descartar = async () => {
    if (!activa) return;
    if (onDecision) await onDecision("descartada", undefined);
    setActiva(null);
    setCondicion(null);
    setEditando(false);
  };

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-base font-semibold tracking-tight text-foreground">
        ¿Cuándo debe verse{" "}
        {leido ? `«${leido.etiqueta}»` : "este campo"}?
      </h3>

      {/* La frase que escribio Simplificacion es la respuesta a la pregunta:
          va antes que nada, sin plegar. Estaba bajo "Ver detalle tecnico",
          debajo del boton Guardar, y el ejemplo generico ocupaba su lugar. */}
      {leido?.frase ? (
        <div
          data-testid="frase-diccionario"
          className="flex flex-col gap-1 rounded-lg border-l-4 border-secondary bg-muted/40 px-3 py-2"
        >
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Esto fue lo que se escribió en el Diccionario
          </span>
          <p className="text-sm text-foreground">«{leido.frase}»</p>
        </div>
      ) : null}

      {pista ? (
        <div className="flex flex-col gap-1.5 text-sm text-muted-foreground">
          <p>{pista.instruccion}</p>
          {/* Plegado aunque sea de campos propios: la respuesta a la pregunta
              es la frase del Diccionario de arriba, no el ejemplo. */}
          {ejemplo ? (
            <details
              role="group"
              aria-label="¿Cómo se ve un ejemplo?"
              className="rounded-md border border-dashed border-border px-3 py-2"
            >
              <summary className="cursor-pointer">¿Cómo se ve un ejemplo?</summary>
              <p className="mt-2 flex items-start gap-2">
                <Lightbulb aria-hidden className="mt-0.5 size-3.5 shrink-0 text-secondary" />
                <span>{ejemplo}</span>
              </p>
            </details>
          ) : null}
        </div>
      ) : null}

      {/* La fila de abajo es la continuacion de esta frase, no un formulario
          aparte: decia "Muestralo solo cuando:", y ese "lo" obligaba a recordar
          de que campo hablaba la tarjeta mientras se elegia en tres cajas. */}
      <p className="text-sm text-muted-foreground">
        Muestra {leido ? `«${leido.etiqueta}»` : "este campo"} solo cuando
      </p>
      {/* `key`: ConstructorRegla solo lee `value` al montar. Al descartar la
          propuesta se remonta vacío en vez de conservar las filas prellenadas. */}
      <ConstructorRegla
        key={activa ? activa.id : "manual"}
        campos={campos}
        objetivo={
          leido
            ? {
                interno: leido.interno,
                // Si no se localiza el campo del hueco, se le supone la
                // ultima pantalla: asi no se descarta NADA por «se captura
                // despues». Suponer la primera hacia lo contrario —marcaba
                // todo el expediente como imposible— y es el peor error
                // posible aqui: esconder la respuesta correcta.
                pantalla:
                  campos.find((c) => c.nombre === leido.interno)?.pantalla ??
                  Number.MAX_SAFE_INTEGER,
              }
            : null
        }
        frase={leido?.frase ?? ""}
        value={activa ? activa.condicion : null}
        onChange={setCondicion}
        marcadorValor={pista?.marcador}
      />

      {frase ? (
        <p className="flex items-start gap-2 rounded-lg bg-muted/50 p-3 text-sm text-foreground">
          <Eye aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
          <span>
            Quedará así: {leido ? `«${leido.etiqueta}»` : "el campo"} se mostrará
            solo si <strong>{frase}</strong>.
          </span>
        </p>
      ) : null}

      {activa ? (
        <div className="flex flex-col gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm">
          <p className="flex items-start gap-2">
            <Sparkles aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
            <span>
              <span className="font-medium text-foreground">Propuesto a partir de: </span>
              {/* La frase ya se lee arriba, entera. Repetirla aqui la ponia tres
                  veces en la misma tarjeta; solo se cita si NO es la de arriba. */}
              {activa.cita.texto !== leido?.frase ? <>«{activa.cita.texto}» — </> : null}
              {activa.cita.fuente} · {activa.cita.pantalla_nombre} ·{" "}
              {activa.cita.campo}
              <span className="ml-2 text-xs text-muted-foreground">
                (confianza {activa.confianza})
              </span>
            </span>
          </p>
          {!editando ? (
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={aceptar} disabled={guardando} aria-busy={guardando}>
                <Check aria-hidden className="size-4" />
                Aceptar
              </Button>
              <Button type="button" variant="outline" onClick={() => setEditando(true)} disabled={guardando}>
                Corregir
              </Button>
              <Button type="button" variant="ghost" onClick={descartar} disabled={guardando}>
                <X aria-hidden className="size-4" />
                Descartar
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <p>{error.message}</p>
        </div>
      ) : null}

      {!activa || editando ? (
        <Button
          type="button"
          aria-busy={guardando}
          disabled={!condicion || guardando}
          onClick={guardar}
          className="self-start"
        >
          <Check aria-hidden className="size-4" />
          {guardando ? "Guardando…" : "Guardar"}
        </Button>
      ) : null}

      {/* No toda condicion es una comparacion entre campos: «Solo si la
          validacion de formato detecta errores al enviar» es un estado del
          sistema y no hay campo que elegir. Esa salida estaba al final de la
          tarjeta, en gris, despues del detalle tecnico. */}
      {onReconocer ? (
        <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/30 p-3">
          <p className="text-sm text-muted-foreground">
            ¿La frase no depende de otro campo del formulario? Entonces no es una
            regla que el compilador pueda armar: se configura directamente en la
            plataforma.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="self-start"
            disabled={guardando}
            onClick={() => onReconocer()}
          >
            Lo configuro a mano
          </Button>
        </div>
      ) : null}

      <DetalleTecnico
        codigo={hueco.codigo}
        ubicacion={hueco.ubicacion}
        crudo={hueco.mensaje}
        extra={
          leido ? (
            <div className="flex gap-2">
              <dt className="font-medium">Nombre interno:</dt>
              <dd className="font-mono">{leido.interno}</dd>
            </div>
          ) : null
        }
      />
    </div>
  );
}
