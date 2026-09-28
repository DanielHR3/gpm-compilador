// frontend/src/features/documentos/Documentos.test.tsx
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const api = {
  leerDocumentos: vi.fn(),
  analizarDocumentos: vi.fn(),
  decidirDestino: vi.fn(),
  aceptarVerificados: vi.fn(),
};
vi.mock("@/lib/api", () => ({
  leerDocumentos: (...a: unknown[]) => api.leerDocumentos(...a),
  analizarDocumentos: (...a: unknown[]) => api.analizarDocumentos(...a),
  decidirDestino: (...a: unknown[]) => api.decidirDestino(...a),
  aceptarVerificados: (...a: unknown[]) => api.aceptarVerificados(...a),
  urlDescargaDocumentos: (sid: string) => `/api/v1/expedientes/${sid}/documentos/descarga`,
  ErrorApi: class ErrorApi extends Error {
    status = 409;
    error = "Hace falta la licencia.";
  },
}));

import Documentos from "./Documentos";

const SID = "a".repeat(16);
const doc = (nombre: string, destino: string, extra = {}) => ({
  id: nombre, nombre, cita_as_is: nombre.toLowerCase(), destino, campo: "", cita_to_be: "",
  motivo: "", motivo_de: "", confianza: "alta", veredicto: "", origen: "agente",
  estado: "propuesto", ...extra,
});
const ESTADO = {
  disponible: true, motivo: "", estado: "lista", motivo_estado: null, pasos: [], origen: "agente",
  documentos: [
    doc("Identificación oficial", "elimina", { cita_to_be: "La identificación se elimina" }),
    doc("Comprobante de domicilio", "conserva", { campo: "doc_comprobante" }),
    doc("Orden de trabajo", "sin_destino", { veredicto: "cita_inventada" }),
  ],
  resumen: {
    total: 3, decididos: 0, ya_no_se_piden: 0, solicitados: 0, completo: false, agregados: ["RFC"],
    titular: "Faltan 3 documentos por revisar.", simplificacion: [],
    por_destino: { elimina: 1, conserva: 1, consulta: 0, sistema: 0, sin_destino: 1 },
  },
  puede_analizar: true, motivo_analizar: null, pruebas: false,
};

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  api.leerDocumentos.mockResolvedValue(ESTADO);
});

afterEach(() => vi.useRealTimers());

it("pinta el titular, la barra y una columna por destino con sus tarjetas", async () => {
  render(<Documentos sid={SID} />);

  expect(await screen.findByRole("heading", { name: /documentos del trámite/i })).toBeInTheDocument();
  expect(screen.getByText("Faltan 3 documentos por revisar.")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: /documentos por destino/i })).toBeInTheDocument();
  const columna = screen.getByRole("region", { name: "Se elimina" });
  expect(within(columna).getByRole("article", { name: "Identificación oficial" })).toBeInTheDocument();
  expect(
    within(screen.getByRole("region", { name: "Sin destino" })).getByRole("article", {
      name: "Orden de trabajo",
    }),
  ).toBeInTheDocument();
  // Una columna vacia no se pinta.
  expect(screen.queryByRole("region", { name: "Lo genera el sistema" })).toBeNull();
  expect(screen.queryByRole("table")).toBeNull();
});

it("enseña aparte los documentos que el TO-BE agrega", async () => {
  render(<Documentos sid={SID} />);
  const agregados = await screen.findByRole("region", { name: /documentos que el TO-BE agrega/i });
  expect(within(agregados).getByText("RFC")).toBeInTheDocument();
});

it("decidir una tarjeta actualiza la página con lo que devuelve el servidor", async () => {
  api.decidirDestino.mockResolvedValue({
    ...ESTADO,
    documentos: ESTADO.documentos.map((d) =>
      d.id === "Identificación oficial" ? { ...d, estado: "aceptado" } : d),
    resumen: { ...ESTADO.resumen, decididos: 1, ya_no_se_piden: 1, solicitados: 0,
               titular: "De 1 documento revisado, 1 ya no se pide. Faltan 2 por revisar." },
  });
  render(<Documentos sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Identificación oficial" });
  await userEvent.click(within(tarjeta).getByRole("button", { name: /^aceptar/i }));

  expect(api.decidirDestino).toHaveBeenCalledWith(SID, "Identificación oficial", "elimina", "");
  expect(await screen.findByText(/De 1 documento revisado, 1 ya no se pide/)).toBeInTheDocument();
});

it("aceptar todo lo verificado es un solo botón y dice cuántos son", async () => {
  api.aceptarVerificados.mockResolvedValue(ESTADO);
  render(<Documentos sid={SID} />);

  await userEvent.click(await screen.findByRole("button", { name: /aceptar los 2 verificados/i }));
  expect(api.aceptarVerificados).toHaveBeenCalledWith(SID);
});

it("analizar pide el análisis y consulta hasta que termina", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  api.leerDocumentos
    .mockResolvedValueOnce({ ...ESTADO, estado: "sin_analizar", origen: "lector" })
    .mockResolvedValueOnce({ ...ESTADO, estado: "analizando",
                             pasos: [{ t: "2026-09-28T18:00:00Z", mensaje: "Leyendo el AS-IS y el TO-BE" }] })
    .mockResolvedValue(ESTADO);
  api.analizarDocumentos.mockResolvedValue({ estado: "analizando" });
  render(<Documentos sid={SID} />);

  await userEvent.click(await screen.findByRole("button", { name: /analizar documentos/i }));
  expect(api.analizarDocumentos).toHaveBeenCalledWith(SID);
  expect(await screen.findByText("Leyendo el AS-IS y el TO-BE")).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent(/analizando/i);

  await act(async () => {
    await vi.advanceTimersByTimeAsync(3100);
  });
  expect(await screen.findByRole("button", { name: /volver a analizar/i })).toBeInTheDocument();
});

