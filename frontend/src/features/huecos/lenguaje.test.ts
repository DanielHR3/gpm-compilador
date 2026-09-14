import { describe, expect, test } from "vitest";

import type { CampoManifiesto, Condicion } from "@/lib/types";

import {
  describirCondicion,
  leerMensajeVisibilidad,
  nombreDeCompuerta,
  nombreDeTarea,
  pistaDeCodigo,
  tituloDeCodigo,
} from "./lenguaje";

describe("tituloDeCodigo", () => {
  test("traduce el codigo a algo que un analista entiende", () => {
    expect(tituloDeCodigo("DIC-08")).toBe("Visibilidad de un campo");
    expect(tituloDeCodigo("MMD-04")).toBe("Decisión del flujo");
    expect(tituloDeCodigo("MMD-03")).toBe("Responsable de una tarea");
    expect(tituloDeCodigo("META-04")).toBe("Nombre del trámite");
  });

  test("un codigo que no conozco se queda como esta, sin inventar", () => {
    expect(tituloDeCodigo("ZZZ-99")).toBe("ZZZ-99");
  });
});

describe("leerMensajeVisibilidad", () => {
  const crudo =
    "la condición de visibilidad de 'RFC de la Dependencia' (rfc_dependencia) " +
    "no se pudo interpretar: «Visible solo cuando `@@procedencia` = Dependencia u organismo»; configúrala a mano";

  test("saca la etiqueta que ve el ciudadano", () => {
    expect(leerMensajeVisibilidad(crudo)?.etiqueta).toBe("RFC de la Dependencia");
  });

  test("saca el nombre interno y la frase original del Diccionario", () => {
    const leido = leerMensajeVisibilidad(crudo);
    expect(leido?.interno).toBe("rfc_dependencia");
    expect(leido?.frase).toBe("Visible solo cuando `@@procedencia` = Dependencia u organismo");
  });

  test("un mensaje con otra forma devuelve null en vez de adivinar", () => {
    expect(leerMensajeVisibilidad("cualquier otra cosa")).toBeNull();
  });
});

describe("describirCondicion", () => {
  const campos = [
    { nombre: "procedencia", etiqueta: "Procedencia", catalogo: [{ valor: "dep", etiqueta: "Dependencia u organismo" }] },
    { nombre: "curp", etiqueta: "CURP", catalogo: [] },
  ] as CampoManifiesto[];

  test("lee la condicion como una frase, con las etiquetas y no los nombres internos", () => {
    const c: Condicion = { campo: "procedencia", operador: "==", igual: "dep", y: [] };

    expect(describirCondicion(c, campos)).toBe(
      "Procedencia es igual a Dependencia u organismo",
    );
  });

  test("une las clausulas con 'y', no con simbolos", () => {
    const c: Condicion = {
      campo: "procedencia",
      operador: "==",
      igual: "dep",
      y: [{ campo: "curp", operador: "!=", igual: "XXXX" }],
    };

    expect(describirCondicion(c, campos)).toBe(
      "Procedencia es igual a Dependencia u organismo y CURP es distinto de XXXX",
    );
  });

  test("sin condicion no describe nada", () => {
    expect(describirCondicion(null, campos)).toBe("");
  });
});

describe("pistaDeCodigo", () => {
  test("dice que hay que hacer y da un ejemplo concreto", () => {
    const p = pistaDeCodigo("META-01");

    expect(p?.instruccion).toMatch(/cuánto tarda/i);
    expect(p?.marcador).toBe("15 días hábiles");
  });

  test("la pista de visibilidad ensena la regla completa con un caso real", () => {
    expect(pistaDeCodigo("DIC-08")?.ejemplo).toBe(
      "Muestra «RFC» solo cuando «Procedencia» sea igual a «Dependencia u organismo».",
    );
  });

  test("el nombre del tramite propone uno de verdad, no 'texto aqui'", () => {
    expect(pistaDeCodigo("META-04")?.marcador).toBe("Constancia de Residencia");
  });

  test("un codigo sin pista escrita devuelve null en vez de una frase hueca", () => {
    expect(pistaDeCodigo("ZZZ-99")).toBeNull();
  });
});

describe("nombreDeTarea", () => {
  test("saca el nombre de la tarea de entre las comillas", () => {
    expect(
      nombreDeTarea(
        "la tarea «Consultar información del trámite» no declara carril (:::clase)",
      ),
    ).toBe("Consultar información del trámite");
  });

  test("quita el emoji y el prefijo de actor que trae el diagrama", () => {
    expect(
      nombreDeTarea(
        "la tarea «🔍 Usuario: Consultar información del trámite» no declara carril",
      ),
    ).toBe("Consultar información del trámite");
  });

  test("recorta el detalle entre parentesis, que alarga sin aportar", () => {
    expect(
      nombreDeTarea(
        "la tarea «🏛️ Periódico Oficial: Revisar expediente (cierre miércoles 14:30)» no declara carril",
      ),
    ).toBe("Revisar expediente");
  });

  test("un mensaje sin comillas devuelve null en vez de inventar", () => {
    expect(nombreDeTarea("otra cosa cualquiera")).toBeNull();
  });
});

describe("nombreDeCompuerta", () => {
  test("saca la pregunta de la compuerta de entre los parentesis", () => {
    expect(
      nombreDeCompuerta(
        "la compuerta (¿Tiene observaciones?) no nombra ningún campo @@; la condición debe capturarse a mano",
      ),
    ).toBe("¿Tiene observaciones?");
  });

  test("quita el emoji y el carril que trae el diagrama", () => {
    expect(
      nombreDeCompuerta(
        "la compuerta (🏛️ Periódico Oficial: ¿Es competencia del PO?) no nombra ningún campo @@",
      ),
    ).toBe("¿Es competencia del PO?");
  });

  test("el marcador de bifurcacion tampoco sobrevive", () => {
    expect(
      nombreDeCompuerta("la compuerta (🔀 ¿Procedencia? tarifa) no nombra ningún campo @@"),
    ).toBe("¿Procedencia? tarifa");
  });

  test("sin parentesis devuelve null en vez de inventar", () => {
    expect(nombreDeCompuerta("otra cosa")).toBeNull();
  });
});

describe("codigos de documentos de salida", () => {
  test("DOC-02 y DOC-03 tienen titulo en castellano y pista de llenado", () => {
    expect(tituloDeCodigo("DOC-02")).toBe("Variable sin campo en un documento");
    expect(tituloDeCodigo("DOC-03")).toBe("Plantilla de documento ilegible");
    expect(pistaDeCodigo("DOC-02")?.instruccion).toMatch(/campo del Diccionario/i);
    expect(pistaDeCodigo("DOC-03")?.instruccion).toMatch(/Word/);
  });
});
