import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import DiagramaToBe from "./DiagramaToBe";

vi.mock("@/lib/api", () => ({ leerToBe: vi.fn() }));
vi.mock("mermaid", () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: '<svg data-testid="svg-mermaid"></svg>' })) },
}));
afterEach(() => vi.clearAllMocks());

const manifiesto = { flujo: {
  tareas: [{ id: "t1", pantallas: ["p1"] }, { id: "t2", pantallas: ["p2"] }, { id: "t_fin", pantallas: [] }],
  conexiones: [{ de: "t1", a: "t2", cuando: { campo: "x" } }, { de: "t1", a: "t_fin", cuando: { campo: "x" } }],
} };

it("sin TO-BE en la sesion no aparece", async () => {
  const { leerToBe } = await import("@/lib/api");
  vi.mocked(leerToBe).mockRejectedValue(new Error("404"));
  const { container } = render(<DiagramaToBe sid={"a".repeat(16)} manifiesto={manifiesto} />);
  await vi.waitFor(() => expect(leerToBe).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
});

it("plegada con el conteo; al abrir dibuja el diagrama grande", async () => {
  const { leerToBe } = await import("@/lib/api");
  vi.mocked(leerToBe).mockResolvedValue("```mermaid\nflowchart TD\n A --> B\n```");
  render(<DiagramaToBe sid={"a".repeat(16)} manifiesto={manifiesto} />);
  const tarjeta = await screen.findByRole("article", { name: /diagrama del to-be/i });
  expect(tarjeta).toHaveTextContent("2 tareas · 1 decisión");
  expect(screen.queryByTestId("svg-mermaid")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /ver el diagrama/i }));
  expect(await screen.findByTestId("svg-mermaid", {}, { timeout: 2000 })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Acercar" })).toBeInTheDocument();
});
