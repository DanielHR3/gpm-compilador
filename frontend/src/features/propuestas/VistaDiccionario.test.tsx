import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import VistaDiccionario from "./VistaDiccionario";

const pantallas = [
  { id: "p1", nombre: "Solicitud", actor: "Ciudadano", campos: [
    { etiqueta: "CURP", tipo: "text", obligatorio: true, opciones: [], condicion: null },
    { etiqueta: "Poder notarial", tipo: "file", obligatorio: false, opciones: [],
      condicion: "«Tipo de persona» es «Moral»" }] },
  { id: "p2", nombre: "Revisión", actor: "Funcionario", campos: [
    { etiqueta: "Dictamen", tipo: "select", obligatorio: true, opciones: ["Aprobado", "Rechazado"], condicion: null }] },
];

it("una tarjeta por pantalla y un campo por tarjeta, en palabras", () => {
  render(<VistaDiccionario pantallas={pantallas} />);
  const p1 = screen.getByRole("article", { name: "Pantalla 1 · Ciudadano · Solicitud" });
  expect(within(p1).getByText("CURP")).toBeInTheDocument();
  expect(within(p1).getByText("Texto")).toBeInTheDocument();
  expect(within(p1).getAllByLabelText("obligatorio")).toHaveLength(1);
  expect(within(p1).getByText("Archivo")).toBeInTheDocument();
  expect(within(p1).getByText("Visible solo si «Tipo de persona» es «Moral»")).toBeInTheDocument();
  const p2 = screen.getByRole("article", { name: "Pantalla 2 · Funcionario · Revisión" });
  expect(within(p2).getByText("Lista")).toBeInTheDocument();
  expect(within(p2).getByText("Aprobado · Rechazado")).toBeInTheDocument();
  expect(document.querySelector("table")).toBeNull();
});
