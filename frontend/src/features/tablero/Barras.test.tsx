import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import Barras from "./Barras";

it("pinta una barra por fila con nombre, cuenta y porcentaje, sin tabla", () => {
  render(
    <Barras
      filas={[
        { nombre: "Identificación oficial", tramites: 5, porcentaje: 83 },
        { nombre: "Tarjeta de circulación", tramites: 2, porcentaje: 33 },
      ]}
      total={6}
    />,
  );
  const fila = screen.getByRole("listitem", { name: /identificación oficial/i });
  expect(fila).toHaveTextContent("5 de 6");
  expect(fila).toHaveTextContent("83%");
  const barra = screen.getByRole("meter", { name: /identificación oficial/i });
  expect(barra).toHaveAttribute("aria-valuenow", "83");
  expect(screen.queryByRole("table")).toBeNull();
});

it("sin filas dice que no hay nada que contar", () => {
  render(<Barras filas={[]} total={0} />);
  expect(screen.getByText(/nada que contar todavía/i)).toBeInTheDocument();
});
