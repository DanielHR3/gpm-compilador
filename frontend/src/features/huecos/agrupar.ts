import type { Hueco } from "@/lib/types";

export type GrupoHuecos = {
  nivel: Hueco["nivel"];
  rotulo: string;
  huecos: Hueco[];
  total: number;
};

/**
 * De mas urgente a menos. El orden es el del producto, no el alfabetico: lo
 * que cierra la puerta del `.gpm` va primero porque es lo unico que impide
 * entregar.
 */
const ORDEN: { nivel: Hueco["nivel"]; rotulo: string }[] = [
  { nivel: "bloqueante", rotulo: "Bloquean la descarga" },
  { nivel: "falta_dato", rotulo: "Falta un dato" },
  { nivel: "por_confirmar", rotulo: "Solo confirmar" },
];

/**
 * Parte los huecos en grupos por severidad.
 *
 * Con un tramite chico la lista plana se lee bien; con 65 huecos —como
 * Publicacion en el Periodico Oficial— no hay forma de saber que es urgente y
 * que es tramite. Agrupar convierte la severidad en algo que se ve sin leer.
 *
 * Dentro de cada grupo se respeta el orden en que llegaron: el compilador ya
 * los emite en un orden con sentido (metadatos, diccionario, flujo) y
 * reordenarlos aqui solo desorientaria a quien ya recorrio la lista una vez.
 */
export function agruparPorNivel(huecos: Hueco[]): GrupoHuecos[] {
  const grupos: GrupoHuecos[] = [];
  for (const { nivel, rotulo } of ORDEN) {
    const propios = huecos.filter((h) => h.nivel === nivel);
    if (propios.length === 0) continue;
    grupos.push({ nivel, rotulo, huecos: propios, total: propios.length });
  }
  return grupos;
}

export type CuentaCodigo = { codigo: string; total: number };

/**
 * Recuento por codigo de validacion, de mas frecuente a menos.
 *
 * El riel de entrega listaba un renglon por hueco con su mensaje completo. Con
 * 62 pendientes eso es una pared de texto que empuja los enlaces fuera de la
 * pantalla y no dice nada que la tarjeta no diga mejor. Un recuento —«MMD-03
 * x42»— si informa: dice de que tipo es el trabajo que falta.
 *
 * El desempate alfabetico evita que dos codigos con la misma cuenta se
 * intercambien de lugar entre renders.
 */
export function contarPorCodigo(huecos: Hueco[]): CuentaCodigo[] {
  const cuenta = new Map<string, number>();
  for (const h of huecos) cuenta.set(h.codigo, (cuenta.get(h.codigo) ?? 0) + 1);
  return [...cuenta.entries()]
    .map(([codigo, total]) => ({ codigo, total }))
    .sort((a, b) => b.total - a.total || a.codigo.localeCompare(b.codigo));
}
