import { expect, it } from "vitest";

import type { Hueco } from "@/lib/types";

import { clave, puertaDelLinter } from "./puerta";

const hueco = (codigo: string, nivel: Hueco["nivel"], ubicacion = "p1::x"): Hueco => ({
  nivel,
  codigo,
  ubicacion,
  mensaje: "",
  propuesta: null,
});

it("un bloqueante cierra la puerta aunque esté reconocido", () => {
  const h = hueco("EST-05", "bloqueante");
  const puerta = puertaDelLinter([h], new Set([clave(h)]));

  expect(puerta.desbloqueado).toBe(false);
  expect(puerta.bloqueantes).toEqual([h]);
});

it("un falta_dato reconocido deja de bloquear; sin reconocer, bloquea", () => {
  const reconocido = hueco("DIC-07", "falta_dato", "p1::a");
  const pendiente = hueco("DIC-07", "falta_dato", "p1::b");

  const puerta = puertaDelLinter([reconocido, pendiente], new Set([clave(reconocido)]));

  expect(puerta.bloqueantes).toEqual([pendiente]);
  expect(puerta.desbloqueado).toBe(false);
});

it("un por_confirmar nunca cierra la puerta", () => {
  const puerta = puertaDelLinter([hueco("FLU-03", "por_confirmar")], new Set());

  expect(puerta.desbloqueado).toBe(true);
  expect(puerta.bloqueantes).toEqual([]);
});
