import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import PieInstitucional from "./PieInstitucional";

it("la greca es decorativa: no la anuncia un lector de pantalla", () => {
  const { container } = render(<PieInstitucional />);
  const pie = container.querySelector("[data-slot='greca']");
  expect(pie).toBeInTheDocument();
  // Sin texto alternativo y oculta al árbol de accesibilidad: no dice nada que
  // no esté ya dicho, y leerla sería ruido.
  expect(pie).toHaveAttribute("aria-hidden", "true");
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
