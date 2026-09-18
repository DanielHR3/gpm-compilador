import { describe, expect, test } from "vitest";

import type { CampoManifiesto, Condicion, Hueco } from "@/lib/types";

import {
  describirCondicion,
  ejemploDeVisibilidad,
  leerMensajeVisibilidad,
  nombreDeCompuerta,
  nombreDeTarea,
  pistaDeCodigo,
  redactarHueco,
  tituloDeCodigo,
} from "./lenguaje";

describe("tituloDeCodigo", () => {
  test("traduce el codigo a algo que un analista entiende", () => {
    expect(tituloDeCodigo("DIC-08")).toBe("Visibilidad de un campo");
    expect(tituloDeCodigo("MMD-04")).toBe("Decisión del flujo");
    expect(tituloDeCodigo("MMD-03")).toBe("Responsable de una tarea");
    expect(tituloDeCodigo("META-04")).toBe("Nombre del trámite");
  });

  test("el titulo de DIC-02 habla del catalogo, que es de lo que habla su mensaje", () => {
    // Decia "Tipo de campo", que no es lo que el hueco reporta: el encabezado
    // y el cuerpo de la tarjeta contaban cosas distintas.
    expect(tituloDeCodigo("DIC-02")).toBe("Lista declarada como pendiente");
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
    expect(tituloDeCodigo("DOC-04")).toBe("En qué tarea se genera el documento");
    expect(pistaDeCodigo("DOC-04")?.instruccion).toMatch(/tarea/i);
  });
});

/**
 * Un mensaje real por cada codigo de la tanda 1, copiado de los extractores.
 * Sirve de red: si una redaccion futura se escribe con jerga, la prueba
 * transversal de abajo lo caza sin que haya que acordarse de anadirla.
 */
const MENSAJES_REALES: ReadonlyArray<readonly [string, string]> = [
  ["META-01", "no se encontro el tiempo de respuesta declarado"],
  ["META-02", "no se encontro la dependencia en el frontmatter del AS-IS"],
  ["META-03", "no se encontro el costo declarado; se asume sin costo"],
  ["META-04", "no se pudo determinar el nombre del tramite"],
  ["META-05", "no se encontro homoclave; en tramites nuevos es normal, la asigna GPM"],
  ["META-06", "no se encontro 'A quien va dirigido'; type_of_person queda en 'ambas'"],
  ["DIC-02", "el catálogo de 'Estatus del Trámite' está declarado como pendiente en el Diccionario; no se emite"],
  ["DIC-07", "el campo 'Modalidad' es select pero no se extrajo ninguna opción (ni en 'Catálogo de Valores' ni en 'Límite/Especificaciones'); el compilador lo emite como campo de texto hasta que se defina el catálogo"],
  ["FLU-01", "el diagrama TO-BE tiene 2 compuerta(s) que este manifiesto NO reproduce: falta el `@@campo` en la compuerta, o una etiqueta de arista no casa con un valor del catálogo, o las tareas no casan con las pantallas. El flujo sale lineal; ramificar a mano."],
  ["FLU-02", "el diagrama tiene 5 tareas y el Diccionario 4 pantallas; confirmar la correspondencia"],
  ["FLU-03", "el flujo se ramificó automáticamente del diagrama TO-BE (1 compuerta(s), 2 conexión(es) con condición). Confirma que las tareas casan con las pantallas: «nueva solicitud» → P1"],
  ["DOC-04", "el documento «Constancia» no se genera en ninguna tarea: ninguna del flujo llega a tener todos sus datos (curp, nombre). Revisa que esas pantallas estén en el flujo"],
];

const MENSAJE: Record<string, string> = Object.fromEntries(MENSAJES_REALES);

/**
 * Los mensajes crudos de esta suite estan copiados literalmente de los
 * extractores de Python (`metadatos.py`, `diccionario.py`, `expediente.py`,
 * `documentos.py`). Si el backend cambia una de estas cadenas, la prueba falla
 * y `redactarHueco` cae al crudo: es justo lo que queremos que se note.
 */
const hueco = (codigo: string, mensaje: string, nivel = "falta_dato"): Hueco => ({
  nivel,
  codigo,
  ubicacion: "metadatos",
  mensaje,
  propuesta: null,
});

