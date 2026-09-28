// frontend/src/features/comparativa/GraficaSimplificacion.test.tsx
import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import type { ComparativaOut, MetricaComparada } from "@/lib/types";

import GraficaSimplificacion from "./GraficaSimplificacion";

function metrica(clave: string, nombre: string, a: number | null, d: number | null, pct: number | null) {
  return {
    clave, nombre, diferencia: a !== null && d !== null ? a - d : null, porcentaje: pct,
    antes: { texto: a === null ? "" : String(a), numero: a, unidad: "", origen: a === null ? "sin_dato" : "contado" },
    despues: { texto: d === null ? "" : String(d), numero: d, unidad: "", origen: d === null ? "sin_dato" : "contado" },
  } as MetricaComparada;
}

function comparativa(metricas: MetricaComparada[], global: number | null): ComparativaOut {
  return {
    disponible: true, motivo: "", tramite: "T", metricas, requisitos: [], pasos_antes: [],
    tareas_despues: [], fricciones: [], cambios: [], eliminaciones: [], impacto: [],
    autollenados: 0, porcentaje_global: global,
    base_global: metricas.filter((m) => m.porcentaje !== null).length,
    total_metricas: 7, veredicto: global === null ? "sin_medida" : "reduce", frase: "", huecos: [], documentos: null,
  };
}

it("pinta una pareja de barras por métrica comparable, con su valor escrito", () => {
  render(
    <GraficaSimplificacion
      comparativa={comparativa(
        [metrica("requisitos", "Requisitos documentales", 5, 3, 40),
         metrica("pasos", "Pasos del proceso", 19, 8, 57.9),
         metrica("visitas", "Visitas presenciales", null, null, null)],
        49,
      )}
    />,
  );

  expect(screen.getByText("49 % sobre 2 de 7 métricas")).toBeInTheDocument();
  const fila = screen.getByRole("listitem", { name: /requisitos documentales/i });
  expect(within(fila).getByRole("meter", { name: /antes/i })).toHaveAttribute("aria-valuenow", "5");
  expect(within(fila).getByRole("meter", { name: /después/i })).toHaveAttribute("aria-valuenow", "3");
  expect(fila).toHaveTextContent("−40 %");
  expect(screen.queryByRole("listitem", { name: /visitas/i })).toBeNull();
  expect(screen.queryByRole("table")).toBeNull();
});

it("una métrica que sube se enseña, no se esconde", () => {
  render(<GraficaSimplificacion comparativa={comparativa(
    [metrica("pasos", "Pasos del proceso", 1, 3, -200),
     metrica("requisitos", "Requisitos documentales", 4, 2, 50)], -75)} />);

  expect(screen.getByRole("listitem", { name: /pasos del proceso/i })).toHaveTextContent("+200 %");
});

it("sin métricas comparables dice qué falta en vez de una gráfica vacía", () => {
  render(<GraficaSimplificacion comparativa={comparativa(
    [metrica("visitas", "Visitas presenciales", null, null, null)], null)} />);

  expect(screen.getByText(/sin cifra global/i)).toBeInTheDocument();
  expect(screen.queryByRole("meter")).toBeNull();
});
