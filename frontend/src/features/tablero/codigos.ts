import { tituloDeCodigo } from "@/features/huecos/lenguaje";

/**
 * Nombre corto para la barra de un codigo. Reusa los titulos del wizard y
 * cubre los que alli no existen; si no conoce el codigo, lo deja tal cual.
 */
const CORTOS: Record<string, string> = {
  "DIC-08": "Condición de visibilidad ambigua",
  "DIC-06": "Nombre técnico demasiado largo",
  "DIC-07": "Desplegable sin opciones",
  "INS-01": "Falta el AS-IS",
  "INS-02": "Falta el TO-BE",
  "API-05": "Endpoint con credencial",
};

export function nombreCorto(codigo: string): string {
  return CORTOS[codigo] ?? tituloDeCodigo(codigo);
}
