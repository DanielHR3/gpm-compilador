import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import MigasDePan from "./MigasDePan";

it("pinta los tramos, enlaza solo los que tienen href y marca el actual", () => {
  render(<MigasDePan tramos={[{ etiqueta: "Inicio", href: "/" }, { etiqueta: "Solo AS-IS" },
    { etiqueta: "Diccionario (1 de 2)" }]} />);
  const nav = screen.getByRole("navigation", { name: /migas de pan/i });
  expect(nav).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/");
  expect(screen.queryByRole("link", { name: "Solo AS-IS" })).not.toBeInTheDocument();
  expect(screen.getByText("Diccionario (1 de 2)")).toHaveAttribute("aria-current", "page");
});
