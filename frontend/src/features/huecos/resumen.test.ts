import { describe, expect, test } from "vitest";

import { resumirManifiesto } from "./resumen";

const manifiesto = {
  tramite: { nombre: "Constancia de Residencia", dependencia: "SEMARNATH" },
  actores: [{ id: "a" }, { id: "b" }],
  pantallas: [
    { id: "p1", campos: [{ nombre: "curp" }, { nombre: "rfc", condicion_visible: { campo: "x" } }] },
    { id: "p2", campos: [{ nombre: "domicilio" }] },
  ],
  flujo: { tareas: [{ id: "t1" }, { id: "t2" }, { id: "t3" }], conexiones: [{ cuando: null }, { cuando: "x" }] },
};

describe("resumirManifiesto", () => {
  test("cuenta lo que el compilador entendio del documento", () => {
    const r = resumirManifiesto(manifiesto);

    expect(r.pantallas).toBe(2);
    expect(r.campos).toBe(3);
    expect(r.tareas).toBe(3);
    expect(r.actores).toBe(2);
  });

  test("destaca los campos que solo se ven bajo condicion", () => {
    expect(resumirManifiesto(manifiesto).condicionales).toBe(1);
  });

  test("cuenta las bifurcaciones del flujo, no las conexiones rectas", () => {
    expect(resumirManifiesto(manifiesto).decisiones).toBe(1);
  });

  test("saca el nombre y la dependencia para encabezar", () => {
    const r = resumirManifiesto(manifiesto);
    expect(r.nombre).toBe("Constancia de Residencia");
    expect(r.dependencia).toBe("SEMARNATH");
  });

  test("un nombre «[por confirmar]» no se presenta como si fuera real", () => {
    const r = resumirManifiesto({ ...manifiesto, tramite: { nombre: "[por confirmar]" } });
    expect(r.nombre).toBeNull();
  });

  test("un manifiesto vacio no revienta ni inventa cifras", () => {
    const r = resumirManifiesto({});
    expect(r).toMatchObject({
      pantallas: 0, campos: 0, tareas: 0, actores: 0,
      condicionales: 0, decisiones: 0, nombre: null, dependencia: null,
    });
  });
});
