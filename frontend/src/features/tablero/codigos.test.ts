import { expect, it } from "vitest";

import { tituloDeCodigo } from "@/features/huecos/lenguaje";

import { nombreCorto } from "./codigos";

it("no inventa el significado de un codigo: INS-01 es lo que dice lenguaje.ts", () => {
  // INS-01 es «no se encontro la Propuesta TO-BE» (extractores/expediente.py);
  // un rotulo inventado aqui diria una mentira en «Donde se atoran».
  expect(nombreCorto("INS-01")).toBe(tituloDeCodigo("INS-01"));
  expect(nombreCorto("INS-01")).not.toMatch(/AS-IS/i);
  expect(nombreCorto("INS-02")).toBe(tituloDeCodigo("INS-02"));
});

it("un codigo desconocido sale tal cual", () => {
  expect(nombreCorto("ZZZ-99")).toBe("ZZZ-99");
});

it("usa la misma redaccion que el wizard: un solo nombre por hallazgo", () => {
  expect(nombreCorto("DIC-08")).toBe(tituloDeCodigo("DIC-08"));
  expect(nombreCorto("API-05")).toBe("Conexión que exige credencial");
});
