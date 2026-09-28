// frontend/src/features/comparativa/formato.test.ts
import { expect, it } from "vitest";

import type { ComparativaOut } from "@/lib/types";

import {
  anchoBarra, etiquetaDestino, etiquetaOrigen, textoCambio, textoGlobal, tituloVeredicto,
} from "./formato";

const BASE = {
  disponible: true, motivo: "", tramite: "T", metricas: [], requisitos: [],
  pasos_antes: [], tareas_despues: [], fricciones: [], cambios: [], eliminaciones: [],
  impacto: [], autollenados: 0, porcentaje_global: 47.5, base_global: 3,
  total_metricas: 7, veredicto: "reduce", frase: "", huecos: [],
} as ComparativaOut;

it("una reducción va con signo menos y un aumento con más", () => {
  expect(textoCambio(40)).toBe("−40 %");
  expect(textoCambio(-200)).toBe("+200 %");
  expect(textoCambio(76.9)).toBe("−76.9 %");
  expect(textoCambio(0)).toBe("−0 %");
});

it("nombra el origen y el destino en castellano", () => {
  expect(etiquetaOrigen("leido")).toBe("leído");
  expect(etiquetaOrigen("sin_dato")).toBe("sin dato");
  expect(etiquetaDestino("sin_destino")).toBe("Sin destino");
  expect(etiquetaDestino("nuevo")).toBe("Nuevo en el TO-BE");
});

it("titula los cuatro veredictos", () => {
  expect(tituloVeredicto("reduce")).toBe("Reduce");
  expect(tituloVeredicto("sin_medida")).toBe("No se puede medir");
});

it("la cifra global va siempre con su base", () => {
  expect(textoGlobal(BASE)).toBe("47.5 % sobre 3 de 7 métricas");
  expect(textoGlobal({ ...BASE, porcentaje_global: null, base_global: 1 })).toBe(
    "Sin cifra global: solo 1 de 7 métricas se pueden comparar",
  );
});

it("una barra nunca desaparece ni se sale", () => {
  expect(anchoBarra(5, 10)).toBe(50);
  expect(anchoBarra(0, 10)).toBe(1);
  expect(anchoBarra(12, 10)).toBe(100);
  expect(anchoBarra(3, 0)).toBe(1);
});

it("una cifra global negativa dice que es aumento neto", () => {
  expect(textoGlobal({ ...BASE, porcentaje_global: -26.3, base_global: 2 })).toBe(
    "−26.3 % (aumento neto) sobre 2 de 7 métricas",
  );
});
