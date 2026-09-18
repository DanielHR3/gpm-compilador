import { useId, useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "cn";
import { clasificarCandidatos, type Objetivo } from "../candidatos";
import type { CampoManifiesto, Clausula, Condicion } from "@/lib/types";

/**
 * Clases nativas de `<select>`, calcadas de `components/ui/input.tsx` (mismos
 * tokens de color/borde/foco) porque las pruebas exigen un `<select>` real
 * (`tagName === "SELECT"` + `userEvent.selectOptions`), y el `Select` de
 * `components/ui/*` (base-ui) renderiza un `<button>`, no un elemento nativo.
 */
const claseSelect =
  "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30";

/**
 * Una fila del constructor: un campo, un operador y el valor a comparar.
 *
 * En pantalla no lleva etiquetas: la fila se lee como frase («Procedencia sea
 * igual a Dependencia»). El nombre accesible va en `aria-label` de cada
 * control, que ademas los distingue entre filas para un lector de pantalla.
 */
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
/** Casa «tramite» con «Trámite»: quien busca no escribe los acentos. */
function llanoBusca(etiqueta: string, busqueda: string): boolean {
  const llano = (s: string) =>
    s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  return llano(etiqueta).includes(llano(busqueda.trim()));
}

export default function ConstructorRegla({
  campos,
  objetivo = null,
  frase = "",
  value,
  onChange,
  marcadorValor = "este valor",
}: {
  campos: CampoManifiesto[];
  /** El campo cuya visibilidad se define. `null`/omitido en la compuerta, donde
      la regla de «se captura después» no aplica igual. */
  objetivo?: Objetivo | null;
  /** La frase que escribió Simplificación, para sugerir lo que ella nombra. */
  frase?: string;
  value: Condicion | null;
  onChange: (c: Condicion) => void;
  /** Ejemplo dentro de la caja de valor: una caja vacia no ensena nada. */
  marcadorValor?: string;
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

  // Un buscador por fila. Con pocos campos estorba mas de lo que ayuda; con 41
  // —el expediente de Reposicion— el desplegable es inservible sin el.
  const [busqueda, setBusqueda] = useState<Record<number, string>>({});
  const HAY_MUCHOS = campos.length > 8;
  const candidatos = clasificarCandidatos(campos, objetivo, frase);
  const GRUPOS = [
    ["sugerido", "Sugeridos — los menciona el Diccionario"],
    ["usable", "También puedes usar"],
    ["inservible", "No se pueden usar aquí"],
  ] as const;

  return (
    <div className="flex flex-col rounded-lg border border-border bg-muted/30 p-3">
      {filas.map((fila, i) => {
        const n = i + 1;
        const campoId = `${idBase}-campo-${i}`;
        const operadorId = `${idBase}-operador-${i}`;
        const valorId = `${idBase}-valor-${i}`;
        const campoElegido = campos.find((c) => c.nombre === fila.campo);
        const tieneCatalogo = !!campoElegido && campoElegido.catalogo.length > 0;

        return (
          <div key={i}>
            {i > 0 ? (
              <div className="flex items-center gap-2 py-1.5 text-xs font-medium text-muted-foreground">
                <span className="h-px flex-1 bg-border" />y además<span className="h-px flex-1 bg-border" />
              </div>
            ) : null}
            <div className="flex flex-wrap items-end gap-2 rounded-md bg-card p-2.5 ring-1 ring-foreground/5">
              <div className="flex min-w-32 flex-1 flex-col gap-1">
                {HAY_MUCHOS ? (
                  <Input
                    aria-label={`Buscar campo de la condición ${n}`}
                    placeholder="Escribe para buscar…"
                    value={busqueda[i] ?? ""}
                    onChange={(e) => setBusqueda({ ...busqueda, [i]: e.target.value })}
                    className="h-8 text-xs"
                  />
                ) : null}
                <select
                  id={campoId}
                  aria-label={`Campo de la condición ${n}`}
                  className={claseSelect}
                  value={fila.campo}
                  onChange={(e) =>
                    actualizarFila(i, { campo: e.target.value, igual: "" })
                  }
                >
                  <option value="">Elige un campo</option>
                  {GRUPOS.map(([grupo, titulo]) => {
                    const visibles = candidatos.filter(
                      (c) =>
                        c.grupo === grupo &&
                        llanoBusca(c.campo.etiqueta, busqueda[i] ?? ""),
                    );
                    if (!visibles.length) return null;
                    return (
                      <optgroup key={grupo} label={titulo}>
                        {visibles.map(({ campo: c, motivo }) => (
                          <option key={c.nombre} value={c.nombre} disabled={!!motivo}>
                            {motivo ? `${c.etiqueta} — ${motivo}` : c.etiqueta}
                          </option>
                        ))}
                      </optgroup>
                    );
                  })}
                </select>
              </div>

              <div className="flex w-36 flex-col gap-1">
                <select
                  id={operadorId}
                  aria-label={`Comparación de la condición ${n}`}
                  className={claseSelect}
                  value={fila.operador}
                  onChange={(e) =>
                    actualizarFila(i, {
                      operador: e.target.value as "==" | "!=",
                    })
                  }
                >
                  {/* Se leen pegados al campo que va antes: «… «Estatus del
                      Tramite» sea «Pendiente»», no «es igual a». */}
                  <option value="==">sea</option>
                  <option value="!=">no sea</option>
                </select>
              </div>

              <div className="flex min-w-32 flex-1 flex-col gap-1">
                {tieneCatalogo ? (
                  <select
                    id={valorId}
                    aria-label={`Valor de la condición ${n}`}
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
                    aria-label={`Valor de la condición ${n}`}
                    placeholder={marcadorValor}
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
                  aria-label={`Quitar la condición ${n}`}
                  onClick={() => quitarFila(i)}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <X aria-hidden className="size-4" />
                </Button>
              ) : null}
            </div>
          </div>
        );
      })}

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={anadirFila}
        className={cn("mt-2 self-start", filas.length > 0 && "border-primary/30 text-primary")}
      >
        <Plus aria-hidden className="size-3.5" />
        y además debe cumplirse que…
      </Button>
    </div>
  );
}
