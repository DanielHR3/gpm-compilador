import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import Indicadores from "./Indicadores";

it("una tarjeta de cifra grande por indicador, con su etiqueta", () => {
  render(
    <Indicadores
      cifras={[
        { etiqueta: "Trámites", valor: 6 },
        { etiqueta: "Campos por trámite", valor: 23.5, nota: "promedio" },
      ]}
    />,
  );
  const t = screen.getByRole("article", { name: /trámites/i });
  expect(t).toHaveTextContent("6");
  const c = screen.getByRole("article", { name: /campos por trámite/i });
  expect(c).toHaveTextContent("23.5");
  expect(c).toHaveTextContent(/promedio/);
  expect(screen.queryByRole("table")).toBeNull();
});
