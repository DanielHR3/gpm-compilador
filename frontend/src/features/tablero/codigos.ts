import { tituloDeCodigo } from "@/features/huecos/lenguaje";

/**
 * Nombre corto para la barra de un codigo. Reusa los titulos del wizard y
 * cubre los que alli no existen; si no conoce el codigo, lo deja tal cual.
 * Nada se inventa: un codigo cuyo significado no este verificado en el
 * extractor no entra aqui (INS-01 no es «falta el AS-IS»: es el TO-BE).
 */
const CORTOS: Record<string, string> = {
  "DIC-08": "Condición de visibilidad ambigua",
  "DIC-06": "Nombre técnico demasiado largo",
  "DIC-07": "Desplegable sin opciones",
  "API-05": "Endpoint con credencial",
};

export function nombreCorto(codigo: string): string {
  return CORTOS[codigo] ?? tituloDeCodigo(codigo);
}
