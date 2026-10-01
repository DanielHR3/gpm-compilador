import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import ControlSiNo from "./ControlSiNo";

const hueco = {
  nivel: "por_confirmar" as const,
  codigo: "META-07",
  ubicacion: "metadatos",
  mensaje:
    "el tramite saldra oculto del portal del ciudadano: nada en el expediente dice si es publico",
  propuesta: "Sí: lo inicia el ciudadano",
};

it("ofrece las dos decisiones con lo que pasa en cada una", async () => {
  const onConfirmar = vi.fn();
  render(<ControlSiNo hueco={hueco} onConfirmar={onConfirmar} onDejar={vi.fn()} />);

  await userEvent.click(screen.getByRole("button", { name: /sí, que aparezca en el portal/i }));
  expect(onConfirmar).toHaveBeenLastCalledWith("si");

  await userEvent.click(screen.getByRole("button", { name: /no, que quede oculto/i }));
  expect(onConfirmar).toHaveBeenLastCalledWith("no");
});

it("se puede dejar como está sin decidir", async () => {
  const onDejar = vi.fn();
  render(<ControlSiNo hueco={hueco} onConfirmar={vi.fn()} onDejar={onDejar} />);

  await userEvent.click(screen.getByRole("button", { name: /dejarlo así/i }));
  expect(onDejar).toHaveBeenCalled();
});

it("mientras guarda no admite otro clic", () => {
  render(<ControlSiNo hueco={hueco} onConfirmar={vi.fn()} onDejar={vi.fn()} guardando />);
  for (const b of screen.getAllByRole("button")) expect(b).toBeDisabled();
});
