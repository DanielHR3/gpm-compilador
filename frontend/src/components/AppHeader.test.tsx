import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import AppHeader from "./AppHeader";

it("muestra el título de la pantalla y el logo institucional", () => {
  render(<AppHeader titulo="Carga de insumos" />);
  expect(screen.getByText("Carga de insumos")).toBeInTheDocument();
  // El logo sustituye al texto "Gobierno del Estado de Hidalgo": dice lo mismo,
  // y sobre la barra blanca puede ir en sus colores institucionales.
  const logo = screen.getByRole("img", { name: /hidalgo/i });
  expect(logo).toHaveAttribute("src", expect.stringContaining("logo"));
  expect(screen.queryByText("Gobierno del Estado de Hidalgo")).not.toBeInTheDocument();
});

it("con un expediente abierto lleva el menú «Entrega»; sin él, no", () => {
  const { rerender } = render(
    <AppHeader titulo="Revisión del expediente" entrega={{ sid: "a".repeat(16), puerta: { desbloqueado: true, bloqueantes: [] } }} />,
  );
  expect(screen.getByRole("button", { name: /entrega.*listo/i })).toBeInTheDocument();

  rerender(<AppHeader titulo="Catálogos" />);
  expect(screen.queryByRole("button", { name: /entrega/i })).not.toBeInTheDocument();
});

it("con sesión lleva la campanita de Simplifica; sin sesión, no", async () => {
  const api = await import("@/lib/api");
  const { vi } = await import("vitest");
  vi.spyOn(api, "leerSolicitudes").mockResolvedValue({ solicitudes: [], nuevas: 0 });
  const usuario = { correo: "a@hidalgo.gob.mx", nombre: "Ana López", dependencia: "DGT", rol: "analista" } as never;
  const { rerender } = render(<AppHeader titulo="Inicio" usuario={usuario} />);
  expect(await screen.findByRole("button", { name: /solicitudes de simplifica/i })).toBeInTheDocument();
  rerender(<AppHeader titulo="Inicio" />);
  expect(screen.queryByRole("button", { name: /solicitudes de simplifica/i })).not.toBeInTheDocument();
});
