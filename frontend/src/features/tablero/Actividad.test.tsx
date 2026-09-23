import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import Actividad from "./Actividad";

const SEMANAS = Array.from({ length: 12 }, (_, i) => ({
  semana: `2026-W${28 + i}`,
  tramites: i === 10 ? 2 : i === 11 ? 3 : 0,
}));

it("una columna por semana con su valor accesible, eje con semanas y total reciente", () => {
  render(<Actividad semanas={SEMANAS} />);
  const grafica = screen.getByRole("img", { name: /trámites por semana/i });
  expect(grafica).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: /2026-W39: 3/ })).toBeInTheDocument();
  // El eje se lee: etiqueta corta en el SVG (el tooltip <title> lleva la larga).
  expect(within(grafica).getAllByText(/^W28$/)).toHaveLength(1);
  expect(within(grafica).getAllByText(/^W39$/)).toHaveLength(1);
  expect(screen.getByText(/5 en las últimas 4 semanas/i)).toBeInTheDocument();
});
