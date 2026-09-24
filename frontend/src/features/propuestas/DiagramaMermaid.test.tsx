import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

it("en grande trae zoom: acercar y alejar cambian la escala y ajustar la regresa", async () => {
  render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} grande />);
  await screen.findByTestId("svg-mermaid");
  const lienzo = screen.getByTestId("lienzo-diagrama");
  await userEvent.click(screen.getByRole("button", { name: "Acercar" }));
  expect(lienzo.style.transform).toBe("scale(1.25)");
  await userEvent.click(screen.getByRole("button", { name: "Alejar" }));
  await userEvent.click(screen.getByRole("button", { name: "Alejar" }));
  expect(lienzo.style.transform).toBe("scale(0.75)");
  await userEvent.click(screen.getByRole("button", { name: "Ajustar" }));
  expect(lienzo.style.transform).toBe("scale(1)");
});

it("pantalla completa solo si el navegador la permite", async () => {
  const { unmount } = render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} grande />);
  await screen.findByTestId("svg-mermaid");
  expect(screen.queryByRole("button", { name: /pantalla completa/i })).not.toBeInTheDocument();
  unmount();
  Object.defineProperty(document, "fullscreenEnabled", { value: true, configurable: true });
  const pedir = vi.fn().mockResolvedValue(undefined);
  HTMLElement.prototype.requestFullscreen = pedir;
  render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> C\n```"} retardoMs={0} grande />);
  await userEvent.click(await screen.findByRole("button", { name: /pantalla completa/i }));
  expect(pedir).toHaveBeenCalled();
  Object.defineProperty(document, "fullscreenEnabled", { value: undefined, configurable: true });
});

it("sin grande no hay controles", async () => {
  render(<DiagramaMermaid texto={"```mermaid\nflowchart TD\n A --> B\n```"} retardoMs={0} />);
  await screen.findByTestId("svg-mermaid");
  expect(screen.queryByRole("button", { name: "Acercar" })).not.toBeInTheDocument();
});
