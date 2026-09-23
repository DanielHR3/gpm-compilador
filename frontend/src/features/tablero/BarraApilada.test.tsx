import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import BarraApilada from "./BarraApilada";

it("un segmento por nivel con etiqueta directa y leyenda; los ceros no ocupan sitio", () => {
  render(
    <BarraApilada
      titulo="Nivel de complejidad"
      segmentos={[
        { nombre: "Alto", valor: 1 },
        { nombre: "Medio", valor: 0 },
        { nombre: "Bajo", valor: 3 },
      ]}
    />,
  );
  const barra = screen.getByRole("img", { name: /nivel de complejidad/i });
  expect(barra).toHaveTextContent(/Alto/);
  expect(barra).toHaveTextContent(/Bajo/);
  expect(screen.getByRole("listitem", { name: /Alto: 1 \(25%\)/ })).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: /Medio: 0 \(0%\)/ })).toBeInTheDocument();
});

it("sin datos no pinta una barra vacía", () => {
  render(<BarraApilada titulo="X" segmentos={[{ nombre: "Alto", valor: 0 }]} />);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText(/nada que contar todavía/i)).toBeInTheDocument();
});
