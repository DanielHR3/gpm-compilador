import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CampoManifiesto, Clausula, Condicion } from "@/lib/types";

/**
 * Clases nativas de `<select>`, calcadas de `components/ui/input.tsx` (mismos
 * tokens de color/borde/foco) porque las pruebas exigen un `<select>` real
 * (`tagName === "SELECT"` + `userEvent.selectOptions`), y el `Select` de
 * `components/ui/*` (base-ui) renderiza un `<button>`, no un elemento nativo.
 */
const claseSelect =
  "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30";

/** Una fila del constructor: un campo, un operador y el valor a comparar. */
type Fila = { campo: string; operador: "==" | "!="; igual: string };

const filaVacia: Fila = { campo: "", operador: "==", igual: "" };

/** Convierte una `Clausula` (o su ausencia) en la forma de fila local. */
function filaDeClausula(c: Clausula): Fila {
  return { campo: c.campo, operador: c.operador, igual: c.igual };
}

/** Siembra el estado local de filas a partir de una `Condicion` (o ninguna). */
function filasIniciales(value: Condicion | null): Fila[] {
  if (!value) return [{ ...filaVacia }];
  return [filaDeClausula(value), ...value.y.map(filaDeClausula)];
}

/** Una fila cuenta como "completa" cuando tiene campo y valor. */
function esCompleta(f: Fila): boolean {
  return f.campo !== "" && f.igual !== "";
}

/**
 * Constructor visual de una `Condicion` con clausulas "Y" (Task 11 de SP2):
 * N filas `campo operador valor`, cada una editable con `Select`/`Input`
 * nativos, unidas por "Y". Solo las filas completas (campo + valor no vacios)
 * viajan a `onChange`; si ninguna fila esta completa no se notifica, igual
 * que el resto de controles de `huecos/controles` que solo confirman con
 * datos validos.
 */
export default function ConstructorRegla({
  campos,
  value,
  onChange,
}: {
  campos: CampoManifiesto[];
  value: Condicion | null;
  onChange: (c: Condicion) => void;
}) {
  const [filas, setFilas] = useState<Fila[]>(() => filasIniciales(value));
  const idBase = useId();

  const notificar = (siguientes: Fila[]) => {
    const completas = siguientes.filter(esCompleta);
    if (completas.length === 0) return;
    const [primera, ...resto] = completas;
    onChange({
      campo: primera.campo,
      operador: primera.operador,
      igual: primera.igual,
      y: resto.map((f) => ({
        campo: f.campo,
        operador: f.operador,
        igual: f.igual,
      })),
    });
  };

  const actualizarFila = (indice: number, cambios: Partial<Fila>) => {
    const siguientes = filas.map((f, i) =>
      i === indice ? { ...f, ...cambios } : f
    );
    setFilas(siguientes);
    notificar(siguientes);
  };

  const anadirFila = () => {
    setFilas([...filas, { ...filaVacia }]);
  };

  const quitarFila = (indice: number) => {
    const siguientes = filas.filter((_, i) => i !== indice);
    setFilas(siguientes);
    notificar(siguientes);
  };

  return (
    <div className="flex flex-col gap-3">
      {filas.map((fila, i) => {
        const n = i + 1;
        const campoId = `${idBase}-campo-${i}`;
        const operadorId = `${idBase}-operador-${i}`;
        const valorId = `${idBase}-valor-${i}`;
        const campoElegido = campos.find((c) => c.nombre === fila.campo);
        const tieneCatalogo = !!campoElegido && campoElegido.catalogo.length > 0;

        return (
          <div key={i} className="flex flex-wrap items-end gap-2">
            <div className="flex flex-col gap-1">
              <label htmlFor={campoId} className="text-sm font-medium">
                Campo {n}
              </label>
              <select
                id={campoId}
                className={claseSelect}
                value={fila.campo}
                onChange={(e) =>
                  actualizarFila(i, { campo: e.target.value, igual: "" })
                }
              >
                <option value="">Elige un campo</option>
                {campos.map((c) => (
                  <option key={c.nombre} value={c.nombre}>
                    {c.etiqueta}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor={operadorId} className="text-sm font-medium">
                Operador {n}
              </label>
              <select
                id={operadorId}
                className={claseSelect}
                value={fila.operador}
                onChange={(e) =>
                  actualizarFila(i, {
                    operador: e.target.value as "==" | "!=",
                  })
                }
              >
                <option value="==">==</option>
                <option value="!=">!=</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor={valorId} className="text-sm font-medium">
                Valor {n}
              </label>
              {tieneCatalogo ? (
                <select
                  id={valorId}
                  className={claseSelect}
                  value={fila.igual}
                  onChange={(e) => actualizarFila(i, { igual: e.target.value })}
                >
                  <option value="">Elige un valor</option>
                  {campoElegido!.catalogo.map((opcion) => (
                    <option key={opcion.valor} value={opcion.valor}>
                      {opcion.etiqueta}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  id={valorId}
                  value={fila.igual}
                  onChange={(e) => actualizarFila(i, { igual: e.target.value })}
                />
              )}
            </div>

            {i > 0 ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Quitar fila ${n}`}
                onClick={() => quitarFila(i)}
              >
                ×
              </Button>
            ) : null}
          </div>
        );
      })}

      <Button type="button" variant="outline" onClick={anadirFila}>
        Añadir Y
      </Button>
    </div>
  );
}