it("con el candado cerrado lo dice y ofrece el camino a mano", async () => {
  api.leerDocumentos.mockResolvedValue({
    ...ESTADO, estado: "sin_analizar", origen: "lector", puede_analizar: false,
    motivo_analizar: "Hace falta la licencia de IA.",
  });
  render(<Documentos sid={SID} />);

  expect(await screen.findByText("Hace falta la licencia de IA.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /analizar documentos/i })).toBeNull();
  // Un selector por documento: el camino a mano sigue entero.
  expect(screen.getAllByRole("combobox", { name: /destino/i }).length).toBe(3);
});

it("en modo de pruebas avisa que los documentos viajan a Gemini", async () => {
  api.leerDocumentos.mockResolvedValue({ ...ESTADO, pruebas: true });
  render(<Documentos sid={SID} />);
  expect(await screen.findByText(/viajan a Gemini/i)).toBeInTheDocument();
});

it("si el análisis falló dice por qué y deja reintentar", async () => {
  api.leerDocumentos.mockResolvedValue({
    ...ESTADO, estado: "error", origen: "lector",
    motivo_estado: "No se pudo consultar al modelo (red o cuota).",
  });
  render(<Documentos sid={SID} />);

  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo consultar al modelo/i);
  expect(screen.getByRole("button", { name: /volver a analizar/i })).toBeInTheDocument();
});

it("sin AS-IS dice por qué y no pinta un tablero vacío", async () => {
  api.leerDocumentos.mockResolvedValue({
    ...ESTADO, disponible: false, motivo: "No se cargó el Análisis AS-IS en este expediente.",
    documentos: [],
  });
  render(<Documentos sid={SID} />);

  expect(await screen.findByText(/no se cargó el análisis as-is/i)).toBeInTheDocument();
  expect(screen.queryByRole("article")).toBeNull();
});

it("ofrece la descarga, el regreso y el paso a la comparativa", async () => {
  render(<Documentos sid={SID} />);

  expect(await screen.findByRole("link", { name: /descargar/i })).toHaveAttribute(
    "href", `/api/v1/expedientes/${SID}/documentos/descarga`);
  expect(screen.getByRole("link", { name: /volver a la revisión/i })).toHaveAttribute(
    "href", `/revisar/${SID}`);
  expect(screen.getByRole("link", { name: /ver antes y después/i })).toHaveAttribute(
    "href", `/revisar/${SID}/comparativa`);
});

it("si la sesión no existe lo dice", async () => {
  api.leerDocumentos.mockRejectedValue(new Error("404"));
  render(<Documentos sid={SID} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudieron abrir los documentos/i);
});

it("dice cómo se simplificó el trámite, nombrando los documentos", async () => {
  api.leerDocumentos.mockResolvedValue({
    ...ESTADO,
    resumen: {
      ...ESTADO.resumen,
      simplificacion: [
        { destino: "elimina", frase: "Se eliminaron",
          documentos: ["Identificación oficial", "Orden de trabajo"] },
        { destino: "conserva", frase: "Se conserva", documentos: ["Comprobante de domicilio"] },
      ],
    },
  });
  render(<Documentos sid={SID} />);

  const apartado = await screen.findByRole("region", { name: /cómo se simplificó el trámite/i });
  expect(within(apartado).getByRole("listitem", { name: "Se eliminaron" })).toHaveTextContent(
    "Identificación oficial, Orden de trabajo",
  );
  expect(within(apartado).getByRole("listitem", { name: "Se conserva" })).toHaveTextContent(
    "Comprobante de domicilio",
  );
});

it("sin nada decidido no afirma cómo se simplificó", async () => {
  render(<Documentos sid={SID} />);
  await screen.findByRole("heading", { name: /documentos del trámite/i });
  expect(screen.queryByRole("region", { name: /cómo se simplificó/i })).toBeNull();
});
