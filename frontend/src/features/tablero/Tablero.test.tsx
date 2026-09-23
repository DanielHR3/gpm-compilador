import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

const leerTablero = vi.fn();
vi.mock("@/lib/api", () => ({
  leerTablero: (...a: unknown[]) => leerTablero(...a),
}));

import Tablero from "./Tablero";

const DATOS = {
  total_tramites: 3,
  dependencias: [{ nombre: "SEMARNATH", tramites: 2 }, { nombre: "IIFEH", tramites: 1 }],
  ultimo_registro: "2026-09-23T18:00:00+00:00",
  requisitos: [{ nombre: "Identificación Oficial", tramites: 2, porcentaje: 67 }],
  campos_compartidos: [{ nombre: "curp", tramites: 3, porcentaje: 100 }],
  huecos: [{ codigo: "DIC-08", tramites: 2, total: 21 }],
  complejidad: [
    { clave: "testamento", nombre: "Testamento", dependencia: "IIFEH", nivel: "Alto",
      metricas: { tareas: 10, bifurcaciones: 3, vistas: 9, campos: 46, acciones: 2, integraciones: 1 } },
  ],
  catalogos: [{ clave: "mgee", tramites: 2 }],
  actividad: [{ semana: "2026-W38", tramites: 1 }, { semana: "2026-W39", tramites: 2 }],
  indicadores: { requisitos_distintos: 1, promedio_campos: 23.5, promedio_huecos: 7.0, con_integracion: 2 },
  matriz_huecos: { filas: ["Testamento"], columnas: ["DIC-08"], celdas: [[21]], maximo: 21 },
  matriz_requisitos: { filas: ["Identificación Oficial"], columnas: ["Testamento"], celdas: [[1]], maximo: 0 },
  niveles: [{ nivel: "Alto", tramites: 1 }, { nivel: "Medio", tramites: 0 }, { nivel: "Bajo", tramites: 2 }],
  metricas_max: { tareas: 10, bifurcaciones: 3, vistas: 9, campos: 46, acciones: 2, integraciones: 1 },
};

beforeEach(() => {
  leerTablero.mockReset();
  leerTablero.mockResolvedValue(DATOS);
});

it("pinta las seis secciones en tarjetas y sin ninguna tabla", async () => {
  render(<Tablero />);
  expect(await screen.findByRole("heading", { name: /^tablero$/i })).toBeInTheDocument();
  expect(screen.getByText(/3 trámites de 2 dependencias/i)).toBeInTheDocument();
  for (const titulo of [
    /requisitos más repetidos/i, /se capturan en varios trámites/i, /se atoran/i,
    /complejidad por trámite/i, /integraciones/i, /actividad/i,
  ]) {
    expect(screen.getByRole("heading", { name: titulo })).toBeInTheDocument();
  }
  expect(screen.queryByRole("table")).toBeNull();
});

it("arriba va la fila de cifras y las secciones traen mapa de calor, matriz y distribucion", async () => {
  render(<Tablero />);
  expect(await screen.findByRole("article", { name: /^trámites$/i })).toHaveTextContent("3");
  expect(screen.getByRole("article", { name: /campos por trámite/i })).toHaveTextContent("23.5");
  expect(screen.getByRole("grid", { name: /inconsistencias por trámite/i })).toBeInTheDocument();
  expect(screen.getByRole("grid", { name: /requisitos por trámite/i })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: /nivel de complejidad/i })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: /trámites por semana/i })).toBeInTheDocument();
  // las tarjetas de complejidad comparan cada metrica con el maximo entre tramites
  const tarjeta = screen.getByRole("article", { name: /testamento/i });
  expect(within(tarjeta).getByRole("meter", { name: /campos/i })).toHaveAttribute("aria-valuenow", "46");
});

it("los huecos salen con su nombre humano, no solo el codigo", async () => {
  render(<Tablero />);
  const seccion = (await screen.findByRole("heading", { name: /se atoran/i })).closest("section")!;
  // La columna del mapa de calor lleva el nombre humano, no solo el codigo.
  expect(within(seccion).getByRole("columnheader", { name: /condición de visibilidad/i })).toBeInTheDocument();
});

it("la complejidad va en una tarjeta por trámite con su nivel y sus métricas", async () => {
  render(<Tablero />);
  const tarjeta = await screen.findByRole("article", { name: /testamento/i });
  expect(tarjeta).toHaveTextContent("Alto");
  expect(tarjeta).toHaveTextContent(/pasos\s*10/i);
  expect(tarjeta).toHaveTextContent(/campos\s*46/i);
  expect(screen.getByText(/no está calibrada/i)).toBeInTheDocument();
});

it("elegir una dependencia vuelve a pedir el tablero filtrado", async () => {
  render(<Tablero />);
  await screen.findByRole("heading", { name: /^tablero$/i });
  await userEvent.click(screen.getByRole("button", { name: /IIFEH/ }));
  expect(leerTablero).toHaveBeenLastCalledWith("IIFEH");
  await userEvent.click(screen.getByRole("button", { name: /todas/i }));
  expect(leerTablero).toHaveBeenLastCalledWith(undefined);
});

it("sin registros explica que se llena al extraer", async () => {
  leerTablero.mockResolvedValue({ ...DATOS, total_tramites: 0, dependencias: [], ultimo_registro: null,
    requisitos: [], campos_compartidos: [], huecos: [], complejidad: [], catalogos: [], actividad: [] });
  render(<Tablero />);
  expect(await screen.findByText(/se llena solo al extraer/i)).toBeInTheDocument();
});

it("si el servidor no contesta avisa", async () => {
  leerTablero.mockRejectedValue(new Error("red"));
  render(<Tablero />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo/i);
});