describe("redactarHueco", () => {
  test("un codigo sin redaccion escrita devuelve el mensaje crudo", () => {
    const crudo = "algo que el compilador dijo y nadie tradujo";

    expect(redactarHueco(hueco("ZZZ-99", crudo))).toBe(crudo);
  });

  test("un META con un mensaje que el backend ya no escribe cae al crudo", () => {
    // Las redacciones fijas tambien se anclan: si el extractor reescribe su
    // cadena, la pantalla vuelve al crudo en vez de seguir contando una
    // version vieja de los hechos que nadie notaria.
    const crudo = "el tiempo de respuesta ahora se declara en el TO-BE";

    expect(redactarHueco(hueco("META-01", crudo))).toBe(crudo);
  });

  test("META-01 nombra el documento donde deberia estar el dato", () => {
    expect(redactarHueco(hueco("META-01", MENSAJE["META-01"]))).toBe(
      "El AS-IS no dice cuánto tarda el trámite desde que se solicita hasta " +
        "que se entrega.",
    );
  });

  test("META-02 dice con que se publicaria la ficha si nadie lo corrige", () => {
    expect(redactarHueco(hueco("META-02", MENSAJE["META-02"]))).toBe(
      "El AS-IS no dice qué dependencia resuelve el trámite. Hasta que alguien " +
        "lo escriba, la ficha sale con «[por confirmar]» en ese lugar.",
    );
  });

  test("META-03 advierte que el tramite saldria gratuito", () => {
    expect(redactarHueco(hueco("META-03", MENSAJE["META-03"], "por_confirmar"))).toBe(
      "En ningún documento aparece el costo, así que el trámite saldría " +
        "publicado como gratuito.",
    );
  });

  test("META-04 dice los dos lugares donde se busco el nombre", () => {
    expect(redactarHueco(hueco("META-04", MENSAJE["META-04"]))).toBe(
      "No hay de dónde sacar el nombre del trámite: ni el AS-IS ni el nombre " +
        "de la carpeta lo dicen.",
    );
  });

  test("META-05 explica por que no es un problema, sin repetir el imperativo de la tarjeta", () => {
    expect(redactarHueco(hueco("META-05", MENSAJE["META-05"], "por_confirmar"))).toBe(
      "No aparece la homoclave en ningún documento. En un trámite nuevo es lo " +
        "normal: la asigna GPM cuando se publica.",
    );
  });

  test("META-06 dice la consecuencia sin nombrar la columna de la base", () => {
    expect(redactarHueco(hueco("META-06", MENSAJE["META-06"], "por_confirmar"))).toBe(
      "Ningún documento dice a quién va dirigido el trámite, así que quedará " +
        "abierto a personas físicas y morales por igual.",
    );
  });

  test("DIC-02 nombra el campo que leyo del mensaje crudo", () => {
    expect(redactarHueco(hueco("DIC-02", MENSAJE["DIC-02"]))).toBe(
      "En el Diccionario, la lista de «Estatus del Trámite» quedó marcada como " +
        "pendiente. Tal como está, el campo saldría sin opciones que elegir. " +
        "Escribe cuáles son.",
    );
  });

  test("DIC-02 con otra forma de mensaje cae al crudo en vez de inventar el campo", () => {
    const crudo = "el catálogo de algo se declaro pendiente";

    expect(redactarHueco(hueco("DIC-02", crudo))).toBe(crudo);
  });

  test("DIC-07 dice en que se convierte el campo si nadie escribe las opciones", () => {
    expect(redactarHueco(hueco("DIC-07", MENSAJE["DIC-07"]))).toBe(
      "«Modalidad» debería ser una lista, pero en el Diccionario no trae " +
        "ninguna opción: ni en «Catálogo de Valores» ni en «Límite/" +
        "Especificaciones». Tal como está, saldría como una caja de texto " +
        "donde cada quien escribe lo que quiera. Escribe las opciones.",
    );
  });

  test("FLU-01 cuenta las decisiones sin hablar de compuertas ni de aristas", () => {
    const redactado = redactarHueco(hueco("FLU-01", MENSAJE["FLU-01"]));

    expect(redactado).toContain("2 decisiones");
    expect(redactado).toContain("saldría en línea recta");
    expect(redactado).not.toMatch(/compuerta|arista|@@|manifiesto/);
  });

  test("FLU-01 concuerda en singular cuando solo hay una decision", () => {
    const una = MENSAJE["FLU-01"].replace("tiene 2 compuerta", "tiene 1 compuerta");

    expect(redactarHueco(hueco("FLU-01", una))).toContain("tiene 1 decisión que");
  });

  test("FLU-02 contrasta las dos cuentas que no cuadran", () => {
    expect(redactarHueco(hueco("FLU-02", MENSAJE["FLU-02"]))).toBe(
      "El diagrama TO-BE tiene 5 tareas y el Diccionario 4 pantallas. Como no " +
        "coinciden, no hay forma de saber qué pantalla le toca a cada tarea. " +
        "Revisa cuál de los dos documentos quedó incompleto.",
    );
  });

  test("FLU-03 conserva el detalle de que tarea quedo en que pantalla", () => {
    expect(redactarHueco(hueco("FLU-03", MENSAJE["FLU-03"], "por_confirmar"))).toBe(
      "El trámite quedó con caminos alternativos, tal como los dibuja el " +
        "diagrama TO-BE: 1 decisión y 2 salidas con condición. Revisa que a " +
        "cada tarea le haya tocado la pantalla correcta: «nueva solicitud» → P1",
    );
  });

  test("DOC-04 sin tarea destino explica que el documento no se generaria nunca", () => {
    expect(redactarHueco(hueco("DOC-04", MENSAJE["DOC-04"]))).toBe(
      "«Constancia» necesita los datos curp, nombre. Ninguna tarea del flujo " +
        "llega a tenerlos todos, así que el documento nunca se generaría. " +
        "Revisa que las pantallas donde se capturan esos datos estén en el flujo.",
    );
  });

  test("DOC-04 ya resuelto solo cuenta donde quedo, sin el imperativo que ya da la pista", () => {
    const crudo =
      "el documento «Constancia» se genera al terminar la tarea «Validar», la " +
      "primera en la que ya están todos sus datos. Si debe salir en otra tarea " +
      "(por ejemplo tras una firma), cámbialo a mano";

    expect(redactarHueco(hueco("DOC-04", crudo, "por_confirmar"))).toBe(
      "«Constancia» se generará al terminar la tarea «Validar»: es la primera " +
        "del flujo en la que ya están todos sus datos.",
    );
  });

  test("ninguna redaccion escrita deja jerga del compilador a la vista", () => {
    const JERGA = /type_of_person|classDef|:::|@@|SEG-\d|campo\.nombre|endpoint|manifiesto|compuerta|arista|select\b|radio\b/;

    for (const [codigo, crudo] of MENSAJES_REALES) {
      const redactado = redactarHueco(hueco(codigo, crudo, "falta_dato"));
      if (redactado === crudo) continue; // sin redaccion: se permite el crudo
      expect(redactado, `${codigo} deja jerga a la vista`).not.toMatch(JERGA);
    }
  });
});

