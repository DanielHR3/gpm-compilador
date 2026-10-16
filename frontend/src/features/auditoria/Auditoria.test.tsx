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

it("una tarjeta por evento, en castellano, con quién, qué, cuándo y desde dónde", async () => {
  const { leerAuditoria } = await import("@/lib/api");
  vi.mocked(leerAuditoria).mockResolvedValue({ filas } as never);
  render(<Auditoria />);

  const lista = await screen.findByRole("list", { name: /eventos/i });
  const tarjetas = within(lista).getAllByRole("article");
  expect(tarjetas).toHaveLength(4);
  expect(tarjetas[0]).toHaveTextContent(/Reconoció la inconsistencia DIC-07/);
  expect(tarjetas[0]).toHaveTextContent("luis.vera@hidalgo.gob.mx");
  expect(tarjetas[0]).toHaveTextContent("10.0.0.9");
  expect(tarjetas[1]).toHaveTextContent(/Descargó el \.gpm de producción/);
  expect(tarjetas[1]).toHaveTextContent(/rechaz/i);             // el (409) se dice, no se esconde
  expect(tarjetas[2]).toHaveTextContent(/Entró al asistente/);
  expect(tarjetas[3]).toHaveTextContent(/Fallo del servidor/);
  expect(tarjetas[3]).toHaveTextContent("#abc123def456");
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
