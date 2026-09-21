import type { CampoManifiesto, Condicion, Hueco } from "@/lib/types";

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
  "DIC-02": "Lista declarada como pendiente",
  "DIC-06": "Nombre técnico demasiado largo",
  "DIC-07": "Lista sin opciones",
  "DIC-08": "Visibilidad de un campo",
  "DIC-09": "Nombre técnico repetido",
  "API-03": "Campo del que depende",
  "API-04": "Conexión con otro sistema",
  "DOC-02": "Variable sin campo en un documento",
  "DOC-03": "Plantilla de documento ilegible",
  "DOC-04": "En qué tarea se genera el documento",
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
      "Elige el campo que decide si este se ve, y el valor que hace que aparezca.",
    ejemplo:
      "Muestra «RFC» solo cuando «Procedencia» sea igual a «Dependencia u organismo».",
    // Sin marcador a proposito: el valor del ejemplo se pintaba como
    // placeholder de la caja y parecia una respuesta ya puesta. Cae en el
    // neutro de ConstructorRegla ("este valor").
  },
  "MMD-04": {
    instruccion:
      "Elige el campo del formulario que la decisión mira para saber por dónde " +
      "sigue el trámite.",
    ejemplo:
      "La decisión «¿Modalidad de pago?» mira el campo «Forma de pago».",
  },
  "MMD-03": {
    instruccion: "Elige quién realiza esta tarea dentro del trámite.",
    ejemplo: "La tarea «Revisar expediente» la hace «Periódico Oficial».",
  },
  "API-03": {
    instruccion:
      "Elige el campo que hay que llenar antes que este, porque de él salen " +
      "sus opciones.",
  },
  "DOC-02": {
    instruccion:
      "Cada {{variable}} de la plantilla debe ser un campo del Diccionario: de ahí saca GPM el valor al generar el PDF. Corrige el nombre o agrega el campo.",
    ejemplo: "«Estimado {{nombre}}, su folio es {{folio}}» — nombre y folio existen en el Diccionario.",
  },
  "DOC-04": {
    instruccion:
      "El documento quedó en la primera tarea del flujo que ya tiene todos sus " +
      "datos. Si está bien, confírmalo; si debe salir en otra (por ejemplo, " +
      "después de una firma), ajústalo en la plataforma.",
  },
  "DOC-03": {
    instruccion:
      "La plantilla se lee en Word, PDF con texto o .md, con {{variables}}. Un oficio escaneado o una foto no se pueden leer: adjúntalo como documento de apoyo y sube su texto en Word.",
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

/**
 * Redaccion humana del mensaje de un hueco.
 *
 * El backend escribe sus mensajes para el equipo tecnico: dicen lo que hizo el
 * compilador ("no se emite", "se emite como campo de texto") y nombran cosas
 * que solo existen dentro del codigo (`type_of_person`, `@@campo`, la columna
 * `campo.nombre`). En la CLI eso esta bien y no se toca. En la pantalla de
 * revision lo lee quien documenta el tramite, y para esa persona el mensaje
 * tiene que decir otras tres cosas: que paso en el insumo, que consecuencia
 * tiene para el tramite publicado, y que le toca hacer.
 *
 * Lo ultimo solo cuando la tarjeta no lo dice ya por su cuenta: los codigos con
 * `Pista` escrita (ver PISTAS) ya traen el imperativo debajo, y repetirlo hace
 * que la tarjeta se lea como si mandara dos veces.
 */
type Redaccion = (mensaje: string, nivel: string) => string | null;

/** "1 decisión" / "2 decisiones", que en una frase se nota. */
function contar(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`;
}

/**
 * Una redaccion de texto fijo, anclada a un trozo del mensaje que la origina.
 *
 * El ancla no es adorno: los mensajes sin datos interpolados tientan a devolver
 * la prosa sin mirar el crudo, y entonces un cambio de cadena en el extractor
 * no rompe nada visible -- la pantalla sigue contando la version vieja de los
 * hechos. Con ancla, ese caso cae al crudo igual que los demas.
 */
const fijo = (ancla: RegExp, texto: string): Redaccion => (mensaje) =>
  ancla.test(mensaje) ? texto : null;

const REDACCIONES: Record<string, Redaccion> = {
  // --- Metadatos: mensajes sin datos interpolados, texto fijo. ---------------
  "META-01": fijo(
    /no se encontro el tiempo de respuesta/,
    "El AS-IS no dice cuánto tarda el trámite desde que se solicita hasta " +
      "que se entrega.",
  ),
  "META-02": fijo(
    /no se encontro la dependencia/,
    "El AS-IS no dice qué dependencia resuelve el trámite. Hasta que alguien " +
      "lo escriba, la ficha sale con «[por confirmar]» en ese lugar.",
  ),
  "META-03": fijo(
    /no se encontro el costo declarado/,
    "En ningún documento aparece el costo, así que el trámite saldría " +
      "publicado como gratuito.",
  ),
  "META-04": fijo(
    /no se pudo determinar el nombre/,
    "No hay de dónde sacar el nombre del trámite: ni el AS-IS ni el nombre " +
      "de la carpeta lo dicen.",
  ),
  "META-05": fijo(
    /no se encontro homoclave/,
    "No aparece la homoclave en ningún documento. En un trámite nuevo es lo " +
      "normal: la asigna GPM cuando se publica.",
  ),
  "META-06": fijo(
    /no se encontro 'A quien va dirigido'/,
    "Ningún documento dice a quién va dirigido el trámite, así que quedará " +
      "abierto a personas físicas y morales por igual.",
  ),

  // --- Diccionario: hay que sacar del crudo la etiqueta del campo. ----------
  "DIC-02": (mensaje) => {
    const m = /el catálogo de '([^']+)' está declarado como pendiente/.exec(mensaje);
    if (!m) return null;
    return (
      `En el Diccionario, la lista de «${m[1]}» quedó marcada como pendiente. ` +
      "Tal como está, el campo saldría sin opciones que elegir. Escribe " +
      "cuáles son."
    );
  },
  "DIC-07": (mensaje) => {
    const m = /el campo '([^']+)' es \w+ pero no se extrajo ninguna opción/.exec(mensaje);
    if (!m) return null;
    return (
      `«${m[1]}» debería ser una lista, pero en el Diccionario no trae ninguna ` +
      "opción: ni en «Catálogo de Valores» ni en «Límite/Especificaciones». " +
      "Tal como está, saldría como una caja de texto donde cada quien escribe " +
      "lo que quiera. Escribe las opciones."
    );
  },

  // --- Flujo: el diagrama y el Diccionario contados en castellano. ----------
  "FLU-01": (mensaje) => {
    const m = /tiene (\d+) compuerta/.exec(mensaje);
    if (!m) return null;
    return (
      `El diagrama TO-BE tiene ${contar(Number(m[1]), "decisión", "decisiones")} ` +
      "que el trámite no reproduce. Suele ser por una de tres cosas: la " +
      "decisión no dice qué campo hay que mirar, alguna de sus salidas no " +
      "coincide con ninguna opción de ese campo, o las tareas del diagrama no " +
      "corresponden con las pantallas. Tal como está, el trámite saldría en " +
      "línea recta, sin caminos alternativos."
    );
  },
  "FLU-02": (mensaje) => {
    const m = /tiene (\d+) tareas y el Diccionario (\d+) pantallas/.exec(mensaje);
    if (!m) return null;
    return (
      `El diagrama TO-BE tiene ${m[1]} tareas y el Diccionario ${m[2]} ` +
      "pantallas. Como no coinciden, no hay forma de saber qué pantalla le " +
      "toca a cada tarea. Revisa cuál de los dos documentos quedó incompleto."
    );
  },
  "FLU-03": (mensaje) => {
    const m = /\((\d+) compuerta\(s\), (\d+) conexión\(es\) con condición\)\.[^:]*:\s*(.+)$/s.exec(mensaje);
    if (!m) return null;
    return (
      "El trámite quedó con caminos alternativos, tal como los dibuja el " +
      `diagrama TO-BE: ${contar(Number(m[1]), "decisión", "decisiones")} y ` +
      `${contar(Number(m[2]), "salida", "salidas")} con condición. Revisa que a ` +
      `cada tarea le haya tocado la pantalla correcta: ${m[3]}`
    );
  },

  // --- Documentos: dos mensajes distintos bajo el mismo codigo. -------------
  "DOC-04": (mensaje) => {
    const huerfano = /el documento «(.+?)» no se genera en ninguna tarea:.*?\((.+?)\)\./s.exec(mensaje);
    if (huerfano) {
      return (
        `«${huerfano[1]}» necesita los datos ${huerfano[2]}. Ninguna tarea del ` +
        "flujo llega a tenerlos todos, así que el documento nunca se " +
        "generaría. Revisa que las pantallas donde se capturan esos datos " +
        "estén en el flujo."
      );
    }
    const colocado = /el documento «(.+?)» se genera al terminar la tarea «(.+?)»/s.exec(mensaje);
    if (!colocado) return null;
    return (
      `«${colocado[1]}» se generará al terminar la tarea «${colocado[2]}»: es la ` +
      "primera del flujo en la que ya están todos sus datos."
    );
  },
};

/**
 * El mensaje del hueco dicho como lo diria una persona.
 *
 * Un codigo sin redaccion escrita —o un mensaje que no tiene la forma que la
 * redaccion espera, porque el backend cambio la cadena— devuelve el crudo. Feo
 * pero cierto: es preferible a inventar una frase que ya no describe lo que
 * paso.
 */
export function redactarHueco(hueco: Hueco): string {
  return REDACCIONES[hueco.codigo]?.(hueco.mensaje, hueco.nivel) ?? hueco.mensaje;
}

/**
 * Un ejemplo de regla de visibilidad armado con los campos DE ESTE expediente.
 *
 * El ejemplo escrito en `PISTAS` habla de «RFC» y «Procedencia», que son campos
 * de otro tramite. Ensena la forma de la regla, pero quien lo abre busca esos
 * nombres en su pantalla y no los encuentra; por eso estaba plegado. Con los
 * campos propios el ejemplo deja de ser ajeno y se entiende de una lectura.
 *
 * No pretende ser la regla correcta —si el compilador supiera cual es, no
 * habria hueco que resolver—: solo ensena la forma con nombres reconocibles.
 *
 * Devuelve `null` cuando no hay con que armarlo (ningun campo de lista, o el
 * unico candidato es el campo mismo). Quien llama cae entonces al ejemplo
 * generico, que sigue siendo mejor que ninguno.
 */
export function ejemploDeVisibilidad(
  campos: CampoManifiesto[],
  objetivo: MensajeVisibilidad | null,
): string | null {
  if (!objetivo?.etiqueta) return null;
  const candidato = campos.find(
    (c) =>
      c.nombre !== objetivo.interno &&
      c.etiqueta !== "" &&
      c.catalogo.some((o) => o.etiqueta !== ""),
  );
  if (!candidato) return null;
  const valor = candidato.catalogo.find((o) => o.etiqueta !== "")!;
  return (
    `Muestra «${objetivo.etiqueta}» solo cuando «${candidato.etiqueta}» sea ` +
    `igual a «${valor.etiqueta}».`
  );
}
