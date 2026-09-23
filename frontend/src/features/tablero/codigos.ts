import { tituloDeCodigo } from "@/features/huecos/lenguaje";

/**
 * Nombre corto de un codigo para el tablero. Es el MISMO titulo que ve el
 * analista en el wizard (`lenguaje.ts`): una sola redaccion que mantener,
 * y la misma persona no ve dos nombres para el mismo hallazgo en dos
 * pantallas. Si `lenguaje.ts` no conoce el codigo, sale tal cual.
 */
export function nombreCorto(codigo: string): string {
  return tituloDeCodigo(codigo);
}
