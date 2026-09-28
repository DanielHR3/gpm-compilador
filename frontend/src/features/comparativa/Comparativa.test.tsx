// frontend/src/features/comparativa/Comparativa.test.tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

const leerComparativa = vi.fn();
const declararMetrica = vi.fn();
vi.mock("@/lib/api", () => ({
  leerComparativa: (...a: unknown[]) => leerComparativa(...a),
  declararMetrica: (...a: unknown[]) => declararMetrica(...a),
  urlDocumentoComparativa: (sid: string) => `/api/v1/expedientes/${sid}/comparativa/documento`,
}));

import Comparativa from "./Comparativa";

const SID = "a".repeat(16);
const valor = (texto: string, origen: string) => ({
  texto, numero: texto && /^\d+$/.test(texto) ? Number(texto) : null, unidad: "", origen,
});
const DATOS = {
  disponible: true, motivo: "", tramite: "Alta de Avisos de Testamento", documentos: null,
  metricas: [
    { clave: "requisitos", nombre: "Requisitos documentales", antes: valor("5", "contado"),
      despues: valor("3", "contado"), diferencia: 2, porcentaje: 40 },
    { clave: "pasos", nombre: "Pasos del proceso", antes: valor("19", "contado"),
      despues: valor("8", "contado"), diferencia: 11, porcentaje: 57.9 },
    { clave: "visitas", nombre: "Visitas presenciales", antes: valor("", "sin_dato"),
      despues: valor("", "sin_dato"), diferencia: null, porcentaje: null },
  ],
  requisitos: [
    { nombre: "identificación oficial", destino: "conservado", fundamento: "Identificación Oficial" },
    { nombre: "orden de trabajo", destino: "sin_destino", fundamento: "" },
  ],
  pasos_antes: ["El Notario entrega el formato", "Oficialía genera el F7"],
  tareas_despues: [{ nombre: "Nueva Solicitud", actor: "ciudadano" }],
  fricciones: ["Doble transcripción del mismo dato"],
  cambios: ["Captura 100% a distancia"],
  eliminaciones: ["El Excel para oficios se elimina por completo"],
  impacto: ["Elimina cualquier traslado físico"],
  autollenados: 3, porcentaje_global: 49, base_global: 2, total_metricas: 7,
  veredicto: "reduce", frase: "La reingeniería reduce: requisitos documentales de 5 a 3 (−40 %).",
  huecos: [{ nivel: "por_confirmar", codigo: "CMP-02", ubicacion: "to_be",
             mensaje: "Falta el dato del después para: Visitas presenciales.", propuesta: null }],
};

beforeEach(() => {
  leerComparativa.mockReset();
  declararMetrica.mockReset();
  leerComparativa.mockResolvedValue(DATOS);
});

it("pinta veredicto, gráfica y una tarjeta por métrica, sin ninguna tabla", async () => {
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("heading", { name: /antes y después/i })).toBeInTheDocument();
  expect(leerComparativa).toHaveBeenCalledWith(SID);
  expect(screen.getByText("Reduce")).toBeInTheDocument();
  expect(screen.getByText(/la reingeniería reduce: requisitos/i)).toBeInTheDocument();
  expect(screen.getByText("49 % sobre 2 de 7 métricas")).toBeInTheDocument();
  const tarjeta = screen.getByRole("article", { name: "Requisitos documentales" });
  expect(tarjeta).toHaveTextContent("5");
  expect(tarjeta).toHaveTextContent("3");
  expect(tarjeta).toHaveTextContent("contado");
  expect(tarjeta).toHaveTextContent("−40 %");
  expect(screen.queryByRole("table")).toBeNull();
});

it("un requisito sin destino no se rotula como eliminado", async () => {
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "orden de trabajo" });
  expect(tarjeta).toHaveTextContent("Sin destino");
  expect(tarjeta).not.toHaveTextContent(/se elimina/i);
});

it("enseña los pasos de antes, las tareas de después y la palabra del equipo", async () => {
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("article", { name: "Paso 1 de antes" })).toHaveTextContent(
    "El Notario entrega el formato",
  );
  expect(screen.getByRole("article", { name: "Tarea 1 de después" })).toHaveTextContent(
    "Nueva Solicitud",
  );
  expect(screen.getByText("Doble transcripción del mismo dato")).toBeInTheDocument();
  expect(screen.getByText(/estimación cualitativa del equipo/i)).toBeInTheDocument();
  expect(screen.getByText(/falta el dato del después/i)).toBeInTheDocument();
});

it("una métrica sin dato se captura en su tarjeta y la vista se recalcula", async () => {
  declararMetrica.mockResolvedValue({
    ...DATOS,
    metricas: DATOS.metricas.map((m) =>
      m.clave === "visitas"
        ? { ...m, antes: valor("2", "declarado"), despues: valor("0", "declarado"),
            diferencia: 2, porcentaje: 100 }
        : m),
    porcentaje_global: 66, base_global: 3,
  });
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  await usuario.type(within(tarjeta).getByLabelText(/antes/i), "2");
  await usuario.type(within(tarjeta).getByLabelText(/después/i), "0");
  await usuario.click(within(tarjeta).getByRole("button", { name: /guardar/i }));

  expect(declararMetrica).toHaveBeenCalledWith(SID, "visitas", "2", "0");
  expect(await screen.findByText("66 % sobre 3 de 7 métricas")).toBeInTheDocument();
  expect(screen.getByRole("article", { name: "Visitas presenciales" })).toHaveTextContent("declarado");
});

