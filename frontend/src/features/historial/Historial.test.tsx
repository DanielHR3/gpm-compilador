import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

const leerHistorial = vi.fn();
vi.mock("@/lib/api", () => ({
  leerHistorial: (...a: unknown[]) => leerHistorial(...a),
  urlGpm: (sid: string) => `/api/v1/expedientes/${sid}/gpm?modo=produccion`,
}));

import Historial from "./Historial";

const SID_A = "a".repeat(16);
const SID_B = "b".repeat(16);

it("pinta una tarjeta por tramite, con enlace a su revision y descarga del .gpm", async () => {
  leerHistorial.mockResolvedValueOnce({
    tramites: [
      { sid: SID_B, nombre: "Constancia de Residencia", dependencia: "SEGOB",
        modificado: "2026-09-23T15:30:00+00:00" },
      { sid: SID_A, nombre: "Testamento", dependencia: "IIFEH",
        modificado: "2026-09-21T10:00:00+00:00" },
    ],
  });
  render(<Historial />);
  const tarjeta = await screen.findByRole("article", { name: /Constancia de Residencia/ });
  expect(tarjeta).toHaveTextContent("SEGOB");
  expect(tarjeta).toHaveTextContent(/2026/);
  // Solo tarjetas en la SPA: nunca una tabla.
  expect(screen.queryByRole("table")).toBeNull();
  const abrir = screen.getByRole("link", { name: /Constancia de Residencia/ });
  expect(abrir).toHaveAttribute("href", `/revisar/${SID_B}`);
  const descargas = screen.getAllByRole("link", { name: /descargar \.gpm/i });
  expect(descargas[0]).toHaveAttribute("href", expect.stringContaining(`${SID_B}/gpm`));
  expect(descargas).toHaveLength(2);
});

it("sin tramites lo dice en palabras, no con una lista vacia", async () => {
  leerHistorial.mockResolvedValueOnce({ tramites: [] });
  render(<Historial />);
  expect(await screen.findByText(/todavía no hay ningún trámite/i)).toBeInTheDocument();
  expect(screen.queryByRole("article")).toBeNull();
});

it("si el servidor no contesta avisa en vez de quedarse en «Cargando»", async () => {
  leerHistorial.mockRejectedValueOnce(new Error("red"));
  render(<Historial />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo/i);
});
