import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import Propuestas from "./Propuestas";

vi.mock("@/lib/api", () => ({
  leerGenerados: vi.fn(),
  decidirDocumento: vi.fn(),
  subirDocumento: vi.fn(),
  ErrorApi: class extends Error { status = 0; error = ""; constructor(m: string) { super(m); this.error = m; } },
}));
vi.mock("mermaid", () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: "<svg></svg>" })) },
}));

const SID = "a".repeat(16);
const doc = { texto: "# x", version_prompt: "dicc-v1", ronda: 1, huecos: [], decision: "pendiente" as const };
const listo = { estado: "listo" as const, motivo: null, nombre: "Constancia", diccionario: doc, tobe: { ...doc, version_prompt: "tobe-v1" } };

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });

it("en generando muestra la espera y consulta cada 3 s hasta listo", async () => {
  const { leerGenerados } = await import("@/lib/api");
  vi.mocked(leerGenerados)
    .mockResolvedValueOnce({ estado: "generando", motivo: null, nombre: "Constancia", diccionario: null, tobe: null })
    .mockResolvedValueOnce(listo);
  render(<Propuestas sid={SID} onListo={() => {}} />);
  expect(await screen.findByText(/uno o dos minutos/i)).toBeInTheDocument();
  expect(screen.getByText(/puedes cerrar y volver/i)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /constancia/i })).toBeInTheDocument();
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  expect(await screen.findAllByRole("article")).toHaveLength(2);
  expect(leerGenerados).toHaveBeenCalledTimes(2);
});

it("sin licencia muestra el motivo y las dos zonas de carga", async () => {
  const { leerGenerados } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue({ estado: "sin_licencia", motivo: "No hay licencia.", nombre: null, diccionario: null, tobe: null });
  render(<Propuestas sid={SID} onListo={() => {}} />);
  expect(await screen.findByText("No hay licencia.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /trámite sin nombre/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/subir mi diccionario/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/subir mi to-be/i)).toBeInTheDocument();
});

it("cuando la decision devuelve el expediente, entra al wizard por onListo", async () => {
  const { leerGenerados, decidirDocumento } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue(listo);
  const est = { sid: SID, manifiesto: {}, huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false };
  vi.mocked(decidirDocumento)
    .mockResolvedValueOnce({ tipo: "generados", generados: { ...listo, diccionario: { ...doc, decision: "aceptada" } } })
    .mockResolvedValueOnce({ tipo: "expediente", estado: est });
  const onListo = vi.fn();
  render(<Propuestas sid={SID} onListo={onListo} />);
  const [dicc] = await screen.findAllByRole("button", { name: /aceptar tal cual/i });
  await userEvent.click(dicc);
  await waitFor(() => expect(screen.getByText(/aceptado tal cual/i)).toBeInTheDocument());
  await userEvent.click(screen.getByRole("button", { name: /aceptar tal cual/i }));
  await waitFor(() => expect(onListo).toHaveBeenCalledWith(est));
});

it("un 422 del extractor se muestra y la pantalla sigue en propuestas", async () => {
  const { leerGenerados, decidirDocumento, ErrorApi } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue({ ...listo, diccionario: { ...doc, decision: "aceptada" } });
  const e = new (ErrorApi as any)("no se extrajo ninguna pantalla"); e.status = 422;
  vi.mocked(decidirDocumento).mockRejectedValue(e);
  render(<Propuestas sid={SID} onListo={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: /aceptar tal cual/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se extrajo ninguna pantalla/);
  // El Diccionario ya estaba aceptado: sin zona de carga no habria salida.
  expect(screen.getByLabelText(/subir mi diccionario/i)).toBeInTheDocument();
});
