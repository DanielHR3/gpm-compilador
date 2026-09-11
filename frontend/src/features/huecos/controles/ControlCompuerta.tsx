import { useId, useState } from "react";
import { ArrowRight, Check, GitBranch } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  camposDelManifiesto,
  ErrorApi,
  leerCompuerta,
  resolverCompuertaCampo,
  resolverCompuertaRamas,
} from "@/lib/api";
import { cn } from "cn";
import type { Condicion, EstructuraCompuerta, Hueco } from "@/lib/types";

import ConstructorRegla from "./ConstructorRegla";

/**
 * Clases nativas de `<select>`, calcadas de `ConstructorRegla`/`input.tsx`
 * (mismos tokens de color/borde/foco). Sigue siendo la 2ª ocurrencia real de
 * este bloque (la 1ª es `ConstructorRegla`): `ControlVisibilidad` no define
 * su propio `<select>`, solo compone `ConstructorRegla` + `Button`, así que
 * no cuenta. Por el umbral que dejó el review de Task 11 ("si se copia una
 * 3ª vez, extraer a un export compartido"), 2 ocurrencias no lo cruzan
 * todavía — se mantiene la copia local aquí. Si aparece una 3ª, ese es el
 * momento de extraerlo (p.ej. a un `components/ui/native-select.ts` o
 * similar).
 */
const claseSelect =
  "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30";

/**
 * Control para `MMD-04` (compuerta sin `@@campo`), en 2 fases (Task 13 de
 * SP2):
 *
 * Fase 1: elegir el campo del manifiesto que decide la compuerta y mandarlo
 * con `resolverCompuertaCampo`. Si el backend logra reensamblar el flujo
 * entero con ese campo, el hueco `MMD-04` desaparece de la respuesta y el
 * control termina ahí (`onResuelto` directo).
 *
 * Fase 2: si el campo solo no bastó (el `MMD-04` de esta `ubicacion` sigue
 * en la respuesta — p.ej. las etiquetas de las ramas no calzan con ningún
 * valor de catálogo), se lee la estructura de la compuerta
 * (`leerCompuerta`) y se muestra un `ConstructorRegla` por cada rama para
 * armar la condición a mano; `resolverCompuertaRamas` cierra el hueco.
 */
export default function ControlCompuerta({
  hueco,
  sid,
  manifiesto,
  onResuelto,
}: {
  hueco: Hueco;
  sid: string;
  manifiesto: Record<string, unknown>;
  onResuelto: (resp: { manifiesto: Record<string, unknown>; huecos: Hueco[] }) => void;
}) {
  const [fase, setFase] = useState<1 | 2>(1);
  const [campoElegido, setCampoElegido] = useState("");
  const [estructura, setEstructura] = useState<EstructuraCompuerta | null>(null);
  const [condPorRama, setCondPorRama] = useState<Record<string, Condicion>>({});
  const [error, setError] = useState<ErrorApi | null>(null);
  const [guardando, setGuardando] = useState(false);
  const campoSelectId = useId();

  const campos = camposDelManifiesto(manifiesto);

  const usarEsteCampo = async () => {
    if (!campoElegido) return;
    setError(null);
    setGuardando(true);
    try {
      const resp = await resolverCompuertaCampo(
        sid,
        hueco.ubicacion,
        campoElegido,
      );
      const sigueElHueco = resp.huecos.some(
        (h) => h.codigo === "MMD-04" && h.ubicacion === hueco.ubicacion,
      );
      if (sigueElHueco) {
        const est = await leerCompuerta(sid, hueco.ubicacion);
        setEstructura(est);
        setFase(2);
      } else {
        onResuelto(resp);
      }
    } catch (e) {
      if (e instanceof ErrorApi) {
        setError(e);
      } else {
        throw e;
      }
    } finally {
      setGuardando(false);
    }
  };

  const guardarRamas = async () => {
    if (!estructura) return;
    setError(null);
    setGuardando(true);
    try {
      const resp = await resolverCompuertaRamas(
        sid,
        hueco.ubicacion,
        estructura.ramas.map((r) => ({ a: r.a, condicion: condPorRama[r.a] })),
      );
      onResuelto(resp);
    } catch (e) {
      if (e instanceof ErrorApi) {
        setError(e);
      } else {
        throw e;
      }
    } finally {
      setGuardando(false);
    }
  };

  const todasLasRamasListas =
    !!estructura &&
    estructura.ramas.every((r) => !!condPorRama[r.a]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span
          className={cn(
            "flex size-5 items-center justify-center rounded-full font-semibold",
            "bg-primary text-primary-foreground",
          )}
        >
          1
        </span>
        Elegir campo
        <span className="h-px w-4 bg-border" />
        <span
          className={cn(
            "flex size-5 items-center justify-center rounded-full font-semibold",
            fase === 2
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground",
          )}
        >
          2
        </span>
        Condición por rama
      </div>

      {fase === 1 ? (
        <>
          <div className="flex flex-col gap-1">
            <label htmlFor={campoSelectId} className="text-sm font-medium">
              Campo de la compuerta
            </label>
            <select
              id={campoSelectId}
              className={claseSelect}
              value={campoElegido}
              onChange={(e) => setCampoElegido(e.target.value)}
            >
              <option value="">Elige un campo</option>
              {campos.map((c) => (
                <option key={c.nombre} value={c.nombre}>
                  {c.etiqueta}
                </option>
              ))}
            </select>
          </div>
          <Button
            type="button"
            disabled={!campoElegido || guardando}
            onClick={usarEsteCampo}
            className="self-start"
          >
            Usar este campo
            <ArrowRight aria-hidden className="size-4" />
          </Button>
        </>
      ) : (
        <>
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <GitBranch aria-hidden className="mt-0.5 size-4 shrink-0 text-amber-600" />
            <p>
              El campo elegido y sus etiquetas no resolvieron solas todas las
              ramas: arma la condición de cada una a mano.
            </p>
          </div>
          {estructura?.ramas.map((rama) => (
            <div
              key={rama.a}
              className="flex flex-col gap-2 rounded-lg border border-border p-3"
            >
              <p className="text-sm font-medium">
                <ArrowRight aria-hidden className="mr-1 inline size-3.5 text-primary" />
                {rama.a_nombre}
                <span className="ml-1 font-normal text-muted-foreground">
                  (etiqueta &quot;{rama.etiqueta}&quot;)
                </span>
              </p>
              <ConstructorRegla
                campos={campos}
                value={null}
                onChange={(c) =>
                  setCondPorRama((prev) => ({ ...prev, [rama.a]: c }))
                }
              />
            </div>
          ))}
          <Button
            type="button"
            disabled={!todasLasRamasListas || guardando}
            onClick={guardarRamas}
            className="self-start"
          >
            <Check aria-hidden className="size-4" />
            Guardar ramas
          </Button>
        </>
      )}
      {error ? (
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <p>{error.message}</p>
        </div>
      ) : null}
    </div>
  );
}
