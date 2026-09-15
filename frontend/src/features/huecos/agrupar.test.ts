import { describe, expect, test } from "vitest";

import type { Hueco } from "@/lib/types";

import { agruparPorNivel, contarPorCodigo } from "./agrupar";

const h = (nivel: Hueco["nivel"], codigo: string): Hueco =>
  ({ nivel, codigo, ubicacion: codigo, mensaje: "", propuesta: null }) as Hueco;

describe("agruparPorNivel", () => {
  test("ordena los grupos por urgencia, no por el orden de llegada", () => {
    const grupos = agruparPorNivel([
      h("por_confirmar", "META-05"),
      h("falta_dato", "META-01"),
      h("bloqueante", "INS-01"),
    ]);

    expect(grupos.map((g) => g.nivel)).toEqual([
      "bloqueante",
      "falta_dato",
      "por_confirmar",
    ]);
  });

  test("omite los niveles sin huecos en vez de mostrarlos vacios", () => {
    const grupos = agruparPorNivel([h("falta_dato", "META-01")]);

    expect(grupos).toHaveLength(1);
    expect(grupos[0].nivel).toBe("falta_dato");
    expect(grupos[0].huecos).toHaveLength(1);
  });

  test("conserva dentro del grupo el orden en que vinieron", () => {
    const grupos = agruparPorNivel([
      h("falta_dato", "B"),
      h("falta_dato", "A"),
      h("falta_dato", "C"),
    ]);

    expect(grupos[0].huecos.map((x) => x.codigo)).toEqual(["B", "A", "C"]);
  });

  test("cada grupo trae su rotulo y su cuenta", () => {
    const grupos = agruparPorNivel([
      h("bloqueante", "INS-01"),
      h("falta_dato", "META-01"),
      h("falta_dato", "DIC-08"),
    ]);

    expect(grupos[0]).toMatchObject({ rotulo: "Bloquean la descarga", total: 1 });
    expect(grupos[1]).toMatchObject({ rotulo: "Falta un dato", total: 2 });
  });

  test("una lista vacia no produce grupos", () => {
    expect(agruparPorNivel([])).toEqual([]);
  });
});

describe("contarPorCodigo", () => {
  test("cuenta cuantos huecos hay de cada codigo, de mas a menos", () => {
    const cuenta = contarPorCodigo([
      h("falta_dato", "DIC-08"),
      h("falta_dato", "MMD-03"),
      h("falta_dato", "MMD-03"),
      h("falta_dato", "MMD-03"),
      h("falta_dato", "DIC-08"),
      h("falta_dato", "META-01"),
    ]);

    expect(cuenta).toEqual([
      { codigo: "MMD-03", total: 3 },
      { codigo: "DIC-08", total: 2 },
      { codigo: "META-01", total: 1 },
    ]);
  });

  test("con la misma cuenta, ordena alfabeticamente para no bailar entre renders", () => {
    const cuenta = contarPorCodigo([h("falta_dato", "MMD-04"), h("falta_dato", "DIC-08")]);

    expect(cuenta.map((c) => c.codigo)).toEqual(["DIC-08", "MMD-04"]);
  });

  test("una lista vacia no cuenta nada", () => {
    expect(contarPorCodigo([])).toEqual([]);
  });
});
