import { describe, expect, it } from "vitest";

import { leerRuta, migas } from "./rutas";

describe("leerRuta", () => {
  it("reconoce cada pantalla y cae a inicio con lo desconocido", () => {
    expect(leerRuta("/")).toEqual({ tipo: "inicio" });
    expect(leerRuta("/expediente")).toEqual({ tipo: "expediente" });
    expect(leerRuta("/desde-as-is")).toEqual({ tipo: "desde_as_is" });
    expect(leerRuta(`/revisar/${"a".repeat(16)}`)).toEqual({ tipo: "revisar", sid: "a".repeat(16) });
    expect(leerRuta("/revisar/xyz")).toEqual({ tipo: "inicio" });
    expect(leerRuta("/tablero")).toEqual({ tipo: "tablero" });
    expect(leerRuta("/cualquier-cosa")).toEqual({ tipo: "inicio" });
  });
});

describe("migas", () => {
  const etiquetas = (t: { etiqueta: string }[]) => t.map((x) => x.etiqueta);
  it("tres tramos como maximo y solo Inicio es enlace", () => {
    const casos = [
      migas("inicio", null), migas("carga", "carpeta"), migas("carga", "as_is"),
      migas("diccionario", "as_is"), migas("tobe", "as_is"),
      migas("revision", "carpeta"), migas("revision", "as_is"), migas("revision", null),
    ];
    for (const c of casos) {
      expect(c.length).toBeLessThanOrEqual(3);
      c.slice(1).forEach((t) => expect(t.href).toBeUndefined());
    }
    expect(migas("inicio", null)).toEqual([{ etiqueta: "Inicio" }]);
    expect(migas("carga", "carpeta")[0]).toEqual({ etiqueta: "Inicio", href: "/" });
  });
  it("dice el camino y el paso", () => {
    expect(etiquetas(migas("carga", "carpeta"))).toEqual(["Inicio", "Expediente completo"]);
    expect(etiquetas(migas("carga", "as_is"))).toEqual(["Inicio", "Solo AS-IS"]);
    expect(etiquetas(migas("diccionario", "as_is"))).toEqual(["Inicio", "Solo AS-IS", "Diccionario (1 de 2)"]);
    expect(etiquetas(migas("tobe", "as_is"))).toEqual(["Inicio", "Solo AS-IS", "TO-BE (2 de 2)"]);
    expect(etiquetas(migas("revision", "carpeta"))).toEqual(["Inicio", "Expediente completo", "Revisión"]);
    expect(etiquetas(migas("revision", null))).toEqual(["Inicio", "Revisión"]);
  });
});
