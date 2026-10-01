// frontend/src/features/comparativa/ComparativaAgente.test.tsx
// La comparativa que llega completa: el agente propone la evidencia de los
// lados vacios y los puntos de mejora (spec 2026-10-01).
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  leerComparativa: vi.fn(),
  declararMetrica: vi.fn(),
  analizarComparativa: vi.fn(),
  descartarMejora: vi.fn(),
}));
vi.mock("@/lib/api", () => ({
  ...api,
  urlDocumentoComparativa: (sid: string) => `/api/v1/expedientes/${sid}/comparativa/documento`,
}));

import Comparativa from "./Comparativa";

const SID = "b".repeat(16);
const valor = (texto: string, origen: string) => ({
  texto, numero: texto && /^\d+$/.test(texto) ? Number(texto) : null, unidad: "", origen,
});
const analisis = (estado: string, mas: object = {}) => ({
  estado, motivo: null, pasos: [], puede_analizar: true, motivo_analizar: null,
  pruebas: false, modelo: "", terminado: null, ...mas,
});
const VACIA = {
  clave: "visitas", nombre: "Visitas presenciales", antes: valor("", "sin_dato"),
  despues: valor("", "sin_dato"), diferencia: null, porcentaje: null,
  propuesta_antes: null, propuesta_despues: null,
};
const PROPUESTA = {
  ...VACIA, antes: valor("2", "propuesto"), despues: valor("0", "propuesto"),
  diferencia: 2, porcentaje: 100,
  propuesta_antes: {
    motivo: "El ciudadano va dos veces en persona.", ninguno: false,
    evidencia: [
      { nombre: "Ir a ventanilla", cita: "Usuario lo lleva a Ventanilla" },
      { nombre: "Ir al banco", cita: "Usuario recibe el F7 y paga (en banco)" },
    ],
  },
  propuesta_despues: {
    motivo: "Todo se resuelve en línea.", ninguno: true,
    evidencia: [{ nombre: "Ninguna", cita: "no queda ninguna visita presencial residual" }],
  },
};
const MEJORA = {
  id: "abc123", titulo: "Quitar la tarjeta de circulación", tipo: "documento",
  propuesta: "Consultarla en el padrón vehicular.", beneficio: "El ciudadano se ahorra un escaneo.",
  cita: "Se adjunta en formato digital PDF", fuente: "to_be", campo: "doc_tarjeta",
  etiqueta_campo: "Tarjeta de Circulación", servicio: "", requiere: "convenio", descartada: false,
};
const BASE = {
  disponible: true, motivo: "", tramite: "Reposición de Certificado", documentos: null,
  metricas: [
    { clave: "pasos", nombre: "Pasos del proceso", antes: valor("10", "contado"),
      despues: valor("4", "contado"), diferencia: 6, porcentaje: 60,
      propuesta_antes: null, propuesta_despues: null },
    VACIA,
  ],
  requisitos: [], pasos_antes: [], tareas_despues: [], fricciones: [], cambios: [],
  eliminaciones: [], impacto: [], autollenados: 0, porcentaje_global: null, base_global: 1,
  total_metricas: 7, veredicto: "sin_medida", frase: "No se puede medir.", huecos: [],
  elementos: [], resumen_elementos: null, resumen: [], mejoras: [],
  analisis: analisis("sin_analizar"),
};
const COMPLETA = {
  ...BASE, metricas: [BASE.metricas[0], PROPUESTA], porcentaje_global: 80, base_global: 2,
  veredicto: "reduce", frase: "La reingeniería reduce.", mejoras: [MEJORA],
  analisis: analisis("lista", { modelo: "gemini-x", terminado: "2026-10-01T18:00:00+00:00" }),
};

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
});
afterEach(() => {
  vi.useRealTimers();
});

it("la primera vez lanza el análisis sola y la página se completa", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  api.leerComparativa
    .mockResolvedValueOnce(BASE)
    .mockResolvedValueOnce({ ...BASE, analisis: analisis("analizando", {
      pasos: [{ t: "1", mensaje: "Leyendo el AS-IS y el TO-BE" }] }) })
    .mockResolvedValue(COMPLETA);
  api.analizarComparativa.mockResolvedValue({ estado: "analizando" });
  render(<Comparativa sid={SID} />);

  const estado = await screen.findByRole("status");
  expect(estado).toHaveTextContent(/el agente está completando la comparativa/i);
  expect(estado).toHaveTextContent("Leyendo el AS-IS y el TO-BE");
  expect(api.analizarComparativa).toHaveBeenCalledTimes(1);
  expect(api.analizarComparativa).toHaveBeenCalledWith(SID);

  await act(async () => {
    await vi.advanceTimersByTimeAsync(2600);
  });
  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(tarjeta).toHaveTextContent("propuesto por el agente");
  expect(tarjeta).toHaveTextContent("−100 %");
  expect(api.analizarComparativa).toHaveBeenCalledTimes(1);
});

