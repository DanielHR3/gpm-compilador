import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

const respConHueco = {
  manifiesto: {},
  huecos: [
    {
      nivel: "falta_dato",
      codigo: "MMD-04",
      ubicacion: "g1",
      mensaje: "x",
      propuesta: null,
    },
  ],
};
const respSinHueco = { manifiesto: {}, huecos: [] };

vi.mock("@/lib/api", () => ({
  resolverCompuertaCampo: vi.fn(),
  resolverCompuertaRamas: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  leerCompuerta: vi.fn().mockResolvedValue({
    predecesora: "t1",
    ramas: [
      { a: "t2", a_nombre: "Aprobar", etiqueta: "procede" },
      { a: "t3", a_nombre: "Rechazar", etiqueta: "no procede" },
    ],
  }),
  camposDelManifiesto: () => [
    { nombre: "procede", etiqueta: "Procede", catalogo: [] },
  ],
}));

import ControlCompuerta from "./ControlCompuerta";

it("fase 1: elegir campo llama resolverCompuertaCampo; si basta, sube el estado", async () => {
  const { resolverCompuertaCampo } = await import("@/lib/api");
  (resolverCompuertaCampo as any).mockResolvedValue(respSinHueco);
  const onResuelto = vi.fn();
  render(
    <ControlCompuerta
      hueco={respConHueco.huecos[0]}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={onResuelto}
    />,
  );
  await userEvent.selectOptions(
    screen.getByLabelText(/campo de la compuerta/i),
    "procede",
  );
  await userEvent.click(
    screen.getByRole("button", { name: /usar este campo/i }),
  );
  expect(resolverCompuertaCampo).toHaveBeenCalledWith(
    "a".repeat(16),
    "g1",
    "procede",
  );
  expect(onResuelto).toHaveBeenCalledWith(respSinHueco);
});

it("fase 2: si el campo no basta, aparece el constructor por rama", async () => {
  const { resolverCompuertaCampo, leerCompuerta, resolverCompuertaRamas } =
    await import("@/lib/api");
  (resolverCompuertaCampo as any).mockResolvedValue(respConHueco); // sigue el MMD-04
  render(
    <ControlCompuerta
      hueco={respConHueco.huecos[0]}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
    />,
  );
  await userEvent.selectOptions(
    screen.getByLabelText(/campo de la compuerta/i),
    "procede",
  );
  await userEvent.click(
    screen.getByRole("button", { name: /usar este campo/i }),
  );
  expect(await screen.findByText(/no resolvieron solas/i)).toBeInTheDocument();
  expect(leerCompuerta).toHaveBeenCalled();
  // una fila de constructor por rama (Aprobar / Rechazar)
  expect(await screen.findByText(/Aprobar/)).toBeInTheDocument();
  await userEvent.selectOptions(
    screen.getAllByLabelText(/campo 1/i)[0],
    "procede",
  );
  await userEvent.type(screen.getAllByLabelText(/valor 1/i)[0], "si");
  await userEvent.selectOptions(
    screen.getAllByLabelText(/campo 1/i)[1],
    "procede",
  );
  await userEvent.type(screen.getAllByLabelText(/valor 1/i)[1], "no");
  await userEvent.click(
    screen.getByRole("button", { name: /guardar ramas/i }),
  );
  expect(resolverCompuertaRamas).toHaveBeenCalledWith(
    "a".repeat(16),
    "g1",
    expect.arrayContaining([expect.objectContaining({ a: "t2" })]),
  );
});