it("si guardar falla lo dice y conserva lo escrito", async () => {
  declararMetrica.mockRejectedValue(new Error("sin red"));
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  await usuario.type(within(tarjeta).getByLabelText(/después/i), "0");
  await usuario.click(within(tarjeta).getByRole("button", { name: /guardar/i }));

  expect(await within(tarjeta).findByRole("alert")).toHaveTextContent(/no se pudo guardar/i);
  expect(within(tarjeta).getByLabelText(/después/i)).toHaveValue("0");
});

it("ofrece el documento y el regreso a la revisión", async () => {
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("link", { name: /descargar documento/i })).toHaveAttribute(
    "href", `/api/v1/expedientes/${SID}/comparativa/documento`,
  );
  expect(screen.getByRole("link", { name: /volver a la revisión/i })).toHaveAttribute(
    "href", `/revisar/${SID}`,
  );
});

it("sin AS-IS dice por qué y no pinta ceros", async () => {
  leerComparativa.mockResolvedValue({
    ...DATOS, disponible: false, motivo: "No se cargó el Análisis AS-IS en este expediente.",
    metricas: [], requisitos: [],
  });
  render(<Comparativa sid={SID} />);

  expect(await screen.findByText(/no se cargó el análisis as-is/i)).toBeInTheDocument();
  expect(screen.queryByRole("article")).toBeNull();
  expect(screen.queryByRole("link", { name: /descargar documento/i })).toBeNull();
});

it("si la sesión no existe lo dice", async () => {
  leerComparativa.mockRejectedValue(new Error("404"));
  render(<Comparativa sid={SID} />);

  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo abrir la comparativa/i);
});

// --- Hallazgos de la revision de la rama (2026-09-28) ---------------------------

it("una cifra contada se puede corregir: el formulario sale al pedirlo", async () => {
  declararMetrica.mockResolvedValue(DATOS);
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Pasos del proceso" });
  expect(within(tarjeta).queryByLabelText(/antes/i)).toBeNull();
  await usuario.click(within(tarjeta).getByRole("button", { name: /corregir/i }));
  await usuario.type(within(tarjeta).getByLabelText(/antes/i), "7");
  await usuario.click(within(tarjeta).getByRole("button", { name: /guardar/i }));

  expect(declararMetrica).toHaveBeenCalledWith(SID, "pasos", "7", "");
});

it("lo declarado se puede quitar dejando los dos campos en blanco", async () => {
  const declarada = {
    ...DATOS,
    metricas: DATOS.metricas.map((m) =>
      m.clave === "visitas"
        ? { ...m, antes: valor("2", "declarado"), despues: valor("0", "declarado"),
            diferencia: 2, porcentaje: 100 }
        : m),
  };
  leerComparativa.mockResolvedValue(declarada);
  declararMetrica.mockResolvedValue(DATOS);
  const usuario = userEvent.setup();
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Visitas presenciales" });
  await usuario.clear(within(tarjeta).getByLabelText(/antes/i));
  await usuario.clear(within(tarjeta).getByLabelText(/después/i));
  await usuario.click(within(tarjeta).getByRole("button", { name: /guardar/i }));

  expect(declararMetrica).toHaveBeenCalledWith(SID, "visitas", "", "");
});

it("con número en los dos lados y sin porcentaje dice por qué no se compara", async () => {
  leerComparativa.mockResolvedValue({
    ...DATOS,
    metricas: [
      { clave: "tiempo", nombre: "Tiempo de respuesta",
        antes: { texto: "13 días hábiles", numero: 13, unidad: "dia habil", origen: "leido" },
        despues: { texto: "24 horas", numero: 24, unidad: "hora", origen: "declarado" },
        diferencia: null, porcentaje: null },
    ],
  });
  render(<Comparativa sid={SID} />);

  const tarjeta = await screen.findByRole("article", { name: "Tiempo de respuesta" });
  expect(tarjeta).toHaveTextContent(/no se compara: las unidades no coinciden/i);
});
it("con los documentos revisados enseña su titular y enlaza a la página", async () => {
  leerComparativa.mockResolvedValue({
    ...DATOS,
    requisitos: [],
    documentos: {
      total: 3, decididos: 3, ya_no_se_piden: 2, completo: true, agregados: [],
      titular: "De 3 documentos que pedía el trámite, 2 ya no se piden.",
      simplificacion: [{ destino: "elimina", frase: "Se eliminó", documentos: ["Orden de trabajo"] }],
      por_destino: { elimina: 1, conserva: 1, consulta: 1, sistema: 0, sin_destino: 0 },
    },
  });
  render(<Comparativa sid={SID} />);

  expect(
    await screen.findByText("De 3 documentos que pedía el trámite, 2 ya no se piden."),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /ver documentos del trámite/i })).toHaveAttribute(
    "href", `/revisar/${SID}/documentos`);
  expect(screen.getByText(/Se eliminó:/)).toBeInTheDocument();
  expect(screen.getByText(/Orden de trabajo/)).toBeInTheDocument();
});

it("sin documentos revisados invita a revisarlos", async () => {
  render(<Comparativa sid={SID} />);
  expect(await screen.findByRole("link", { name: /ver documentos del trámite/i })).toBeInTheDocument();
});
