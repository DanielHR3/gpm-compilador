import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { reconocer, resolver } from "@/lib/api";
import type { Hueco, Resolucion } from "@/lib/types";

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
  onResuelto: (nuevo: RespuestaResuelto) => void;
}) {
  const resolverCon = async (tipo: Resolucion["tipo"], valor: string) => {
    const resp = await resolver(sid, [
      { tipo, ubicacion: hueco.ubicacion, valor },
    ]);
    onResuelto(resp);
  };

  const reconocerHueco = async () => {
    const resp = await reconocer(sid, hueco.codigo, hueco.ubicacion);
    onResuelto(resp);
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
          onResuelto={onResuelto}
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
          onResuelto={onResuelto}
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
    <Card>
      <CardHeader>
        <CardTitle>{hueco.codigo}</CardTitle>
        <CardDescription>{hueco.nivel}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p>{hueco.mensaje}</p>
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
