import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import ControlActor from "./ControlActor";

const actores = [
  { id: "usuario", nombre: "Usuario" },
  { id: "po", nombre: "Periódico Oficial" },
];

const hueco = {
  nivel: "falta_dato" as const,
  codigo: "MMD-03",
  ubicacion: "A",
  mensaje:
    "la tarea «🔍 Usuario: Consultar información del trámite (requisitos, tarifas)» no declara carril (:::clase); el actor queda sin asignar",
  propuesta: null,
};

it("pregunta quien hace la tarea, con el nombre limpio de la tarea", () => {
  render(<ControlActor hueco={hueco} actores={actores} onConfirmar={vi.fn()} />);

  expect(
    screen.getByRole("heading", {
      name: "¿Quién hace «Consultar información del trámite»?",
    }),
  ).toBeInTheDocument();
});

it("explica que hacer, sin jerga de diagramas", () => {
  render(<ControlActor hueco={hueco} actores={actores} onConfirmar={vi.fn()} />);

  expect(
    screen.getByText(/Elige quién realiza esta tarea dentro del trámite/i),
  ).toBeInTheDocument();
});

it("el desplegable se llama por lo que hace, no con el mensaje crudo", () => {
  render(<ControlActor hueco={hueco} actores={actores} onConfirmar={vi.fn()} />);

  const combo = screen.getByRole("combobox", { name: /responsable de la tarea/i });
  expect(combo).toBeInTheDocument();
  expect(combo).not.toHaveAccessibleName(/:::clase/);
});

it("lo tecnico queda plegado pero presente", () => {
  render(<ControlActor hueco={hueco} actores={actores} onConfirmar={vi.fn()} />);

  const detalle = screen.getByText(/ver detalle técnico/i).closest("details");
  expect(detalle).not.toHaveAttribute("open");
  expect(detalle).toHaveTextContent("MMD-03");
  expect(detalle).toHaveTextContent(":::clase");
});

it("propone el actor que se eligio la vez anterior, para no repetir el mismo clic 42 veces", () => {
  render(
    <ControlActor
      hueco={hueco}
      actores={actores}
      onConfirmar={vi.fn()}
      valorInicial="po"
    />,
  );

  expect(
    screen.getByRole("combobox", { name: /responsable de la tarea/i }),
  ).toHaveTextContent("Periódico Oficial");
  // Y "Guardar" ya está activo: un solo clic cierra el hueco.
  expect(screen.getByRole("button", { name: /guardar/i })).toBeEnabled();
});

it("sin eleccion previa no propone nada", () => {
  render(<ControlActor hueco={hueco} actores={actores} onConfirmar={vi.fn()} />);

  expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled();
});
