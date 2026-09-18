import { describe, expect, test } from "vitest";

import type { EstadoExpediente, Hueco } from "@/lib/types";

import { documentoDeObservaciones } from "./observaciones";

const hueco = (codigo: string, ubicacion: string, mensaje: string, nivel = "falta_dato"): Hueco =>
  ({ nivel, codigo, ubicacion, mensaje, propuesta: null });

const estado = (huecos: Hueco[]): EstadoExpediente =>
  ({
    sid: "a".repeat(16),
    manifiesto: {
      tramite: { nombre: "Reposición de Certificado" },
      pantallas: [
        { id: "p1", nombre: "Nueva Solicitud", campos: [] },
        { id: "p7", nombre: "Cargar Copia del Certificado", campos: [] },
      ],
    },
    huecos,
    estimacion: {},
    problemas: [],
    tieneVistas: false,
    reconocidos: [],
    adjuntos: [],
    propuestasPendientes: false,
  }) as unknown as EstadoExpediente;

describe("documentoDeObservaciones", () => {
  test("separa lo que corrige el Diccionario de lo que corrige el TO-BE", () => {
    const doc = documentoDeObservaciones(
      estado([
        hueco("DIC-08", "p1::vista", "la condición de visibilidad de 'Vista' (vista) no se pudo interpretar: «Visible solo si \"¿Documentación Conforme?\" = No»; configúrala a mano"),
        hueco("FLU-01", "flujo", "el diagrama TO-BE tiene 2 compuerta(s) que este manifiesto NO reproduce: falta el `@@campo`."),
      ]),
    );

    expect(doc).toContain("## Lo que hay que corregir en el Diccionario de Datos");
    expect(doc).toContain("## Lo que hay que corregir en la Propuesta TO-BE");
    expect(doc.indexOf("Diccionario de Datos")).toBeLessThan(doc.indexOf("Propuesta TO-BE"));
  });

  test("nombra la pantalla por su nombre, no por su id", () => {
    const doc = documentoDeObservaciones(
      estado([hueco("DIC-07", "p7::modalidad", "el campo 'Modalidad' es select pero no se extrajo ninguna opción (ni en 'Catálogo de Valores' ni en 'Límite/Especificaciones'); el compilador lo emite como campo de texto")]),
    );

    expect(doc).toContain("Pantalla «Cargar Copia del Certificado»");
    expect(doc).not.toContain("p7::");
  });

  test("incluye la frase textual del Diccionario cuando el mensaje la trae", () => {
    // Es el dato con el que Simplificacion localiza la celda que escribio.
    const doc = documentoDeObservaciones(
      estado([hueco("DIC-08", "p1::vista", "la condición de visibilidad de 'Vista de solo lectura' (vista) no se pudo interpretar: «Visible solo si \"¿Documentación Conforme?\" = No»; configúrala a mano")]),
    );

    expect(doc).toContain("«Visible solo si \"¿Documentación Conforme?\" = No»");
    expect(doc).toContain("Vista de solo lectura");
  });

  test("lo que se configura en la plataforma no se les manda, pero se cuenta", () => {
    const doc = documentoDeObservaciones(
      estado([
        hueco("DIC-07", "p1::x", "el campo 'X' es select pero no se extrajo ninguna opción (ni en 'Catálogo de Valores' ni en 'Límite/Especificaciones'); el compilador lo emite como campo de texto"),
        hueco("META-05", "metadatos", "no se encontro homoclave; en tramites nuevos es normal, la asigna GPM", "por_confirmar"),
        hueco("DOC-04", "documentos/Acta", "el documento «Acta» se genera al terminar la tarea «Revisar», la primera en la que ya están todos sus datos.", "por_confirmar"),
      ]),
    );

    expect(doc).not.toContain("homoclave");
    expect(doc).toContain("2 se configuran en la plataforma");
  });

  test("un codigo que nadie clasifico acaba en «Otros», no en el olvido", () => {
    const doc = documentoDeObservaciones(estado([hueco("ZZZ-99", "p1::x", "algo nuevo que nadie clasifico")]));

    expect(doc).toContain("## Otros hallazgos");
    expect(doc).toContain("algo nuevo que nadie clasifico");
  });

  test("sin nada que corregir lo dice, en vez de entregar un documento vacio", () => {
    const doc = documentoDeObservaciones(estado([]));

    expect(doc).toContain("No hay observaciones");
    expect(doc).not.toContain("## Lo que hay que corregir");
  });

  test("encabeza con el tramite y la fecha, para que se pueda archivar", () => {
    const doc = documentoDeObservaciones(estado([]));

    expect(doc.split("\n")[0]).toBe("# Observaciones al expediente — Reposición de Certificado");
    expect(doc).toMatch(/\d{1,2} de \w+ de \d{4}/);
  });
});
