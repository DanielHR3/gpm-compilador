import type { CampoManifiesto, Condicion } from "@/lib/types";

/**
 * Titulos en castellano para los codigos de validacion.
 *
 * Quien documenta un tramite no sabe —ni tiene por que saber— que es un
 * "DIC-08". El codigo sigue existiendo para rastrear y reportar, pero vive en
 * el detalle tecnico, no en el encabezado de la tarjeta.
 */
const TITULOS: Record<string, string> = {
  "INS-01": "Falta un documento de entrada",
  "META-01": "Tiempo de respuesta",
  "META-02": "Dependencia responsable",
  "META-03": "Costo del trámite",
  "META-04": "Nombre del trámite",
  "META-05": "Homoclave",
  "META-06": "A quién va dirigido",
  "DIC-01": "Campo sin pantalla asignada",
  "DIC-04": "División en pantallas",
  "DIC-05": "Etiqueta de un campo",
  "DIC-02": "Tipo de campo",
  "DIC-06": "Nombre técnico demasiado largo",
  "DIC-07": "Lista sin opciones",
  "DIC-08": "Visibilidad de un campo",
  "API-03": "Campo del que depende",
  "API-04": "Conexión con otro sistema",
  "DOC-02": "Variable sin campo en un documento",
  "DOC-03": "Plantilla de documento ilegible",
  "MMD-02": "Nodo del diagrama no declarado",
  "MMD-03": "Responsable de una tarea",
  "MMD-04": "Decisión del flujo",
  "FLU-01": "Compuertas del diagrama",
  "FLU-02": "Tareas y pantallas",
  "FLU-03": "Ramificación del flujo",
};

/** El titulo humano del codigo; si no lo conozco, el codigo tal cual. */
export function tituloDeCodigo(codigo: string): string {
  return TITULOS[codigo] ?? codigo;
}

export type MensajeVisibilidad = {
  /** La etiqueta que ve el ciudadano en el formulario. */
  etiqueta: string;
  /** El nombre interno del campo (para el detalle tecnico). */
  interno: string;
  /** La frase tal cual se escribio en el Diccionario. */
  frase: string;
};

/**
 * Descompone el mensaje de DIC-08 en sus partes legibles.
 *
 * El backend emite una sola cadena que mezcla lo que le sirve a una persona
 * (que campo, que se escribio) con lo que solo le sirve a un programador. Esto
 * la parte para poder mostrar cada cosa en su lugar.
 *
 * Si el mensaje no tiene la forma esperada devuelve `null` en vez de adivinar:
 * la tarjeta cae entonces al mensaje crudo, que es feo pero cierto.
 */
export function leerMensajeVisibilidad(
  mensaje: string,
): MensajeVisibilidad | null {
  const m = /de '([^']+)' \(([^)]+)\).*?«(.+?)»/s.exec(mensaje);
  if (!m) return null;
  return { etiqueta: m[1], interno: m[2], frase: m[3] };
}

/** "es igual a" / "es distinto de": el operador dicho como se diria hablando. */
const VERBO: Record<string, string> = {
  "==": "es igual a",
  "!=": "es distinto de",
};

/** Cambia el nombre interno por la etiqueta, y el valor por su texto visible. */
function nombrarCampo(nombre: string, campos: CampoManifiesto[]): string {
  return campos.find((c) => c.nombre === nombre)?.etiqueta ?? nombre;
}

function nombrarValor(
  nombreCampo: string,
  valor: string,
  campos: CampoManifiesto[],
): string {
  const campo = campos.find((c) => c.nombre === nombreCampo);
  return campo?.catalogo.find((o) => o.valor === valor)?.etiqueta ?? valor;
}

/**
 * Lee una `Condicion` como una frase en castellano.
 *
 * Es la unica forma de que quien arma la regla pueda comprobar que dice lo que
 * queria decir: tres desplegables no se leen, una frase si.
 */
export function describirCondicion(
  condicion: Condicion | null,
  campos: CampoManifiesto[],
): string {
  if (!condicion) return "";
  const trozo = (c: { campo: string; operador: string; igual: string }) =>
    `${nombrarCampo(c.campo, campos)} ${VERBO[c.operador] ?? c.operador} ${nombrarValor(c.campo, c.igual, campos)}`;
  return [trozo(condicion), ...condicion.y.map(trozo)].join(" y ");
}

export type Pista = {
  /** Que tiene que hacer la persona, en imperativo y sin jerga. */
  instruccion: string;
  /** Un caso real del que copiar la forma. */
  ejemplo?: string;
  /** Texto de ejemplo dentro de la caja, para que no arranque en blanco. */
  marcador?: string;
};

