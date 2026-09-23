import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import MapaCalor from "./MapaCalor";

const M = {
  filas: ["Reposición", "Prórroga"],
  columnas: ["DIC-08", "FLU-01"],
  celdas: [[20, 0], [1, 1]],
  maximo: 20,
};

it("pinta una rejilla con una celda por cruce, con su valor accesible y sin tabla", () => {
  render(<MapaCalor titulo="Inconsistencias por trámite" {...M} etiquetaColumna={(c) => c} />);
  const rejilla = screen.getByRole("grid", { name: /inconsistencias por trámite/i });
  const celda = within(rejilla).getByRole("gridcell", { name: /Reposición · DIC-08: 20/ });
  expect(celda).toHaveAttribute("data-paso", "5");
  expect(within(rejilla).getByRole("gridcell", { name: /Reposición · FLU-01: 0/ })).toHaveAttribute("data-paso", "0");
  expect(screen.queryByRole("table")).toBeNull();
});

it("en modo presencia la celda dice sí o no, no un numero", () => {
  render(<MapaCalor titulo="Requisitos" filas={["Acta"]} columnas={["Testamento"]} celdas={[[1]]} modo="presencia" />);
  expect(screen.getByRole("gridcell", { name: /Acta · Testamento: sí/i })).toBeInTheDocument();
});

it("ofrece la misma informacion como lista, para quien no lee color", () => {
  render(<MapaCalor titulo="Inconsistencias por trámite" {...M} />);
  const lista = screen.getByText(/ver como lista/i).closest("details")!;
  expect(within(lista).getByText(/Reposición · DIC-08: 20/)).toBeInTheDocument();
  expect(within(lista).queryByText(/Reposición · FLU-01/)).toBeNull();   // los ceros no estorban
});

it("sin filas dice que no hay nada que cruzar", () => {
  render(<MapaCalor titulo="X" filas={[]} columnas={[]} celdas={[]} />);
  expect(screen.getByText(/nada que cruzar todavía/i)).toBeInTheDocument();
});
