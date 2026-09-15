import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import ConstructorRegla from "./ConstructorRegla";

const campos = [
  {
    nombre: "estado",
    etiqueta: "Estado",
    catalogo: [
      { etiqueta: "Hidalgo", valor: "hidalgo" },
      { etiqueta: "Otro", valor: "otro" },
    ],
  },
  { nombre: "folio", etiqueta: "Folio", catalogo: [] },
];

it("emite una Condicion con clausula Y al añadir una fila", async () => {
  const onChange = vi.fn();
  render(<ConstructorRegla campos={campos} value={null} onChange={onChange} />);
  // fila 1: estado != hidalgo
  await userEvent.selectOptions(screen.getByLabelText(/Campo de la condición 1/i), "estado");
  await userEvent.selectOptions(screen.getByLabelText(/Comparación de la condición 1/i), "!=");
  await userEvent.selectOptions(screen.getByLabelText(/Valor de la condición 1/i), "hidalgo");
  await userEvent.click(screen.getByRole("button", { name: /y además/i }));
  // fila 2: folio == 123 (texto libre, sin catalogo)
  await userEvent.selectOptions(screen.getByLabelText(/Campo de la condición 2/i), "folio");
  await userEvent.type(screen.getByLabelText(/Valor de la condición 2/i), "123");
  const ultima = onChange.mock.calls.at(-1)![0];
  expect(ultima).toEqual({
    campo: "estado",
    operador: "!=",
    igual: "hidalgo",
    y: [{ campo: "folio", operador: "==", igual: "123" }],
  });
});

it("el valor es un select si el campo tiene catalogo y un input si no", async () => {
  render(<ConstructorRegla campos={campos} value={null} onChange={vi.fn()} />);
  await userEvent.selectOptions(screen.getByLabelText(/Campo de la condición 1/i), "estado");
  expect(screen.getByLabelText(/Valor de la condición 1/i).tagName).toBe("SELECT");
  await userEvent.selectOptions(screen.getByLabelText(/Campo de la condición 1/i), "folio");
  expect(screen.getByLabelText(/Valor de la condición 1/i).tagName).toBe("INPUT");
});