it("con el análisis ya hecho no lo vuelve a lanzar", async () => {
  api.leerComparativa.mockResolvedValue(COMPLETA);
  render(<Comparativa sid={SID} />);

  await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(api.analizarComparativa).not.toHaveBeenCalled();
  expect(screen.queryByRole("status")).toBeNull();
});

it("una cifra propuesta enseña su motivo y las frases en que se apoya", async () => {
  api.leerComparativa.mockResolvedValue(COMPLETA);
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(tarjeta).toHaveTextContent("El ciudadano va dos veces en persona.");
  expect(within(tarjeta).getByText(/ver las 2 frases de antes/i)).toBeInTheDocument();
  expect(tarjeta).toHaveTextContent("«Usuario lo lleva a Ventanilla»");
  expect(tarjeta).toHaveTextContent("Ir al banco");
  // Un cero propuesto dice que frase lo afirma.
  expect(within(tarjeta).getByText(/ver la frase de después/i)).toBeInTheDocument();
  expect(tarjeta).toHaveTextContent("«no queda ninguna visita presencial residual»");
  // Lo propuesto se puede corregir a mano, como lo contado.
  expect(within(tarjeta).getByRole("button", { name: /corregir/i })).toBeInTheDocument();
  expect(within(tarjeta).queryByLabelText(/antes/i)).toBeNull();
});

it("sin agente disponible la página queda como antes y lo dice", async () => {
  api.leerComparativa.mockResolvedValue({ ...BASE, analisis: analisis("sin_analizar", {
    puede_analizar: false, motivo_analizar: "No hay un proveedor de IA configurado en el servidor." }) });
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(api.analizarComparativa).not.toHaveBeenCalled();
  expect(screen.getByText(/no hay un proveedor de ia configurado/i)).toBeInTheDocument();
  expect(within(tarjeta).getByLabelText(/antes/i)).toBeInTheDocument();
});

it("mientras el agente trabaja, un lado vacío no pide que lo capturen", async () => {
  api.leerComparativa.mockResolvedValue({ ...BASE, analisis: analisis("analizando") });
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(tarjeta).toHaveTextContent(/el agente está buscando este dato/i);
  expect(within(tarjeta).queryByLabelText(/antes/i)).toBeNull();
});

it("lo que el agente no encontró se puede escribir a mano", async () => {
  api.leerComparativa.mockResolvedValue({ ...BASE, analisis: analisis("lista") });
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(tarjeta).toHaveTextContent(/el expediente no trae evidencia de este dato/i);
  expect(within(tarjeta).getByLabelText(/antes/i)).toBeInTheDocument();
});

it("si el análisis falla lo dice, deja lo contado y ofrece reintentar", async () => {
  api.leerComparativa.mockResolvedValue({ ...BASE, analisis: analisis("error", {
    motivo: "No se pudo consultar al modelo (red o cuota)." }) });
  api.analizarComparativa.mockResolvedValue({ estado: "analizando" });
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo consultar al modelo/i);
  expect(screen.getByRole("article", { name: "Pasos del proceso" })).toHaveTextContent("10");
  expect(api.analizarComparativa).not.toHaveBeenCalled();
  await usuario.click(screen.getByRole("button", { name: /volver a analizar/i }));
  expect(api.analizarComparativa).toHaveBeenCalledWith(SID);
});

it("en modo de pruebas avisa a dónde viajan los documentos", async () => {
  api.leerComparativa.mockResolvedValue({ ...COMPLETA, analisis: analisis("lista", { pruebas: true }) });
  render(<Comparativa sid={SID} />);

  expect(await screen.findByText(/modo de pruebas/i)).toHaveTextContent(/gemini/i);
});

it("dice en palabras qué bajó, qué quedó igual y qué falta", async () => {
  api.leerComparativa.mockResolvedValue({ ...COMPLETA, resumen: [
    { clase: "elementos", texto: "De los 9 elementos del trámite actual que revisó el equipo, 5 se eliminan." },
    { clase: "baja", texto: "Baja: visitas presenciales, de 2 a 0." },
    { clase: "sin_dato", texto: "Sin dato en el expediente: capturas manuales del mismo dato." },
  ] });
  render(<Comparativa sid={SID} />);

  const resumen = await screen.findByRole("list", { name: /en pocas palabras/i });
  expect(within(resumen).getAllByRole("listitem")).toHaveLength(3);
  expect(resumen).toHaveTextContent("Baja: visitas presenciales, de 2 a 0.");
});