/**
 * Instrucciones de llenado por codigo de validacion.
 *
 * Una caja vacia con la etiqueta "Valor" no ensena nada: quien nunca ha
 * capturado un tramite no sabe si se espera un numero, una fecha o una frase.
 * Los ejemplos son casos reales de tramites de Hidalgo, no marcadores de
 * relleno, para que se pueda copiar la forma.
 *
 * Un codigo sin pista escrita devuelve `null` y la tarjeta no inventa una
 * frase generica, que seria ruido.
 */
const PISTAS: Record<string, Pista> = {
  "META-01": {
    instruccion:
      "Escribe cuánto tarda el trámite desde que se solicita hasta que se entrega.",
    marcador: "15 días hábiles",
  },
  "META-02": {
    instruccion: "Escribe la dependencia que resuelve el trámite.",
    marcador: "Secretaría de Movilidad y Transporte",
  },
  "META-03": {
    instruccion:
      "Escribe el costo con el que se publica. Si es gratuito, escribe «Sin costo».",
    marcador: "Sin costo",
  },
  "META-04": {
    instruccion: "Escribe el nombre oficial con el que se publica el trámite.",
    marcador: "Constancia de Residencia",
  },
  "DIC-08": {
    instruccion:
      "Elige el campo que decide si este se ve, y con qué valor debe compararse.",
    ejemplo:
      "Muestra «RFC» solo cuando «Procedencia» sea igual a «Dependencia u organismo».",
    marcador: "Dependencia u organismo",
  },
  "MMD-04": {
    instruccion:
      "Elige el campo del formulario que la decisión consulta para tomar cada camino.",
    ejemplo:
      "La decisión «¿Modalidad de pago?» consulta el campo «Forma de pago».",
  },
  "MMD-03": {
    instruccion: "Elige quién realiza esta tarea dentro del trámite.",
    ejemplo: "La tarea «Revisar expediente» la hace «Periódico Oficial».",
  },
  "API-03": {
    instruccion:
      "Elige el campo del que depende este: el que hay que llenar antes.",
  },
  "DOC-02": {
    instruccion:
      "Cada {{variable}} de la plantilla debe ser un campo del Diccionario: de ahí saca GPM el valor al generar el PDF. Corrige el nombre o agrega el campo.",
    ejemplo: "«Estimado {{nombre}}, su folio es {{folio}}» — nombre y folio existen en el Diccionario.",
  },
  "DOC-03": {
    instruccion:
      "Solo se leen plantillas .md con {{variables}}. Un oficio escaneado adjúntalo como documento de apoyo y escribe su texto como plantilla.",
  },
};

/** La pista del codigo, o `null` si no hay una escrita para el. */
export function pistaDeCodigo(codigo: string): Pista | null {
  return PISTAS[codigo] ?? null;
}

/**
 * El nombre legible de la tarea que menciona un mensaje de `MMD-03`.
 *
 * El diagrama TO-BE escribe las tareas como «🔍 Usuario: Consultar información
 * del trámite (requisitos, tarifas por modalidad…)»: un emoji de adorno, el
 * carril delante y un parentesis con detalle operativo. Para preguntar «¿quién
 * hace esto?» basta el verbo y su objeto; lo demas alarga la pregunta sin
 * ayudar a responderla.
 *
 * Devuelve `null` si el mensaje no trae comillas, y entonces la tarjeta cae al
 * texto crudo en vez de inventar un nombre.
 */
export function nombreDeTarea(mensaje: string): string | null {
  const m = /«(.+?)»/s.exec(mensaje);
  return m ? limpiarEtiquetaDelDiagrama(m[1]) : null;
}

/**
 * La pregunta de la compuerta que menciona un mensaje de `MMD-04`.
 *
 * A diferencia de `MMD-03`, el compilador la envuelve en parentesis y no en
 * comillas: «la compuerta (🏛️ Periódico Oficial: ¿Es competencia del PO?) no
 * nombra ningun campo @@». Se limpia igual que una tarea.
 */
export function nombreDeCompuerta(mensaje: string): string | null {
  const m = /la compuerta \(([^)]*(?:\)[^)]*)*?)\)\s*no /s.exec(mensaje);
  return m ? limpiarEtiquetaDelDiagrama(m[1]) : null;
}

/**
 * Quita del texto de un nodo del diagrama lo que es adorno o andamiaje:
 * emojis, el carril delante («Usuario: …») y el detalle entre parentesis al
 * final. Lo que queda es lo que una persona diria.
 */
function limpiarEtiquetaDelDiagrama(bruto: string): string {
  let t = bruto.trim();
  // Emoji(s) de adorno al principio, con o sin selector de variacion.
  t = t.replace(/^(?:[\p{Extended_Pictographic}️‍]+\s*)+/u, "");
  // Carril delante: «Usuario: …», «Periódico Oficial: …».
  t = t.replace(/^[^:]{1,40}:\s*/u, "");
  // Detalle operativo entre parentesis al final.
  t = t.replace(/\s*\([^()]*\)\s*$/u, "");
  return t.trim();
}
