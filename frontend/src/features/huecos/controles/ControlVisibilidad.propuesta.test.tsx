import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  camposDelManifiesto: () => [
    {
      nombre: "es_moral",
      etiqueta: "¿Persona moral?",
      tipo: "radio",
      catalogo: [{ etiqueta: "Sí", valor: "si" }, { etiqueta: "No", valor: "no" }],
    },
  ],
  ErrorApi: class ErrorApi extends Error {},
}));

import ControlVisibilidad from "./ControlVisibilidad";

const huecoIA = {
  nivel: "falta_dato",
  codigo: "DIC-08",
  ubicacion: "p1::rfc",
  mensaje:
    "la condición de visibilidad de 'RFC' (rfc) no se pudo interpretar: «Solo si es moral»; configúrala a mano",
  propuesta: null,
};
const propuestaIA = {
  id: "p1",
  ubicacion: "p1::rfc",
  condicion: { campo: "es_moral", igual: "si", operador: "==" as const, y: [] },
  motivo_modelo: null,
  confianza: "alta" as const,
  cita: {
    fuente: "Diccionario de Datos" as const,
    pantalla: "p1",
    pantalla_nombre: "Datos",
    campo: "rfc",
    texto: "Solo si es moral",
  },
  veredicto: "aceptable",
  decision: null,
  condicion_final: null,
  creada: "2026-09-17T00:00:00Z",
  decidida: null,
};
const sid = "a".repeat(16);

it("con propuesta: muestra la cita y las tres acciones; sin propuesta: como hoy", () => {
  const { unmount } = render(
    <ControlVisibilidad
      hueco={huecoIA}
      sid={sid}
      manifiesto={{}}
      onResuelto={vi.fn()}
      propuesta={propuestaIA}
      onDecision={vi.fn()}
    />,
  );
  expect(screen.getByText(/Propuesto a partir de/)).toBeInTheDocument();
  // La frase se lee arriba (lo que hay que traducir) y queda en el mensaje del
  // compilador, plegado. La cita NO la repite: aporta de donde salio.
  expect(screen.getAllByText(/«Solo si es moral»/)).toHaveLength(2);
  expect(screen.getByText(/Propuesto a partir de/).parentElement).toHaveTextContent(
    /Diccionario/,
  );
  expect(screen.getByRole("button", { name: /aceptar/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /corregir/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /descartar/i })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /guardar/i })).not.toBeInTheDocument();

  // Una instancia NUEVA sin propuesta: el estado de la anterior no cuenta.
  unmount();
  render(<ControlVisibilidad hueco={huecoIA} sid={sid} manifiesto={{}} onResuelto={vi.fn()} />);
  expect(screen.queryByText(/Propuesto a partir de/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /guardar/i })).toBeInTheDocument();
});

it("aceptar resuelve con la condición propuesta y luego anota la decisión", async () => {
  const { resolverDic08 } = await import("@/lib/api");
  vi.mocked(resolverDic08).mockClear();
  const onDecision = vi.fn().mockResolvedValue(undefined);
  const onResuelto = vi.fn();
  render(
    <ControlVisibilidad
      hueco={huecoIA}
      sid={sid}
      manifiesto={{}}
      onResuelto={onResuelto}
      propuesta={propuestaIA}
      onDecision={onDecision}
    />,
  );
  await userEvent.click(screen.getByRole("button", { name: /aceptar/i }));
  expect(resolverDic08).toHaveBeenCalledWith(sid, "p1::rfc", propuestaIA.condicion);
  expect(onDecision).toHaveBeenCalledWith("aceptada", undefined);
  expect(onResuelto).toHaveBeenCalled();
  // orden: primero la escritura, después el registro
  expect(vi.mocked(resolverDic08).mock.invocationCallOrder[0]).toBeLessThan(
    onDecision.mock.invocationCallOrder[0],
  );
});

it("descartar anota y vuelve al modo manual sin resolver", async () => {
  const { resolverDic08 } = await import("@/lib/api");
  vi.mocked(resolverDic08).mockClear();
  const onDecision = vi.fn().mockResolvedValue(undefined);
  render(
    <ControlVisibilidad
      hueco={huecoIA}
      sid={sid}
      manifiesto={{}}
      onResuelto={vi.fn()}
      propuesta={propuestaIA}
      onDecision={onDecision}
    />,
  );
  await userEvent.click(screen.getByRole("button", { name: /descartar/i }));
  expect(onDecision).toHaveBeenCalledWith("descartada", undefined);
  expect(resolverDic08).not.toHaveBeenCalled();
  expect(screen.queryByText(/Propuesto a partir de/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /guardar/i })).toBeInTheDocument();
});