describe("ejemploDeVisibilidad", () => {
  const objetivo = {
    etiqueta: "Notificación de Sanción",
    interno: "notificacion_sancion",
    frase: "Visible solo si \"Estatus del Trámite\" = Pendiente de regularización",
  };
  const campos = [
    { nombre: "curp", etiqueta: "CURP", catalogo: [] },
    {
      nombre: "estatus_tramite",
      etiqueta: "Estatus del Trámite",
      catalogo: [
        { valor: "pendiente", etiqueta: "Pendiente de regularización" },
        { valor: "vigente", etiqueta: "Vigente" },
      ],
    },
  ] as CampoManifiesto[];

  test("arma el ejemplo con campos del propio expediente", () => {
    expect(ejemploDeVisibilidad(campos, objetivo)).toBe(
      "Muestra «Notificación de Sanción» solo cuando «Estatus del Trámite» " +
        "sea igual a «Pendiente de regularización».",
    );
  });

  test("no se propone a si mismo como condicion", () => {
    // Un campo no puede decidir su propia visibilidad: el ejemplo ensenaria
    // justo la regla que el backend rechaza por autorreferencia.
    const soloElMismo = [
      {
        nombre: "notificacion_sancion",
        etiqueta: "Notificación de Sanción",
        catalogo: [{ valor: "si", etiqueta: "Sí" }],
      },
    ] as CampoManifiesto[];

    expect(ejemploDeVisibilidad(soloElMismo, objetivo)).toBeNull();
  });

  test("un campo sin etiqueta no sirve de ejemplo aunque tenga lista", () => {
    const sinEtiqueta = [
      { nombre: "x", etiqueta: "", catalogo: [{ valor: "a", etiqueta: "A" }] },
    ] as CampoManifiesto[];

    expect(ejemploDeVisibilidad(sinEtiqueta, objetivo)).toBeNull();
  });

  test("sin ningun campo con lista no inventa un ejemplo", () => {
    const sinListas = [
      { nombre: "curp", etiqueta: "CURP", catalogo: [] },
    ] as CampoManifiesto[];

    expect(ejemploDeVisibilidad(sinListas, objetivo)).toBeNull();
  });

  test("si el mensaje no dejo leer el campo del hueco, no hay ejemplo propio", () => {
    expect(ejemploDeVisibilidad(campos, null)).toBeNull();
  });
});

describe("pistaDeCodigo: instrucciones sin jerga de programador", () => {
  test("DIC-08 pide el valor que hace aparecer el campo, no una comparacion", () => {
    expect(pistaDeCodigo("DIC-08")?.instruccion).toBe(
      "Elige el campo que decide si este se ve, y el valor que hace que aparezca.",
    );
  });

  test("MMD-04 dice que la decision «mira» un campo para saber por donde seguir", () => {
    const p = pistaDeCodigo("MMD-04");

    expect(p?.instruccion).toBe(
      "Elige el campo del formulario que la decisión mira para saber por dónde " +
        "sigue el trámite.",
    );
    expect(p?.ejemplo).toBe(
      "La decisión «¿Modalidad de pago?» mira el campo «Forma de pago».",
    );
  });

  test("API-03 explica por que importa el orden de los campos", () => {
    expect(pistaDeCodigo("API-03")?.instruccion).toBe(
      "Elige el campo que hay que llenar antes que este, porque de él salen " +
        "sus opciones.",
    );
  });

  test("DOC-04 no dice que el compilador «colgó» el documento de una tarea", () => {
    const p = pistaDeCodigo("DOC-04");

    expect(p?.instruccion).toBe(
      "El documento quedó en la primera tarea del flujo que ya tiene todos sus " +
        "datos. Si está bien, confírmalo; si debe salir en otra (por ejemplo, " +
        "después de una firma), ajústalo en la plataforma.",
    );
    expect(p?.instruccion).not.toMatch(/compilador/);
  });
});
