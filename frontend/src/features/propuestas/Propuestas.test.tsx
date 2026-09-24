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
const conVista = { ...doc, vista: [{ id: "p1", nombre: "Solicitud", actor: "Ciudadano", campos: [] }] };
const listo = { estado: "listo" as const, motivo: null, nombre: "Constancia",
  diccionario: conVista, tobe: { ...doc, version_prompt: "tobe-v1" },
  insumos: { diccionario: false, tobe: false } };
/** Tarjetas de documento (no las de pantalla del Diccionario). */
const documentos = () => screen.queryAllByRole("article", { name: /^(diccionario de datos|propuesta to-be)$/i });

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
  await waitFor(() => expect(documentos()).toHaveLength(1));
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
  // Con las dos zonas a la vista no hay «1 de 2»: solo el camino.
  expect(screen.getByRole("navigation", { name: /migas de pan/i })).not.toHaveTextContent(/de 2/);
});

it("primero el Diccionario (1 de 2), despues el TO-BE (2 de 2)", async () => {
  const { leerGenerados, decidirDocumento } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue(listo);
  vi.mocked(decidirDocumento).mockResolvedValueOnce({ tipo: "generados", generados: {
    ...listo, diccionario: { ...conVista, decision: "aceptada" }, insumos: { diccionario: true, tobe: false } } });
  render(<Propuestas sid={SID} onListo={() => {}} />);
  // Mientras no llega la respuesta, las migas no prometen un paso.
  expect(screen.getByRole("navigation", { name: /migas de pan/i })).not.toHaveTextContent(/de 2/);
  expect(await screen.findByText("Diccionario (1 de 2)")).toBeInTheDocument();
  expect(documentos()).toHaveLength(1);
  expect(screen.getByRole("article", { name: /^diccionario de datos$/i })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /aceptar tal cual/i }));
  expect(await screen.findByText("TO-BE (2 de 2)")).toBeInTheDocument();
  expect(screen.getByRole("article", { name: /^propuesta to-be$/i })).toBeInTheDocument();
  expect(documentos()).toHaveLength(1);
});

it("al recargar con el Diccionario ya subido, abre en el TO-BE", async () => {
  const { leerGenerados } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue({ ...listo,
    diccionario: { ...conVista, decision: "declinada" }, insumos: { diccionario: true, tobe: false } });
  render(<Propuestas sid={SID} onListo={() => {}} />);
  expect(await screen.findByText("TO-BE (2 de 2)")).toBeInTheDocument();
});

it("cuando la decision devuelve el expediente, entra al wizard por onListo", async () => {
  const { leerGenerados, decidirDocumento } = await import("@/lib/api");
  vi.mocked(leerGenerados).mockResolvedValue({ ...listo,
    diccionario: { ...conVista, decision: "aceptada" }, insumos: { diccionario: true, tobe: false } });
  const est = { sid: SID, manifiesto: {}, huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false };
  vi.mocked(decidirDocumento).mockResolvedValueOnce({ tipo: "expediente", estado: est });
  const onListo = vi.fn();
  render(<Propuestas sid={SID} onListo={onListo} />);
  await userEvent.click(await screen.findByRole("button", { name: /aceptar tal cual/i }));
  await waitFor(() => expect(onListo).toHaveBeenCalledWith(est));
});

it("422 con los dos resueltos: muestra las dos zonas de carga", async () => {
  // El servidor guarda `aceptada` ANTES de que el extractor conteste 422; se
  // relee, y con los dos resueltos hay que poder subir encima de cualquiera.
  const { leerGenerados, decidirDocumento, ErrorApi } = await import("@/lib/api");
  const soloDicc = { ...listo, diccionario: { ...conVista, decision: "aceptada" as const },
    insumos: { diccionario: true, tobe: false } };
  vi.mocked(leerGenerados)
    .mockResolvedValueOnce(soloDicc)
    .mockResolvedValueOnce({ ...soloDicc, tobe: { ...doc, version_prompt: "tobe-v1", decision: "aceptada" },
      insumos: { diccionario: true, tobe: true } });
  const e = new (ErrorApi as any)("no se extrajo ninguna pantalla"); e.status = 422;
  vi.mocked(decidirDocumento).mockRejectedValue(e);
  render(<Propuestas sid={SID} onListo={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: /aceptar tal cual/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se extrajo ninguna pantalla/);
  expect(await screen.findByLabelText(/subir mi diccionario/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/subir mi to-be/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /aceptar tal cual/i })).not.toBeInTheDocument();
});

it("un fallo pasajero al consultar no detiene la consulta periodica", async () => {
  const { leerGenerados } = await import("@/lib/api");
  vi.mocked(leerGenerados)
    .mockResolvedValueOnce({ estado: "generando", motivo: null, nombre: "Constancia", diccionario: null, tobe: null })
    .mockRejectedValueOnce(new Error("red"))
    .mockResolvedValueOnce(listo);
  render(<Propuestas sid={SID} onListo={() => {}} />);
  expect(await screen.findByText(/uno o dos minutos/i)).toBeInTheDocument();
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  await waitFor(() => expect(documentos()).toHaveLength(1));
});
