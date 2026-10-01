import { useEffect, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { leerGrupos } from "@/lib/api";
import type { Hueco } from "@/lib/types";

import { pistaDeCodigo } from "../lenguaje";

import BotonGuardar from "./BotonGuardar";
import DetalleTecnico from "./DetalleTecnico";

/** Minusculas, digitos y guion bajo: la forma de casi todos los grupos. */
const PARECE_IDENTIFICADOR = /^[a-z0-9_]+$/;

/**
 * Control para `ACT-01`: el grupo de usuarios de la plataforma al que
 * corresponde un responsable del trámite.
 *
 * El catálogo de grupos vive en la plataforma y aquí no se conoce, así que es
 * texto libre con sugerencias de los ya vistos (`GET /api/v1/grupos`). La
 * forma NO se impone: un trámite real usa `grupo práctica`, con espacio y
 * acento. Si lo escrito no parece un identificador se avisa —lo usual es que
 * alguien haya escrito el nombre del área— y se deja guardar igual.
 */
export default function ControlGrupo({
  hueco,
  onConfirmar,
  onDejar,
  guardando = false,
}: {
  hueco: Hueco;
  onConfirmar: (grupo: string) => void | Promise<void>;
  onDejar: () => void | Promise<void>;
  /** Lo controla `TarjetaHueco` via `useAccion`: cierra la puerta al doble envio. */
  guardando?: boolean;
}) {
  const [valor, setValor] = useState<string>("");
  const [sugerencias, setSugerencias] = useState<string[]>([]);
  const id = useId();
  const idLista = useId();
  const pista = pistaDeCodigo(hueco.codigo);
  const limpio = valor.trim();

  useEffect(() => {
    let vivo = true;
    // Las sugerencias son ayuda: si no llegan, la caja sirve igual.
    leerGrupos()
      .then((g) => {
        if (vivo) setSugerencias(g);
      })
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        Grupo de usuarios en la plataforma
      </label>
      {pista ? (
        <p className="text-sm text-muted-foreground">{pista.instruccion}</p>
      ) : null}
      <Input
        id={id}
        list={idLista}
        placeholder={pista?.marcador}
        value={valor}
        onChange={(e) => setValor(e.target.value)}
      />
      <datalist id={idLista}>
        {sugerencias.map((g) => (
          <option key={g} value={g} />
        ))}
      </datalist>
      {limpio && !PARECE_IDENTIFICADOR.test(limpio) ? (
        <p className="text-sm text-amber-700">
          «{limpio}» no parece un identificador de grupo: suelen ir en
          minúsculas y con guion bajo, como «verificacion_vehicular». Si así
          se llama en la plataforma, guárdalo tal cual.
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <BotonGuardar
          guardando={guardando}
          disabled={!limpio}
          onClick={() => onConfirmar(limpio)}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={guardando}
          onClick={() => onDejar()}
        >
          Dejarlo así
        </Button>
      </div>

      <DetalleTecnico
        codigo={hueco.codigo}
        ubicacion={hueco.ubicacion}
        crudo={hueco.mensaje}
      />
    </div>
  );
}
