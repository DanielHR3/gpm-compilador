import { expect, it } from "vitest";

import { resumenEnPalabras } from "./resumen";

const BASE = {
  total_tramites: 10,
  requisitos: [
    { nombre: "Comprobante de Pago", tramites: 4, porcentaje: 40 },
    { nombre: "Tarjeta de Circulación", tramites: 4, porcentaje: 40 },
    { nombre: "Acta Constitutiva", tramites: 2, porcentaje: 20 },
  ],
  huecos: [{ codigo: "META-05", tramites: 9, total: 9 }],
  niveles: [{ nivel: "Complejo", tramites: 6 }, { nivel: "Medio", tramites: 3 }, { nivel: "Bajo", tramites: 1 }],
};

it("cuenta en palabras lo que mas se repite, el pendiente mas comun y cuantos son complejos", () => {
  const frases = resumenEnPalabras(BASE);
  expect(frases[0]).toBe("Los documentos que más se repiten son Comprobante de Pago y Tarjeta de Circulación.");
  expect(frases[1]).toBe("El pendiente más común es «Homoclave»: aparece en 9 de 10 trámites.");
  expect(frases[2]).toBe("6 de 10 trámites son complejos.");
});

it("con un solo tramite o sin repetidos no inventa comparaciones", () => {
  const frases = resumenEnPalabras({
    total_tramites: 1,
    requisitos: [{ nombre: "Acta", tramites: 1, porcentaje: 100 }],
    huecos: [],
    niveles: [{ nivel: "Bajo", tramites: 1 }],
  });
  expect(frases).toEqual(["Todavía hay un solo trámite: las comparaciones aparecen cuando haya dos o más."]);
});

it("sin tramites no dice nada", () => {
  expect(resumenEnPalabras({ total_tramites: 0, requisitos: [], huecos: [], niveles: [] })).toEqual([]);
});
