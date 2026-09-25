import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import Entrada from "./Entrada";

vi.mock("@/lib/api", () => ({
  entrar: vi.fn(),
  ErrorApi: class ErrorApi extends Error {
    status: number;
    constructor(status: number) { super(String(status)); this.status = status; }
  },
}));

afterEach(() => vi.clearAllMocks());

it("pide correo institucional y contraseña, y entra con ellos", async () => {
  const { entrar } = await import("@/lib/api");
  vi.mocked(entrar).mockResolvedValueOnce({
    token: "a.b.c", usuario: { correo: "daniel.hernandezr@hidalgo.gob.mx", nombre: "Daniel", dependencia: "DGT" },
  });
  const onEntrar = vi.fn();
  render(<Entrada onEntrar={onEntrar} />);
  expect(screen.getByRole("region", { name: /entrar al compilador gpm/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^entrar$/i })).toBeInTheDocument();
  expect(screen.getByText(/^compilador gpm$/i)).toBeInTheDocument();      // la franja guinda
  const boton = screen.getByRole("button", { name: /entrar/i });
  expect(boton).toBeDisabled();                                   // sin datos no se envía
  await userEvent.type(screen.getByLabelText(/correo institucional/i), " daniel.hernandezr@hidalgo.gob.mx ");
  await userEvent.type(screen.getByLabelText(/^contraseña$/i), "Secreta-123");
  await userEvent.click(boton);
  expect(entrar).toHaveBeenCalledWith("daniel.hernandezr@hidalgo.gob.mx", "Secreta-123");
  await waitFor(() => expect(onEntrar).toHaveBeenCalledWith(
    { correo: "daniel.hernandezr@hidalgo.gob.mx", nombre: "Daniel", dependencia: "DGT" }));
});

it("con credenciales malas lo dice en la misma pantalla y deja reintentar", async () => {
  const { entrar, ErrorApi } = await import("@/lib/api");
  vi.mocked(entrar).mockRejectedValueOnce(new (ErrorApi as unknown as new (s: number) => Error)(401));
  render(<Entrada onEntrar={vi.fn()} />);
  await userEvent.type(screen.getByLabelText(/correo institucional/i), "x@hidalgo.gob.mx");
  await userEvent.type(screen.getByLabelText(/^contraseña$/i), "mal");
  await userEvent.click(screen.getByRole("button", { name: /entrar/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/correo o contraseña incorrectos/i);
  expect(screen.getByRole("button", { name: /entrar/i })).toBeEnabled();
});

it("ofrece crear cuenta y recuperar la contraseña, y dice quién aprueba (decisión del 2026-09-25)", () => {
  render(<Entrada onEntrar={vi.fn()} />);
  expect(screen.getByRole("link", { name: /crear cuenta/i })).toHaveAttribute("href", "/registro");
  expect(screen.getByRole("link", { name: /olvidé mi contraseña/i })).toHaveAttribute("href", "/recuperar");
  expect(screen.getByText(/la aprueba la dirección general de tecnologías/i)).toBeInTheDocument();
});

it("el ojo enseña y vuelve a ocultar la contraseña", async () => {
  render(<Entrada onEntrar={vi.fn()} />);
  const campo = screen.getByLabelText(/^contraseña$/i);
  expect(campo).toHaveAttribute("type", "password");
  await userEvent.click(screen.getByRole("button", { name: /mostrar contraseña/i }));
  expect(campo).toHaveAttribute("type", "text");
  await userEvent.click(screen.getByRole("button", { name: /ocultar contraseña/i }));
  expect(campo).toHaveAttribute("type", "password");
});
