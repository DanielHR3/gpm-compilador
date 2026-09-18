import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "cn";
import { decidirPropuesta, reconocer, resolver } from "@/lib/api";

import { tituloDeCodigo } from "./lenguaje";

/**
 * Codigos cuyo control redacta su propia pregunta a partir del mensaje.
 *
 * Para estos, pintar `hueco.mensaje` aqui arriba lo duplica en pantalla: se ve
 * el texto crudo del compilador y justo debajo la misma idea bien dicha. El
 * crudo no se pierde, vive en el detalle tecnico del propio control.
 */
const CONTROL_REDACTA_EL_MENSAJE = new Set(["DIC-08", "MMD-03", "MMD-04"]);
import type { Hueco, Propuesta, Resolucion } from "@/lib/types";

/** Color de acento por severidad -- solo estos tres niveles existen hoy. */
const ACENTO_NIVEL: Record<Hueco["nivel"], string> = {
  bloqueante: "border-l-destructive",
  falta_dato: "border-l-amber-500",
  por_confirmar: "border-l-muted-foreground/30",
};

const ETIQUETA_NIVEL: Record<Hueco["nivel"], string> = {
  bloqueante: "Bloqueante",
  falta_dato: "Falta un dato",
  por_confirmar: "Por confirmar",
};

const BADGE_NIVEL: Record<Hueco["nivel"], string> = {
  bloqueante: "bg-destructive/10 text-destructive",
  falta_dato: "bg-amber-50 text-amber-700",
  por_confirmar: "bg-muted text-muted-foreground",
};

import BotonReconocer from "./controles/BotonReconocer";
import ControlActor, { type Actor } from "./controles/ControlActor";
import ControlCampoPadre, { type Campo } from "./controles/ControlCampoPadre";
import ControlCompuerta from "./controles/ControlCompuerta";
import ControlConfirmar from "./controles/ControlConfirmar";
import ControlTexto from "./controles/ControlTexto";
import ControlVisibilidad from "./controles/ControlVisibilidad";
import { useAccion } from "./useAccion";

/**
 * Forma de la respuesta de `resolver`/`reconocer` que el wizard fusiona en su
 * estado local. `resolver` trae `manifiesto` + `huecos`; `reconocer` trae
 * `huecos` + `reconocidos`.
 */
export type RespuestaResuelto = {
  manifiesto?: Record<string, unknown>;
  huecos: Hueco[];
  reconocidos?: [string, string][];
};

/** Lee `manifiesto.actores[]` de forma tolerante (el manifiesto no esta tipado). */
function leerActores(manifiesto: Record<string, unknown>): Actor[] {
  const bruto = manifiesto.actores;
  if (!Array.isArray(bruto)) return [];
  const out: Actor[] = [];
  for (const item of bruto) {
    if (item && typeof item === "object") {
      const o = item as Record<string, unknown>;
      if (typeof o.id === "string" && typeof o.nombre === "string") {
        out.push({ id: o.id, nombre: o.nombre });
      }
    }
  }
  return out;
}

/** Aplana `manifiesto.pantallas[].campos[]` a `{ nombre }`. */
function leerCampos(manifiesto: Record<string, unknown>): Campo[] {
  const pantallas = manifiesto.pantallas;
  if (!Array.isArray(pantallas)) return [];
  const out: Campo[] = [];
  for (const pantalla of pantallas) {
    if (!pantalla || typeof pantalla !== "object") continue;
    const campos = (pantalla as Record<string, unknown>).campos;
    if (!Array.isArray(campos)) continue;
    for (const campo of campos) {
      if (campo && typeof campo === "object") {
        const nombre = (campo as Record<string, unknown>).nombre;
        if (typeof nombre === "string") out.push({ nombre });
      }
    }
  }
  return out;
}

/**
 * Una `Card` por hueco. Elige el control por `hueco.codigo` y, al confirmar,
 * llama `/api/v1` (`resolver` o `reconocer`) y sube la respuesta al wizard con
 * `onResuelto` — sin recargar la pagina.
 */
