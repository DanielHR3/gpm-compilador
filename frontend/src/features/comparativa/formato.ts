import type {
  ClaseElemento, ComparativaOut, MejoraTramite, OrigenValor, RequisitoComparado,
} from "@/lib/types";

/**
 * Como se dice cada cosa de la comparativa. Aparte de los componentes porque
 * el documento descargable dice lo mismo desde el servidor
 * (`comparativa/documento.py`): si una etiqueta cambia aqui, cambia alla.
 */

const NUMERO = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 1 });

/** El porcentaje es de reduccion: positivo baja (−), negativo sube (+). */
export function textoCambio(pct: number): string {
  return `${pct >= 0 ? "−" : "+"}${NUMERO.format(Math.abs(pct))} %`;
}

const ORIGEN: Record<OrigenValor, string> = {
  contado: "contado",
  leido: "leído",
  declarado: "declarado",
  revisado: "revisado",
  propuesto: "propuesto por el agente",
  sin_dato: "sin dato",
};

export function etiquetaOrigen(o: OrigenValor): string {
  return ORIGEN[o];
}

const DESTINO: Record<RequisitoComparado["destino"], string> = {
  conservado: "Se conserva",
  eliminado: "Se elimina",
  sin_destino: "Sin destino",
  nuevo: "Nuevo en el TO-BE",
};

export function etiquetaDestino(d: RequisitoComparado["destino"]): string {
  return DESTINO[d];
}

const VEREDICTO: Record<ComparativaOut["veredicto"], string> = {
  reduce: "Reduce",
  mixto: "Mixto",
  no_reduce: "No reduce",
  sin_medida: "No se puede medir",
};

export function tituloVeredicto(v: ComparativaOut["veredicto"]): string {
  return VEREDICTO[v];
}

/** La cifra global nunca viaja sola: sin su base, 47 % no dice de que. */
export function textoGlobal(c: ComparativaOut): string {
  if (c.porcentaje_global === null) {
    return `Sin cifra global: solo ${c.base_global} de ${c.total_metricas} métricas se pueden comparar`;
  }
  // Negativa quiere decir que las metricas medidas crecieron en promedio.
  const cifra =
    c.porcentaje_global >= 0
      ? `${NUMERO.format(c.porcentaje_global)} %`
      : `−${NUMERO.format(Math.abs(c.porcentaje_global))} % (aumento neto)`;
  return `${cifra} sobre ${c.base_global} de ${c.total_metricas} métricas`;
}

/** Ancho en porcentaje del carril. Minimo 1: un cero sigue siendo una barra. */
export function anchoBarra(valor: number, tope: number): number {
  if (tope <= 0) return 1;
  return Math.min(100, Math.max(1, Math.round((100 * valor) / tope)));
}

/** Orden de lectura de la tabla de eliminacion: primero lo que se quito. */
export const ORDEN_ELEMENTOS: ClaseElemento[] = [
  "elimina", "cambia", "conserva", "sin_decision", "otro",
];

const CLASE: Record<ClaseElemento, string> = {
  elimina: "Se elimina",
  cambia: "Cambia",
  conserva: "Se conserva",
  sin_decision: "Sin decisión",
  otro: "Otra respuesta",
};

export function nombreDeClase(c: ClaseElemento): string {
  return CLASE[c];
}

/**
 * El color sigue a la clase. Son tres de los cuatro tonos de la paleta
 * categorica de «Documentos del tramite» (`--dest-*`, validada con `dataviz`):
 * aqui tambien son identidades, no magnitudes. Lo que el equipo no decidio va
 * en gris, igual que «sin destino» alla.
 */
export function colorDeClase(c: ClaseElemento): string {
  if (c === "elimina") return "var(--dest-elimina)";
  if (c === "cambia") return "var(--dest-sistema)";
  if (c === "conserva") return "var(--dest-conserva)";
  return "var(--muted-foreground)";
}

const REQUIERE: Record<MejoraTramite["requiere"], string> = {
  "": "",
  servicio_publico: "Se puede hacer hoy con un servicio público en línea",
  convenio: "Requiere un convenio o un sistema de la dependencia",
};

export function requiereEnPalabras(r: MejoraTramite["requiere"]): string {
  return REQUIERE[r] ?? "";
}

const TIPO_MEJORA: Record<MejoraTramite["tipo"], string> = {
  documento: "Documento",
  paso: "Paso",
  captura: "Captura de datos",
  visita: "Visita",
  friccion: "Fricción",
  tiempo: "Tiempo",
};

export function tipoDeMejora(t: MejoraTramite["tipo"]): string {
  return TIPO_MEJORA[t] ?? "Fricción";
}

export function fuenteEnPalabras(f: MejoraTramite["fuente"]): string {
  return f === "as_is" ? "Análisis AS-IS" : f === "to_be" ? "Propuesta TO-BE" : "";
}
