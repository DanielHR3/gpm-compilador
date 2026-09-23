import { expect, it } from "vitest";

import { PASOS, pasoDe } from "./escala";

it("cinco pasos de la rampa guinda validada; cero queda fuera de la rampa", () => {
  expect(PASOS).toBe(5);
  expect(pasoDe(0, 20)).toBe(0);          // sin dato: no pinta
  expect(pasoDe(1, 20)).toBe(1);          // el minimo con dato ya se ve
  expect(pasoDe(20, 20)).toBe(5);         // el maximo, el mas oscuro
  expect(pasoDe(10, 20)).toBe(3);
  expect(pasoDe(1, 1)).toBe(5);           // un solo valor: el mas oscuro
  expect(pasoDe(3, 0)).toBe(0);           // sin maximo no hay escala
});