export default function TarjetaHueco({
  hueco,
  manifiesto,
  sid,
  onResuelto,
  ultimoActor = "",
  propuesta = null,
}: {
  hueco: Hueco;
  manifiesto: Record<string, unknown>;
  sid: string;
  /** Actor elegido en el MMD-03 anterior; se propone ya seleccionado. */
  ultimoActor?: string;
  onResuelto: (nuevo: RespuestaResuelto, hueco: Hueco, valor?: string) => void;
  /** Propuesta del generador de IA para este DIC-08, si la hay. */
  propuesta?: Propuesta | null;
}) {
  // El wizard necesita saber CUAL hueco se resolvio para poder anunciarlo;
  // los controles siguen emitiendo solo la respuesta de la API.
  const reportar = (resp: RespuestaResuelto, valor?: string) =>
    onResuelto(resp, hueco, valor);
  const { ejecutar, guardando } = useAccion();

  const resolverCon = async (tipo: Resolucion["tipo"], valor: string) => {
    await ejecutar(async () => {
      const resp = await resolver(sid, [
        { tipo, ubicacion: hueco.ubicacion, valor },
      ]);
      reportar(resp, valor);
    });
  };

  const reconocerHueco = async () => {
    await ejecutar(async () => {
      const resp = await reconocer(sid, hueco.codigo, hueco.ubicacion);
      reportar(resp);
    });
  };

  let control: ReactNode = null;
  if (hueco.codigo === "MMD-03" && hueco.nivel === "falta_dato") {
    // Solo el MMD-03 *por nodo* lleva control: su `ubicacion` es el id de un
    // nodo del diagrama, que `/resolver` sabe traducir a la Tarea real. El
    // MMD-03 colapsado (`por_confirmar`, ubicacion "flujo") no nombra ninguna
    // tarea -- mandarlo a `/resolver` daria 422 -- y como no bloquea, se lee y
    // se revisa el diagrama, nada mas. Ver `_colapsar_mmd03` en
    // `extractores/expediente.py`.
    control = (
      <div className="flex flex-col gap-2">
        <ControlActor
          guardando={guardando}
          valorInicial={ultimoActor}
          hueco={hueco}
          actores={leerActores(manifiesto)}
          onConfirmar={(v) => resolverCon("mmd03", v)}
        />
        {/* Mueve el trabajo a la plataforma en vez de eliminarlo: es la
            decision con mas consecuencias del flujo y estaba pintada como un
            enlace gris de 12 px. Boton de contorno: visible, secundario. */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={reconocerHueco}
        >
          o lo configuro a mano
        </Button>
      </div>
    );
  } else if (hueco.codigo === "META-01") {
    control = (
      <ControlTexto
        guardando={guardando}
        hueco={hueco}
        onConfirmar={(v) => resolverCon("meta01", v)}
      />
    );
  } else if (hueco.codigo === "META-02") {
    control = (
      <ControlTexto
        guardando={guardando}
        hueco={hueco}
        onConfirmar={(v) => resolverCon("meta02", v)}
      />
    );
  } else if (hueco.codigo === "META-04") {
    control = (
      <ControlTexto
        guardando={guardando}
        hueco={hueco}
        onConfirmar={(v) => resolverCon("meta04", v)}
      />
    );
  } else if (hueco.codigo === "API-03") {
    control = (
      <ControlCampoPadre
        guardando={guardando}
        hueco={hueco}
        campos={leerCampos(manifiesto)}
        onConfirmar={(v) => resolverCon("api03", v)}
      />
    );
  } else if (hueco.codigo === "DIC-08") {
    control = (
      <div className="flex flex-col gap-2">
        {/* `key`: ControlVisibilidad toma `propuesta` al montar. Las tarjetas se
            montan ANTES de que el generador termine, asi que cuando la
            propuesta llega el control se remonta prellenado. */}
        <ControlVisibilidad
          key={propuesta ? propuesta.id : "manual"}
          hueco={hueco}
          sid={sid}
          manifiesto={manifiesto}
          onResuelto={reportar}
          propuesta={propuesta}
          onDecision={
            propuesta
              ? async (d, cf) => {
                  await decidirPropuesta(sid, propuesta.id, d, cf ?? null);
                }
              : undefined
          }
        />
        {/* Mueve el trabajo a la plataforma en vez de eliminarlo: es la
            decision con mas consecuencias del flujo y estaba pintada como un
            enlace gris de 12 px. Boton de contorno: visible, secundario. */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={reconocerHueco}
        >
          o lo configuro a mano
        </Button>
      </div>
    );
  } else if (hueco.codigo === "MMD-04") {
    control = (
      <div className="flex flex-col gap-2">
        <ControlCompuerta
          hueco={hueco}
          sid={sid}
          manifiesto={manifiesto}
          onResuelto={reportar}
        />
        {/* Mueve el trabajo a la plataforma en vez de eliminarlo: es la
            decision con mas consecuencias del flujo y estaba pintada como un
            enlace gris de 12 px. Boton de contorno: visible, secundario. */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={reconocerHueco}
        >
          o lo configuro a mano
        </Button>
      </div>
    );
  } else if (hueco.nivel === "por_confirmar") {
    control = (
      <ControlConfirmar
        hueco={hueco}
        guardando={guardando}
        onConfirmar={reconocerHueco}
      />
    );
  } else if (hueco.nivel === "falta_dato") {
    control = <BotonReconocer hueco={hueco} onReconocer={reconocerHueco} />;
  } else if (hueco.nivel === "bloqueante") {
    control = (
      <p className="text-sm text-muted-foreground">
        Esta inconsistencia se corrige en los insumos: vuelve a subirlos con el archivo
        que falta.
      </p>
    );
  }

  return (
    <Card
      className={cn(
        "border-l-4",
        ACENTO_NIVEL[hueco.nivel] ?? "border-l-border",
      )}
    >
      <CardHeader className="flex items-center justify-between gap-2 space-y-0">
        {/* El codigo de validacion no dice nada a quien documenta un tramite;
            vive en el detalle tecnico de cada control. */}
        <CardTitle
          role="heading"
          aria-level={3}
          className="text-sm font-semibold tracking-tight text-foreground"
        >
          {tituloDeCodigo(hueco.codigo)}
        </CardTitle>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            BADGE_NIVEL[hueco.nivel] ?? "bg-muted text-muted-foreground",
          )}
        >
          {ETIQUETA_NIVEL[hueco.nivel] ?? hueco.nivel}
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {/* El MMD-03 colapsado no lleva ControlActor (ver mas arriba), asi que
            nadie redacta su pregunta. Lleva el control generico de confirmar,
            que no redacta nada: sin esta excepcion la tarjeta salia vacia. */}
        {!CONTROL_REDACTA_EL_MENSAJE.has(hueco.codigo) ||
        (hueco.codigo === "MMD-03" && hueco.nivel !== "falta_dato") ? (
          <p className="text-sm font-medium text-foreground">{hueco.mensaje}</p>
        ) : null}
        {hueco.propuesta ? (
          <p className="text-sm text-muted-foreground">
            Propuesta: {hueco.propuesta}
          </p>
        ) : null}
        {control}
      </CardContent>
    </Card>
  );
}
