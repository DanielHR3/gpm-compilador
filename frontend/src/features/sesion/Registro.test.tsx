import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import Registro from "./Registro";

vi.mock("@/lib/api", () => ({
  registrar: vi.fn(),
  ErrorApi: class ErrorApi extends Error {
    status: number;
    constructor(status: number, msg = "") { super(msg); this.status = status; }
  },
}));

afterEach(() => vi.clearAllMocks());

async function llenar(correo: string, contrasena = "Secreta-123", confirma = contrasena) {
  await userEvent.type(screen.getByLabelText(/correo institucional/i), correo);
  await userEvent.type(screen.getByLabelText(/nombre completo/i), "Luis Vera");
  await userEvent.type(screen.getByLabelText(/dependencia/i), "DSA");
  await userEvent.type(screen.getByLabelText(/^contraseña/i), contrasena);
  await userEvent.type(screen.getByLabelText(/repite la contraseña/i), confirma);
}

it("solo deja solicitar con correo institucional y contraseñas iguales de 8+", async () => {
  render(<Registro />);
  const boton = screen.getByRole("button", { name: /solicitar cuenta/i });
  await llenar("luis@gmail.com");
  expect(screen.getByText(/debe terminar en @hidalgo.gob.mx/i)).toBeInTheDocument();
  expect(boton).toBeDisabled();
  await userEvent.clear(screen.getByLabelText(/correo institucional/i));
  await userEvent.type(screen.getByLabelText(/correo institucional/i), "luis.vera@hidalgo.gob.mx");
  await userEvent.clear(screen.getByLabelText(/repite la contraseña/i));
  await userEvent.type(screen.getByLabelText(/repite la contraseña/i), "otra-cosa");
  expect(screen.getByText(/no coinciden/i)).toBeInTheDocument();
  expect(boton).toBeDisabled();
});

it("registra y explica que la cuenta queda pendiente de la DGT", async () => {
  const { registrar } = await import("@/lib/api");
  vi.mocked(registrar).mockResolvedValueOnce({ estado: "pendiente", correo: "luis.vera@hidalgo.gob.mx" });
  render(<Registro />);
  await llenar("Luis.Vera@hidalgo.gob.mx");
  await userEvent.click(screen.getByRole("button", { name: /solicitar cuenta/i }));
  expect(registrar).toHaveBeenCalledWith({ correo: "Luis.Vera@hidalgo.gob.mx", nombre: "Luis Vera", dependencia: "DSA", contrasena: "Secreta-123" });
  expect(await screen.findByRole("status")).toHaveTextContent(/pendiente|aprueb/i);
  expect(screen.getByRole("status")).toHaveTextContent("luis.vera@hidalgo.gob.mx");
});

it("un 422 del servidor se muestra con su motivo", async () => {
  const { registrar, ErrorApi } = await import("@/lib/api");
  vi.mocked(registrar).mockRejectedValueOnce(new (ErrorApi as unknown as new (s: number, m: string) => Error)(422, "solo se admiten correos @hidalgo.gob.mx"));
  render(<Registro />);
  await llenar("luis.vera@hidalgo.gob.mx");
  await userEvent.click(screen.getByRole("button", { name: /solicitar cuenta/i }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/solo se admiten correos/i));
});
