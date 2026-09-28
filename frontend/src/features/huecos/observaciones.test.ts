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

test("DIC-09 va al apartado del Diccionario, no a «Otros hallazgos»", () => {
  // Un nombre @@ declarado dos veces se corrige donde vive el dato. Si cae en
  // «Otros hallazgos», Simplificacion tiene que adivinar que le toca.
  const doc = documentoDeObservaciones(estado([
    hueco("DIC-09", "p1", "el nombre técnico '@@estatus_tramite' lo declara más de un campo"),
  ]));
  expect(doc).toContain("corregir en el Diccionario de Datos  (1)");
  expect(doc).toContain("estatus_tramite");
  expect(doc).not.toContain("Otros hallazgos");
});

test("GEN-01 va al apartado del Diccionario, no a «Otros hallazgos»", () => {
  // Un requisito del AS-IS sin campo Archivo se corrige en el Diccionario.
  const doc = documentoDeObservaciones(estado([
    hueco("GEN-01", "requisitos", "El AS-IS pide «CURP» y el Diccionario propuesto no lo captura como un campo de tipo Archivo."),
  ]));
  expect(doc).toContain("corregir en el Diccionario de Datos  (1)");
  expect(doc).not.toContain("Otros hallazgos");
});

test("API-06 se confirma en la plataforma: no se le manda a Simplificacion", () => {
  const doc = documentoDeObservaciones(estado([
    hueco("API-06", "p1", "se armó el autollenado por CURP con SIPUBEH", "por_confirmar"),
  ]));
  expect(doc).not.toContain("Otros hallazgos");
  expect(doc).not.toContain("corregir en el Diccionario");
});

test("GEN-02 va al apartado del TO-BE, no a «Otros hallazgos»", () => {
  const doc = documentoDeObservaciones(estado([
    hueco("GEN-02", "flujo", "el AS-IS habla de solventar («solventa») y el diagrama compilable no regresa a ninguna tarea: falta el ciclo de corrección (revisión → dictamen → corrección del ciudadano → vuelta a la revisión)"),
  ]));
  expect(doc).toContain("corregir en la Propuesta TO-BE");
  expect(doc).not.toContain("Otros hallazgos");
});

test("GEN-03 va al apartado del TO-BE", () => {
  const doc = documentoDeObservaciones(estado([
    hueco("GEN-03", "G2", "la rama «Transferencia» de la compuerta «¿@@modalidad_pago?» no es un valor de @@modalidad_pago; su catálogo es: En línea · Banco o transferencia. Con una sola etiqueta así el flujo entero sale lineal"),
  ]));
  expect(doc).toContain("corregir en la Propuesta TO-BE");
  expect(doc).not.toContain("Otros hallazgos");
});

describe("avisos de la comparativa", () => {
  test("van en su propia sección", () => {
    const doc = documentoDeObservaciones(estado([]), new Date(2026, 8, 28), [
      hueco("CMP-04", "to_be", "Requisitos del AS-IS que el TO-BE no conserva ni dice que elimina: «acta»."),
      hueco("CMP-01", "as_is", "El AS-IS no trae una lista de pasos que se pueda leer: los pasos de antes no se cuentan."),
    ]);

    expect(doc).toContain("## Sobre la comparativa de antes y después  (2)");
    expect(doc).toContain("«acta»");
    expect(doc).toContain("En el Análisis AS-IS");
    expect(doc).toContain("En la Propuesta TO-BE");
    expect(doc).not.toContain("No hay observaciones que requieran cambios");
    expect(doc).not.toContain("Otros hallazgos");
  });

  test("un documento eliminado sin fundamento va en las observaciones", () => {
    const doc = documentoDeObservaciones(estado([]), new Date(2026, 8, 28), [
      hueco("CMP-05", "to_be", "El TO-BE ya no pide «orden de trabajo» y no dice por qué."),
    ]);
    expect(doc).toContain("En la Propuesta TO-BE");
    expect(doc).toContain("«orden de trabajo»");
  });

  test("sin avisos el documento queda como antes", () => {
    expect(documentoDeObservaciones(estado([]), new Date(2026, 8, 28), [])).toBe(
      documentoDeObservaciones(estado([]), new Date(2026, 8, 28)),
    );
  });
});
