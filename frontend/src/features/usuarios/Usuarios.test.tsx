import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import Usuarios from "./Usuarios";

vi.mock("@/lib/api", () => ({
  listarUsuarios: vi.fn(), aprobarUsuario: vi.fn(), desactivarUsuario: vi.fn(), cambiarRol: vi.fn(), crearUsuario: vi.fn(),
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


it("«Nueva cuenta» abre un modal y da de alta un superusuario de inmediato", async () => {
  // Regla de la DGT (2026-10-16): los superusuarios se crean desde aqui, por
  // el superusuario, sin pasar por el registro publico ni por «pendiente».
  const { listarUsuarios, crearUsuario } = await import("@/lib/api");
  vi.mocked(listarUsuarios).mockResolvedValue(lista as never);
  vi.mocked(crearUsuario).mockResolvedValue({ usuario: { correo: "ana.lopez@hidalgo.gob.mx", nombre: "Ana López", dependencia: "DGT", rol: "admin", estado: "activo" } } as never);
  render(<Usuarios yo={YO} />);
  await screen.findByRole("article", { name: YO });

  await userEvent.click(screen.getByRole("button", { name: /nueva cuenta/i }));
  const modal = await screen.findByRole("dialog", { name: /nueva cuenta/i });
  await userEvent.type(within(modal).getByRole("textbox", { name: /correo/i }), "ana.lopez@hidalgo.gob.mx");
  await userEvent.type(within(modal).getByRole("textbox", { name: /nombre/i }), "Ana López");
  await userEvent.type(within(modal).getByRole("textbox", { name: /dependencia/i }), "DGT");
  await userEvent.type(within(modal).getByLabelText(/contraseña temporal/i), "Temporal-789");
  await userEvent.click(within(modal).getByRole("radio", { name: /superusuario/i }));
  await userEvent.click(within(modal).getByRole("button", { name: /dar de alta/i }));

  await waitFor(() => expect(crearUsuario).toHaveBeenCalledWith({
    correo: "ana.lopez@hidalgo.gob.mx", nombre: "Ana López", dependencia: "DGT", contrasena: "Temporal-789", rol: "admin",
  }));
  await waitFor(() => expect(listarUsuarios).toHaveBeenCalledTimes(2));         // recarga
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
});

it("si el alta falla el modal lo dice y no se cierra", async () => {
  const { listarUsuarios, crearUsuario } = await import("@/lib/api");
  vi.mocked(listarUsuarios).mockResolvedValue(lista as never);
  vi.mocked(crearUsuario).mockRejectedValue(Object.assign(new Error("ya existe"), { status: 409, mensaje: "ya existe una cuenta con ese correo" }));
  render(<Usuarios yo={YO} />);
  await screen.findByRole("article", { name: YO });
  await userEvent.click(screen.getByRole("button", { name: /nueva cuenta/i }));
  const modal = await screen.findByRole("dialog", { name: /nueva cuenta/i });
  await userEvent.type(within(modal).getByRole("textbox", { name: /correo/i }), "luis.vera@hidalgo.gob.mx");
  await userEvent.type(within(modal).getByRole("textbox", { name: /nombre/i }), "Luis");
  await userEvent.type(within(modal).getByRole("textbox", { name: /dependencia/i }), "DSA");
  await userEvent.type(within(modal).getByLabelText(/contraseña temporal/i), "Temporal-789");
  await userEvent.click(within(modal).getByRole("button", { name: /dar de alta/i }));
  expect(await within(modal).findByRole("alert")).toHaveTextContent(/ya existe/i);
  expect(screen.getByRole("dialog", { name: /nueva cuenta/i })).toBeInTheDocument();
});
