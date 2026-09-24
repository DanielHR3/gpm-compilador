import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import DiagramaMermaid, { primerBloqueMermaid } from "./DiagramaMermaid";

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async (_id: string, codigo: string) => {
      if (codigo.includes("ROTO")) throw new Error("Parse error");
      return { svg: `<svg data-testid="svg-mermaid"><text>${codigo.length}</text></svg>` };
    }),
  },
}));

it("primerBloqueMermaid toma solo el primer bloque, el que lee el compilador", () => {
  const texto = "# TO-BE\n\n```mermaid\nflowchart TD\n A --> B\n```\n\n```mermaid\nflowchart TD\n C --> D\n```";
  expect(primerBloqueMermaid(texto)).toBe("flowchart TD\n A --> B");
  expect(primerBloqueMermaid("sin diagrama")).toBeNull();
});

it("dibuja el primer bloque y avisa cuando el texto no tiene diagrama", async () => {
  const { rerender } = render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} />);
  expect(await screen.findByTestId("svg-mermaid")).toBeInTheDocument();
  rerender(<DiagramaMermaid texto="sin diagrama" retardoMs={0} />);
  expect(await screen.findByText(/no tiene un bloque/i)).toBeInTheDocument();
});

it("un diagrama que no se puede dibujar lo dice sin tirar la tarjeta", async () => {
  render(<DiagramaMermaid texto={"```mermaid\nROTO\n```"} retardoMs={0} />);
  expect(await screen.findByRole("status")).toHaveTextContent(/no se pudo dibujar/i);
});

it("cuando mermaid no puede dibujar, dice en que linea para poder corregirlo", async () => {
  render(<DiagramaMermaid texto={"```mermaid\nROTO\n```"} retardoMs={0} />);
  const aviso = await screen.findByRole("status");
  expect(aviso).toHaveTextContent(/Parse error/);
});
