import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import Auditoria from "./Auditoria";

vi.mock("@/lib/api", () => ({
  leerAuditoria: vi.fn(),
  urlAuditoriaCsv: (f: Record<string, string>) => `/api/v1/auditoria?formato=csv&${new URLSearchParams(f)}`,
}));
afterEach(() => vi.clearAllMocks());

const SID = "a".repeat(16);
const filas = [
  { fecha: "2026-10-16T18:05:00+00:00", usuario: "luis.vera@hidalgo.gob.mx", dependencia: "DSA",
    accion: "hueco.reconocer", sid: SID, detalle: "DIC-07", ip: "10.0.0.9" },
  { fecha: "2026-10-16T18:04:00+00:00", usuario: "luis.vera@hidalgo.gob.mx", dependencia: "DSA",
    accion: "gpm.descargar", sid: SID, detalle: "produccion (409)", ip: "10.0.0.9" },
  { fecha: "2026-10-16T18:00:00+00:00", usuario: "daniel.hernandezr@hidalgo.gob.mx", dependencia: "DGT",
    accion: "sesion.entrar", sid: null, detalle: "", ip: "10.0.0.1" },
  { fecha: "2026-10-16T17:59:00+00:00", usuario: "anonimo", dependencia: "",
    accion: "error.servidor", sid: null, detalle: "RuntimeError en GET /api/v1/x #abc123def456 (500)", ip: "10.0.0.1" },
];

it("una tarjeta por persona con sus cuentas, y el detalle plegado en castellano", async () => {
  const { leerAuditoria } = await import("@/lib/api");
  vi.mocked(leerAuditoria).mockResolvedValue({ filas } as never);
  render(<Auditoria />);

  const personas = await screen.findByRole("list", { name: /personas/i });
  const tarjetas = within(personas).getAllByRole("article");
  // Luis, Daniel y el anonimo del fallo: tres tarjetas, no cuatro eventos sueltos.
  expect(tarjetas.map((t) => t.getAttribute("aria-label"))).toEqual([
    "luis.vera@hidalgo.gob.mx", "daniel.hernandezr@hidalgo.gob.mx", "anonimo",
  ]);
  const luis = tarjetas[0];
  expect(luis).toHaveTextContent(/2 acciones/);
  expect(luis).toHaveTextContent(/1 trámite/);
  expect(luis).toHaveTextContent(/1 rechazada/);
  expect(luis).toHaveTextContent("DSA");
  // El detalle viene plegado y se abre.
  expect(within(luis).getByText(/Reconoció la inconsistencia DIC-07/)).not.toBeVisible();
  await userEvent.click(within(luis).getByText(/ver las 2 acciones/i));
  const eventos = within(luis).getAllByRole("listitem");
  expect(eventos[0]).toBeVisible();
  expect(eventos[0]).toHaveTextContent(/Reconoció la inconsistencia DIC-07/);
  expect(eventos[0]).toHaveTextContent("10.0.0.9");
  expect(eventos[1]).toHaveTextContent(/Descargó el \.gpm de producción/);
  expect(eventos[1]).toHaveTextContent(/rechaz/i);
  // El fallo del servidor se ve desde fuera, con su numero.
  expect(tarjetas[2]).toHaveTextContent(/1 fallo del servidor/);
  await userEvent.click(within(tarjetas[2]).getByText(/ver la acción/i));
  expect(tarjetas[2]).toHaveTextContent("#abc123def456");
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

it("los filtros van a la API y «Solo errores» pide solo_errores", async () => {
  const { leerAuditoria } = await import("@/lib/api");
  vi.mocked(leerAuditoria).mockResolvedValue({ filas: [] } as never);
  render(<Auditoria />);
  await waitFor(() => expect(leerAuditoria).toHaveBeenCalled());

  await userEvent.type(screen.getByRole("textbox", { name: /usuario/i }), "luis.vera@hidalgo.gob.mx");
  await userEvent.click(screen.getByRole("checkbox", { name: /solo errores/i }));
  await userEvent.click(screen.getByRole("button", { name: /buscar/i }));

  await waitFor(() =>
    expect(leerAuditoria).toHaveBeenLastCalledWith(
      expect.objectContaining({ usuario: "luis.vera@hidalgo.gob.mx", solo_errores: true }),
    ),
  );
  expect(await screen.findByText(/sin eventos/i)).toBeInTheDocument();
});

it("arranca filtrada por el trámite que viene en la dirección y ofrece el CSV con los mismos filtros", async () => {
  const { leerAuditoria } = await import("@/lib/api");
  vi.mocked(leerAuditoria).mockResolvedValue({ filas } as never);
  render(<Auditoria sidInicial={SID} />);

  await waitFor(() => expect(leerAuditoria).toHaveBeenCalledWith(expect.objectContaining({ sid: SID })));
  const csv = await screen.findByRole("link", { name: /descargar csv/i });
  expect(csv).toHaveAttribute("href", expect.stringContaining(`sid=${SID}`));
  expect(csv).toHaveAttribute("href", expect.stringContaining("formato=csv"));
});
