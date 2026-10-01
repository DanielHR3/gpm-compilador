import { describe, expect, test } from "vitest";

import { tareasDeDocumento } from "./tareasDeDocumento";

/** T1 -> T2 (rama sí) / T3 (rama no) -> fin. Cada tarea captura un campo. */
const manifiesto = (variables: string[], colgadoDe = "t1") => ({
  pantallas: [
    { id: "p1", campos: [{ nombre: "curp" }] },
    { id: "p2", campos: [{ nombre: "monto" }] },
    { id: "p3", campos: [{ nombre: "motivo" }] },
  ],
  flujo: {
    tareas: [
      { id: "t1", nombre: "Solicitud", terminal: false, pantallas: [{ id: "p1" }], acciones_antes: [], acciones_despues: colgadoDe === "t1" ? ["Oficio"] : [] },
      { id: "t2", nombre: "Cotiza", terminal: false, pantallas: [{ id: "p2" }], acciones_antes: [], acciones_despues: colgadoDe === "t2" ? ["Oficio"] : [] },
      { id: "t3", nombre: "Rechazo", terminal: false, pantallas: [{ id: "p3" }], acciones_antes: [], acciones_despues: colgadoDe === "t3" ? ["Oficio"] : [] },
      { id: "fin", nombre: "Trámite concluido", terminal: true, pantallas: [], acciones_antes: [], acciones_despues: [] },
    ],
    conexiones: [
      { de: "t1", a: "t2" }, { de: "t1", a: "t3" },
      { de: "t2", a: "fin" }, { de: "t3", a: "fin" },
    ],
  },
  acciones: [{ tipo: "documento", nombre: "Oficio", variables }],
});

describe("tareasDeDocumento: la misma regla que `vale_para` en el servidor", () => {
  test("una tarea vale si los datos se capturan en ella o en una anterior", () => {
    const t = tareasDeDocumento(manifiesto(["curp", "motivo"]), "Oficio");
    expect(t.map((x) => [x.id, x.vale])).toEqual([
      ["t1", false], ["t2", false], ["t3", true], ["fin", false],
    ]);
  });

  test("dice qué falta, con el motivo listo para leerse", () => {
    const t = tareasDeDocumento(manifiesto(["curp", "motivo"]), "Oficio");
    expect(t[0].motivo).toBe("todavía no se capturan: motivo");
  });

  test("una rama hermana no aporta sus campos", () => {
    const t = tareasDeDocumento(manifiesto(["monto"]), "Oficio");
    expect(t.find((x) => x.id === "t3")?.vale).toBe(false);
    expect(t.find((x) => x.id === "t2")?.vale).toBe(true);
  });

  test("el cierre del trámite nunca vale, aunque le lleguen todos los datos", () => {
    const fin = tareasDeDocumento(manifiesto(["curp"]), "Oficio").find((x) => x.id === "fin");
    expect(fin).toMatchObject({ vale: false, motivo: "es el cierre del trámite" });
  });

  test("una plantilla sin variables vale en toda tarea que no sea el cierre", () => {
    const t = tareasDeDocumento(manifiesto([]), "Oficio");
    expect(t.map((x) => x.vale)).toEqual([true, true, true, false]);
  });

  test("marca la tarea donde el documento está hoy", () => {
    const t = tareasDeDocumento(manifiesto([], "t2"), "Oficio");
    expect(t.filter((x) => x.actual).map((x) => x.id)).toEqual(["t2"]);
  });

  test("un ciclo de corrección no cuelga el cálculo", () => {
    const m = manifiesto(["motivo"]);
    m.flujo.conexiones.push({ de: "t3", a: "t1" });
    expect(tareasDeDocumento(m, "Oficio").find((x) => x.id === "t1")?.vale).toBe(true);
  });

  test("un documento que no existe o un manifiesto sin flujo dan lista vacía", () => {
    expect(tareasDeDocumento(manifiesto([]), "Otro")).toEqual([]);
    expect(tareasDeDocumento({}, "Oficio")).toEqual([]);
  });
});