it("enseña qué pasó con cada elemento del trámite, con la palabra del equipo", async () => {
  api.leerComparativa.mockResolvedValue({
    ...COMPLETA,
    elementos: [
      { nombre: "Paso 1. Solicitud de información", decision: "Sí",
        fundamento: "Se consulta en el sistema.", clase: "elimina", tipo: "paso" },
      { nombre: "Requisito: tarjeta de circulación", decision: "No, se conserva en digital",
        fundamento: "Identifica el vehículo.", clase: "conserva", tipo: "requisito" },
      { nombre: "Pasos 6A y 7B", decision: "Se reduce", fundamento: "", clase: "cambia", tipo: "paso" },
    ],
    resumen_elementos: { total: 3, elimina: 1, conserva: 1, cambia: 1, sin_decision: 0, otro: 0 },
  });
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("img", { name: /elementos del trámite por decisión/i })).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: "Se elimina: 1" })).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: "Cambia: 1" })).toBeInTheDocument();
  const tarjeta = screen.getByRole("article", { name: "Requisito: tarjeta de circulación" });
  expect(tarjeta).toHaveTextContent("No, se conserva en digital");
  expect(tarjeta).toHaveTextContent("Identifica el vehículo.");
  expect(screen.queryByRole("table")).toBeNull();
});

it("sin tabla de eliminación ni mejoras no inventa secciones", async () => {
  api.leerComparativa.mockResolvedValue({ ...COMPLETA, mejoras: [] });
  render(<Comparativa sid={SID} />);

  await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(screen.queryByRole("heading", { name: /qué pasó con cada elemento/i })).toBeNull();
  expect(screen.queryByRole("heading", { name: /qué más se puede simplificar/i })).toBeNull();
});

it("un punto de mejora trae propuesta, beneficio y evidencia, y se puede descartar", async () => {
  api.leerComparativa.mockResolvedValue(COMPLETA);
  api.descartarMejora.mockResolvedValue({ ...COMPLETA, mejoras: [{ ...MEJORA, descartada: true }] });
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("heading", { name: /qué más se puede simplificar/i })).toBeInTheDocument();
  const tarjeta = screen.getByRole("article", { name: "Quitar la tarjeta de circulación" });
  expect(tarjeta).toHaveTextContent("Consultarla en el padrón vehicular.");
  expect(tarjeta).toHaveTextContent("El ciudadano se ahorra un escaneo.");
  expect(tarjeta).toHaveTextContent("Tarjeta de Circulación");
  expect(tarjeta).toHaveTextContent("«Se adjunta en formato digital PDF»");
  expect(tarjeta).toHaveTextContent(/requiere un convenio/i);

  await usuario.click(within(tarjeta).getByRole("button", { name: /descartar/i }));
  expect(api.descartarMejora).toHaveBeenCalledWith(SID, "abc123", true);
  const descartada = await screen.findByRole("article", { name: "Quitar la tarjeta de circulación" });
  expect(descartada).toHaveTextContent(/descartado/i);
  expect(within(descartada).getByRole("button", { name: /restaurar/i })).toBeInTheDocument();
});

it("un punto descartado se puede restaurar", async () => {
  api.leerComparativa.mockResolvedValue({ ...COMPLETA, mejoras: [{ ...MEJORA, descartada: true }] });
  api.descartarMejora.mockResolvedValue(COMPLETA);
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Quitar la tarjeta de circulación" });
  await usuario.click(within(tarjeta).getByRole("button", { name: /restaurar/i }));
  expect(api.descartarMejora).toHaveBeenCalledWith(SID, "abc123", false);
});

it("si descartar falla lo dice y la tarjeta sigue ahí", async () => {
  api.leerComparativa.mockResolvedValue(COMPLETA);
  api.descartarMejora.mockRejectedValue(new Error("sin red"));
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Quitar la tarjeta de circulación" });
  await usuario.click(within(tarjeta).getByRole("button", { name: /descartar/i }));
  expect(await within(tarjeta).findByRole("alert")).toHaveTextContent(/no se pudo guardar/i);
});

it("tras un fallo no afirma que el expediente no trae el dato", async () => {
  api.leerComparativa.mockResolvedValue({ ...BASE, analisis: analisis("error", { motivo: "Falló." }) });
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  expect(tarjeta).not.toHaveTextContent(/no trae evidencia/i);
  expect(within(tarjeta).getByLabelText(/antes/i)).toBeInTheDocument();
});
