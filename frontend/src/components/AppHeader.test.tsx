import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import AppHeader from "./AppHeader";

it("muestra el título de la pantalla y el logo institucional", () => {
  render(<AppHeader titulo="Carga de insumos" />);
  expect(screen.getByText("Carga de insumos")).toBeInTheDocument();
  // El logo sustituye al texto "Gobierno del Estado de Hidalgo": dice lo mismo,
  // y sobre la barra blanca puede ir en sus colores institucionales.
  const logo = screen.getByRole("img", { name: /hidalgo/i });
  expect(logo).toHaveAttribute("src", expect.stringContaining("logo"));
  expect(screen.queryByText("Gobierno del Estado de Hidalgo")).not.toBeInTheDocument();
});

it("con un expediente abierto lleva el menú «Entrega»; sin él, no", () => {
  const { rerender } = render(
    <AppHeader titulo="Revisión del expediente" entrega={{ sid: "a".repeat(16), puerta: { desbloqueado: true, bloqueantes: [] } }} />,
  );
  expect(screen.getByRole("button", { name: /entrega.*listo/i })).toBeInTheDocument();

  rerender(<AppHeader titulo="Catálogos" />);
  expect(screen.queryByRole("button", { name: /entrega/i })).not.toBeInTheDocument();
});
