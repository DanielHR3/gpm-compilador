import { describe, expect, test } from "vitest";

import type { CampoManifiesto } from "@/lib/types";

import { clasificarCandidatos } from "./candidatos";

const campo = (nombre: string, etiqueta: string, pantalla: number, catalogo = 1): CampoManifiesto =>
  ({
    nombre,
    etiqueta,
    pantalla,
    catalogo: Array.from({ length: catalogo }, (_, i) => ({ valor: `v${i}`, etiqueta: `V${i}` })),
  }) as CampoManifiesto;

const CAMPOS = [
  campo("es_persona_moral", "¿Es Persona Moral?", 0),
  campo("vista", "Vista de solo lectura", 0, 0),
  campo("documentacion_conforme", "¿Documentación Conforme?", 1),
  campo("estatus_tramite", "Estatus del Trámite", 2),
];

const objetivo = { interno: "vista", pantalla: 0 };

describe("clasificarCandidatos", () => {
  test("un campo de una pantalla posterior no se puede usar", () => {
    // Al llenar la pantalla 1 ese dato todavia no existe: lo captura otra
    // persona mas adelante. Es el caso que rompio el expediente de Reposicion.
    const c = clasificarCandidatos(CAMPOS, objetivo, "");
    const conforme = c.find((x) => x.campo.nombre === "documentacion_conforme");

    expect(conforme?.grupo).toBe("inservible");
    expect(conforme?.motivo).toBe("se captura después");
  });

  test("el campo no puede decidir su propia visibilidad", () => {
    const c = clasificarCandidatos(CAMPOS, objetivo, "");

    expect(c.find((x) => x.campo.nombre === "vista")?.motivo).toBe("es este mismo campo");
  });

  test("lo que menciona la frase del Diccionario encabeza", () => {
    const c = clasificarCandidatos(
      CAMPOS,
      { interno: "vista", pantalla: 3 },
      'Visible solo si "Estatus del Trámite" = Pago validado',
    );

    expect(c[0].campo.nombre).toBe("estatus_tramite");
    expect(c[0].grupo).toBe("sugerido");
  });

  test("la sugerencia no depende de acentos ni de mayusculas", () => {
    const c = clasificarCandidatos(
      CAMPOS,
      { interno: "vista", pantalla: 3 },
      "visible solo si ESTATUS DEL TRAMITE es Pago validado",
    );

    expect(c[0].campo.nombre).toBe("estatus_tramite");
  });

  test("un campo de una pantalla posterior no se sugiere aunque la frase lo nombre", () => {
    // El Diccionario lo nombra, pero seguiria siendo imposible: primero manda
    // la regla, y la sugerencia no puede contradecirla.
    const c = clasificarCandidatos(
      CAMPOS,
      objetivo,
      'Visible solo si "¿Documentación Conforme?" = No',
    );

    expect(c.find((x) => x.campo.nombre === "documentacion_conforme")?.grupo).toBe("inservible");
  });

  test("los grupos salen en orden: sugeridos, usables, inservibles", () => {
    const grupos = clasificarCandidatos(
      CAMPOS,
      { interno: "vista", pantalla: 1 },
      "Estatus del Trámite",
    ).map((x) => x.grupo);

    expect(grupos).toEqual([...grupos].sort((a, b) =>
      ["sugerido", "usable", "inservible"].indexOf(a) -
      ["sugerido", "usable", "inservible"].indexOf(b)));
  });

  test("sin objetivo no se descarta nada: la compuerta no tiene esa regla", () => {
    const c = clasificarCandidatos(CAMPOS, null, "");

    expect(c.every((x) => x.grupo === "usable")).toBe(true);
  });
});
