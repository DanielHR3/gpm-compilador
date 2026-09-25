import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import Usuarios from "./Usuarios";

vi.mock("@/lib/api", () => ({
  listarUsuarios: vi.fn(), aprobarUsuario: vi.fn(), desactivarUsuario: vi.fn(), cambiarRol: vi.fn(),
}));
afterEach(() => vi.clearAllMocks());

const YO = "daniel.hernandezr@hidalgo.gob.mx";
const lista = {
  usuarios: [
    { correo: YO, nombre: "Daniel Hernández", dependencia: "DGT", rol: "admin", estado: "activo" },
    { correo: "luis.vera@hidalgo.gob.mx", nombre: "Luis Vera", dependencia: "DSA", rol: "analista", estado: "pendiente" },
  ],
} as const;

it("agrupa las cuentas por estado, en tarjetas, con las pendientes primero", async () => {
  const { listarUsuarios } = await import("@/lib/api");
  vi.mocked(listarUsuarios).mockResolvedValue(lista as never);
  render(<Usuarios yo={YO} />);
  const pendientes = await screen.findByRole("region", { name: /pendientes de aprobación/i });
  expect(within(pendientes).getByRole("article", { name: "luis.vera@hidalgo.gob.mx" })).toBeInTheDocument();
  const activas = screen.getByRole("region", { name: /con acceso/i });
  const yo = within(activas).getByRole("article", { name: YO });
  expect(yo).toHaveTextContent(/superusuario/);
  expect(yo).toHaveTextContent(/tú/);
  expect(within(yo).queryByRole("button", { name: /desactivar/i })).not.toBeInTheDocument();   // no a mi mismo
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

it("aprobar una pendiente llama a la API y recarga", async () => {
  const { listarUsuarios, aprobarUsuario } = await import("@/lib/api");
  vi.mocked(listarUsuarios).mockResolvedValue(lista as never);
  vi.mocked(aprobarUsuario).mockResolvedValue({ usuario: { ...lista.usuarios[1], estado: "activo" } } as never);
  render(<Usuarios yo={YO} />);
  const tarjeta = await screen.findByRole("article", { name: "luis.vera@hidalgo.gob.mx" });
  await userEvent.click(within(tarjeta).getByRole("button", { name: /aprobar/i }));
  expect(aprobarUsuario).toHaveBeenCalledWith("luis.vera@hidalgo.gob.mx");
  await waitFor(() => expect(listarUsuarios).toHaveBeenCalledTimes(2));
});
