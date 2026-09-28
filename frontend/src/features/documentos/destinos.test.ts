// frontend/src/features/documentos/destinos.test.ts
import { expect, it } from "vitest";

import { DESTINOS, ORDEN, colorDe, estadoEnPalabras, nombreDe, veredictoEnPalabras } from "./destinos";

it("los destinos van en orden fijo, primero lo que se dejó de pedir", () => {
  expect(ORDEN).toEqual(["elimina", "consulta", "sistema", "conserva", "sin_destino"]);
  expect(DESTINOS).toEqual(["elimina", "consulta", "sistema", "conserva"]);
});

it("cada destino tiene nombre y color propios", () => {
  expect(nombreDe("elimina")).toBe("Se elimina");
  expect(nombreDe("consulta")).toBe("Se sustituye por consulta en línea");
  expect(nombreDe("sistema")).toBe("Lo genera el sistema");
  expect(nombreDe("conserva")).toBe("Se conserva");
  expect(nombreDe("sin_destino")).toBe("Sin destino");
  expect(new Set(ORDEN.map(colorDe)).size).toBe(5);
  expect(colorDe("elimina")).toBe("var(--dest-elimina)");
});

it("dice el estado y el veredicto en palabras", () => {
  expect(estadoEnPalabras("propuesto")).toBe("Propuesto, sin revisar");
  expect(estadoEnPalabras("corregido")).toBe("Corregido por una persona");
  expect(veredictoEnPalabras("cita_inventada")).toMatch(/no está en el TO-BE/i);
  expect(veredictoEnPalabras("omitido_por_el_modelo")).toMatch(/el agente no lo revisó/i);
  expect(veredictoEnPalabras("campo_desaparecido")).toMatch(/ya no existe/i);
  expect(veredictoEnPalabras("")).toBe("");
  // Uno que nadie tradujo se enseña tal cual, no desaparece.
  expect(veredictoEnPalabras("algo_nuevo")).toBe("algo_nuevo");
});
