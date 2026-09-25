import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import Recuperar, { Restablecer } from "./Recuperar";

vi.mock("@/lib/api", () => ({ recuperar: vi.fn(), restablecer: vi.fn() }));
afterEach(() => vi.clearAllMocks());

it("pide el correo y repite el mensaje del servidor, sin decir si existe la cuenta", async () => {
  const { recuperar } = await import("@/lib/api");
  vi.mocked(recuperar).mockResolvedValueOnce({ mensaje: "Si el correo tiene cuenta, recibirá una liga." });
  render(<Recuperar />);
  await userEvent.type(screen.getByLabelText(/correo institucional/i), "luis.vera@hidalgo.gob.mx");
  await userEvent.click(screen.getByRole("button", { name: /enviar liga/i }));
  expect(recuperar).toHaveBeenCalledWith("luis.vera@hidalgo.gob.mx");
  expect(await screen.findByRole("status")).toHaveTextContent(/si el correo tiene cuenta/i);
});

it("la liga del correo pide la contraseña nueva dos veces y la guarda con el token", async () => {
  const { restablecer } = await import("@/lib/api");
  vi.mocked(restablecer).mockResolvedValueOnce({ ok: true });
  render(<Restablecer token="tok-123" />);
  await userEvent.type(screen.getByLabelText(/contraseña nueva/i), "Nueva-789!");
  await userEvent.type(screen.getByLabelText(/repite la contraseña/i), "Nueva-789!");
  await userEvent.click(screen.getByRole("button", { name: /guardar contraseña/i }));
  expect(restablecer).toHaveBeenCalledWith("tok-123", "Nueva-789!");
  expect(await screen.findByRole("link", { name: /ir a la entrada/i })).toBeInTheDocument();
});

it("una liga vencida lo dice y manda a pedir otra", async () => {
  const { restablecer } = await import("@/lib/api");
  vi.mocked(restablecer).mockRejectedValueOnce(new Error("400"));
  render(<Restablecer token="viejo" />);
  await userEvent.type(screen.getByLabelText(/contraseña nueva/i), "Nueva-789!");
  await userEvent.type(screen.getByLabelText(/repite la contraseña/i), "Nueva-789!");
  await userEvent.click(screen.getByRole("button", { name: /guardar contraseña/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/no es válida, ya se usó o caducó/i);
});
