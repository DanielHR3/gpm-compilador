import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import Inicio from "./Inicio";

vi.mock("@/lib/api", () => ({ leerCapacidades: vi.fn() }));
afterEach(() => vi.clearAllMocks());

it("ofrece los dos caminos, cada uno con su enlace", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockResolvedValue({ proponer: true, motivo: null });
  render(<Inicio />);
  expect(screen.getByRole("heading", { name: /qué tienes del trámite/i })).toBeInTheDocument();
  expect(screen.getByRole("article", { name: /expediente completo/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /empezar con el expediente completo/i })).toHaveAttribute("href", "/expediente");
  expect(await screen.findByRole("link", { name: /empezar con el as-is/i })).toHaveAttribute("href", "/desde-as-is");
});

it("sin licencia, el camino del AS-IS sale desactivado con el motivo", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockResolvedValue({ proponer: false, motivo: "Sin licencia de Planeación." });
  render(<Inicio />);
  expect(await screen.findByText("Sin licencia de Planeación.")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /empezar con el as-is/i })).not.toBeInTheDocument();
  const boton = screen.getByRole("button", { name: /empezar con el as-is/i });
  expect(boton).toBeDisabled();
  // El motivo esta ligado al boton y no se salta con Tab (un boton
  // desactivado no recibe el foco): el motivo mismo es enfocable.
  expect(boton).toHaveAccessibleDescription("Sin licencia de Planeación.");
  expect(screen.getByText("Sin licencia de Planeación.")).toHaveAttribute("tabindex", "0");
});

it("si no se puede consultar, el camino del AS-IS queda activo", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockRejectedValue(new Error("red"));
  render(<Inicio />);
  expect(await screen.findByRole("link", { name: /empezar con el as-is/i })).toBeInTheDocument();
});

it("en modo de pruebas el camino del AS-IS lo avisa", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockResolvedValue({ proponer: true, motivo: null, pruebas: true });
  render(<Inicio />);
  expect(await screen.findByRole("note", { name: /modo de pruebas/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /empezar con el as-is/i })).toBeInTheDocument();
});
