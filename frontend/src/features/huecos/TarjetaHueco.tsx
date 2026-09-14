import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "cn";
import { reconocer, resolver } from "@/lib/api";
import type { Hueco, Resolucion } from "@/lib/types";

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
import ControlTexto from "./controles/ControlTexto";
import ControlVisibilidad from "./controles/ControlVisibilidad";

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
}: {
  hueco: Hueco;
  manifiesto: Record<string, unknown>;
  sid: string;
  onResuelto: (nuevo: RespuestaResuelto, hueco: Hueco) => void;
}) {
  // El wizard necesita saber CUAL hueco se resolvio para poder anunciarlo;
  // los controles siguen emitiendo solo la respuesta de la API.
  const reportar = (resp: RespuestaResuelto) => onResuelto(resp, hueco);

  const resolverCon = async (tipo: Resolucion["tipo"], valor: string) => {
    const resp = await resolver(sid, [
      { tipo, ubicacion: hueco.ubicacion, valor },
    ]);
    reportar(resp);
  };

  const reconocerHueco = async () => {
    const resp = await reconocer(sid, hueco.codigo, hueco.ubicacion);
    reportar(resp);
  };

  let control: ReactNode = null;
  if (hueco.codigo === "MMD-03") {
    control = (
      <ControlActor
        hueco={hueco}
        actores={leerActores(manifiesto)}
        onConfirmar={(v) => resolverCon("mmd03", v)}
      />
    );
  } else if (hueco.codigo === "META-01") {
    control = (
      <ControlTexto
        hueco={hueco}
        onConfirmar={(v) => resolverCon("meta01", v)}
      />
    );
  } else if (hueco.codigo === "META-02") {
    control = (
      <ControlTexto
        hueco={hueco}
        onConfirmar={(v) => resolverCon("meta02", v)}
      />
    );
  } else if (hueco.codigo === "META-04") {
    control = (
      <ControlTexto
        hueco={hueco}
        onConfirmar={(v) => resolverCon("meta04", v)}
      />
    );
  } else if (hueco.codigo === "API-03") {
    control = (
      <ControlCampoPadre
        hueco={hueco}
        campos={leerCampos(manifiesto)}
        onConfirmar={(v) => resolverCon("api03", v)}
      />
    );
  } else if (hueco.codigo === "DIC-08") {
    control = (
      <div className="flex flex-col gap-2">
        <ControlVisibilidad
          hueco={hueco}
          sid={sid}
          manifiesto={manifiesto}
          onResuelto={reportar}
        />
        <button
          type="button"
          className="self-start text-xs text-muted-foreground underline-offset-2 hover:underline"
          onClick={reconocerHueco}
        >
          o lo configuro a mano
        </button>
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
        <button
          type="button"
          className="self-start text-xs text-muted-foreground underline-offset-2 hover:underline"
          onClick={reconocerHueco}
        >
          o lo configuro a mano
        </button>
      </div>
    );
  } else if (hueco.nivel === "falta_dato") {
    control = <BotonReconocer hueco={hueco} onReconocer={reconocerHueco} />;
  } else if (hueco.nivel === "bloqueante") {
    control = (
      <p className="text-sm text-muted-foreground">
        Este hueco se corrige en los insumos: vuelve a subirlos con el archivo
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
        <CardTitle className="font-mono text-sm tracking-tight text-muted-foreground">
          {hueco.codigo}
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
        {/* DIC-08 muestra `hueco.mensaje` dentro de su propio control (la
            frase cruda que no se pudo interpretar es el punto de partida del
            constructor de reglas) -- repetirlo aqui arriba lo duplicaria en
            pantalla. Ver ControlVisibilidad.test.tsx, que exige el mensaje
            visible en su render aislado. */}
        {hueco.codigo !== "DIC-08" ? (
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
