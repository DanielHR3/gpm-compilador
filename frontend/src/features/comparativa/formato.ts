import type { ComparativaOut, OrigenValor, RequisitoComparado } from "@/lib/types";

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
