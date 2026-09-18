import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import ConstructorRegla from "./ConstructorRegla";

const campos = [
  {
    nombre: "estado",
    etiqueta: "Estado",
    pantalla: 0,
    catalogo: [
      { etiqueta: "Hidalgo", valor: "hidalgo" },
      { etiqueta: "Otro", valor: "otro" },
    ],
  },
  { nombre: "folio", etiqueta: "Folio", pantalla: 0, catalogo: [] },
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

const muchos = Array.from({ length: 12 }, (_, i) => ({
  nombre: `c${i}`,
  etiqueta: `Campo ${i}`,
  pantalla: i < 6 ? 0 : 2,
  catalogo: [{ valor: "v", etiqueta: "V" }],
}));

it("los campos que se capturan después se ofrecen deshabilitados y con el motivo", async () => {
  render(
    <ConstructorRegla
      campos={muchos}
      value={null}
      onChange={vi.fn()}
      objetivo={{ interno: "c0", pantalla: 0 }}
      frase=""
    />,
  );

  const opcion = screen.getByRole("option", { name: /Campo 6 — se captura después/i });
  expect(opcion).toBeDisabled();
  expect(screen.getByRole("option", { name: /Campo 0 — es este mismo campo/i })).toBeDisabled();
});

it("agrupa las opciones para que se entienda por qué unas no sirven", () => {
  render(
    <ConstructorRegla
      campos={muchos}
      value={null}
      onChange={vi.fn()}
      objetivo={{ interno: "c0", pantalla: 0 }}
      frase="depende de Campo 3"
    />,
  );

  const grupos = [...document.querySelectorAll("optgroup")].map((g) => g.label);
  expect(grupos).toEqual([
    "Sugeridos — los menciona el Diccionario",
    "También puedes usar",
    "No se pueden usar aquí",
  ]);
});

it("con muchos campos aparece un buscador que filtra las opciones", async () => {
  render(
    <ConstructorRegla campos={muchos} value={null} onChange={vi.fn()} objetivo={null} frase="" />,
  );

  await userEvent.type(screen.getByLabelText(/buscar campo de la condición 1/i), "Campo 7");

  expect(screen.getByRole("option", { name: /Campo 7/ })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /Campo 3/ })).not.toBeInTheDocument();
});

it("con pocos campos no se estorba con un buscador", () => {
  render(<ConstructorRegla campos={campos} value={null} onChange={vi.fn()} />);

  expect(screen.queryByLabelText(/buscar campo/i)).not.toBeInTheDocument();
});
