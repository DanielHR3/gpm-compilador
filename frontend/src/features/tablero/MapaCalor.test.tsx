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

it("la esquina de la cabecera ocupa su celda (sin sr-only), o la rejilla se corre una columna", () => {
  render(<MapaCalor titulo="X" {...M} />);
  const rejilla = screen.getByRole("grid", { name: "X" });
  const cabecera = rejilla.firstElementChild!;
  expect(cabecera.children).toHaveLength(M.columnas.length + 1);
  expect(cabecera.firstElementChild).not.toHaveClass("sr-only");
});

it("en modo cuenta trae la leyenda de la rampa, del minimo al maximo", () => {
  render(<MapaCalor titulo="X" {...M} />);
  const leyenda = screen.getByRole("img", { name: /escala/i });
  expect(leyenda).toHaveTextContent(/^1/);
  expect(leyenda).toHaveTextContent(/20$/);
});

it("en modo presencia no hay leyenda de rampa", () => {
  render(<MapaCalor titulo="Requisitos" filas={["Acta"]} columnas={["Testamento"]} celdas={[[1]]} modo="presencia" />);
  expect(screen.queryByRole("img", { name: /escala/i })).toBeNull();
});

it("el detalle de columna va al tooltip y al nombre accesible de la celda, no al encabezado", () => {
  render(<MapaCalor titulo="X" {...M} etiquetaColumna={(c) => (c === "DIC-08" ? "Visibilidad" : c)} detalleColumna={(c) => c} />);
  expect(screen.getByRole("columnheader", { name: "Visibilidad" })).not.toHaveTextContent("DIC-08");
  const celda = screen.getByRole("gridcell", { name: "Reposición · Visibilidad (DIC-08): 20" });
  expect(celda).toHaveAttribute("title", "Reposición · Visibilidad (DIC-08): 20");
});
