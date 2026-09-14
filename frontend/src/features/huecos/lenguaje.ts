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
  "DIC-02": "Tipo de campo",
  "DIC-06": "Nombre técnico demasiado largo",
  "DIC-07": "Lista sin opciones",
  "DIC-08": "Visibilidad de un campo",
  "API-03": "Campo del que depende",
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
