import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import Instrucciones from "./Instrucciones";

beforeEach(() => {
  localStorage.clear();
});

const pantalla = () => (
  <Instrucciones id="prueba" resumen="Haz esto y luego lo otro.">
    <p>El detalle largo.</p>
  </Instrucciones>
);

it("el resumen se ve siempre, sin tener que abrir nada", () => {
  render(pantalla());
  expect(screen.getByText("Haz esto y luego lo otro.")).toBeInTheDocument();
});

it("la primera vez el detalle viene abierto", () => {
  render(pantalla());
  expect(screen.getByRole("group")).toHaveAttribute("open");
  expect(screen.getByText("El detalle largo.")).toBeVisible();
});

it("si ya lo cerró una vez, la siguiente abre plegado", async () => {
  const { unmount } = render(pantalla());
  await userEvent.click(screen.getByText(/cómo funciona esta pantalla/i));
  expect(screen.getByRole("group")).not.toHaveAttribute("open");

  unmount();
  render(pantalla());
  expect(screen.getByRole("group")).not.toHaveAttribute("open");
});

it("cada pantalla recuerda lo suyo por separado", async () => {
  render(pantalla());
  await userEvent.click(screen.getByText(/cómo funciona esta pantalla/i));
  expect(localStorage.getItem("gpmc.ayuda.prueba")).toBe("plegado");
  expect(localStorage.getItem("gpmc.ayuda.otra")).toBeNull();
});

it("si localStorage revienta, la pantalla sigue de pie", async () => {
  // Ventana privada, cookies bloqueadas: el acceso lanza. La ayuda no puede
  // ser el motivo de que no se vea la pantalla.
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("acceso denegado");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("acceso denegado");
  });

  render(pantalla());
  expect(screen.getByText("Haz esto y luego lo otro.")).toBeInTheDocument();
  expect(screen.getByRole("group")).toHaveAttribute("open");
  // y cerrarlo tampoco revienta
  await userEvent.click(screen.getByText(/cómo funciona esta pantalla/i));
  expect(screen.getByText("Haz esto y luego lo otro.")).toBeInTheDocument();

  vi.restoreAllMocks();
});
