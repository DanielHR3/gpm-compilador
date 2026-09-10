import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  camposDelManifiesto: () => [
    { nombre: "estado", etiqueta: "Estado", catalogo: [] },
  ],
}));

import ControlVisibilidad from "./ControlVisibilidad";

it("muestra la frase cruda y al guardar llama resolverDic08", async () => {
  const { resolverDic08 } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(
    <ControlVisibilidad
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::domicilio",
        mensaje: "no se pudo interpretar: «visible si es de otro estado»",
        propuesta: null,
      }}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={onResuelto}
    />,
  );
  expect(screen.getByText(/otro estado/)).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText(/campo 1/i), "estado");
  await userEvent.type(screen.getByLabelText(/valor 1/i), "hidalgo");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolverDic08).toHaveBeenCalledWith(
    "a".repeat(16),
    "p1::domicilio",
    expect.objectContaining({ campo: "estado", igual: "hidalgo" }),
  );
  expect(onResuelto).toHaveBeenCalled();
});
