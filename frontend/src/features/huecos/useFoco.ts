import { useCallback, useState } from "react";

import type { Hueco } from "@/lib/types";

/** Misma clave estable que usa el wizard: `codigo|ubicacion`. */
const claveDe = (h: Hueco): string => `${h.codigo}|${h.ubicacion}`;

/**
 * Donde abrir el recorrido: en el primer hueco que pida algo.
 *
 * Publicacion abre con META-05 (homoclave) y META-03 (costo), dos tarjetas de
 * solo confirmar. Gastar ahi el primer golpe de vista del modo foco no ayuda:
 * se arranca en el primero accionable. Si todos son de confirmar, el primero.
 */
function primeroAccionable(huecos: Hueco[], resueltas: Set<string>): number {
  const pendiente = (h: Hueco) => !resueltas.has(claveDe(h));
  const i = huecos.findIndex((h) => pendiente(h) && h.nivel !== "por_confirmar");
  if (i >= 0) return i;
  const j = huecos.findIndex(pendiente);
  return j >= 0 ? j : 0;
}

/**
 * Recorrido de un hueco a la vez.
 *
 * Con 65 huecos —Publicacion en el Periodico Oficial— la lista completa no
 * ayuda: el analista pierde el sitio en cuanto hace scroll. Aqui solo hay uno
 * en foco y un indice al lado.
 *
 * Lo delicado es que la lista cambia bajo los pies: al resolver el hueco en
 * foco, la respuesta de la API llega sin el. Guardar solo el indice haria
 * saltar el foco en cada guardado; guardar solo la clave lo dejaria en la nada.
 * Se guardan los dos y se decide al pintar: si la clave sigue viva manda ella;
 * si desaparecio, manda la posicion que ocupaba —donde ahora esta el
 * siguiente— acotada al final de la lista.
 *
 * Todo se deriva durante el render: no hay efecto que sincronice nada, asi que
 * no hay renders en cascada ni un fotograma con el foco equivocado.
 */
export function useFoco(huecos: Hueco[], resueltas: Set<string>) {
  const [elegido, setElegido] = useState<{ clave: string; indice: number }>(
    () => {
      if (huecos.length === 0) return { clave: "", indice: 0 };
      const i = primeroAccionable(huecos, resueltas);
      return { clave: claveDe(huecos[i]), indice: i };
    },
  );

  const vivo = huecos.findIndex((h) => claveDe(h) === elegido.clave);
  const indice =
    huecos.length === 0
      ? 0
      : vivo >= 0
        ? vivo
        : Math.min(elegido.indice, huecos.length - 1);
  const actual = huecos.length > 0 ? (huecos[indice] ?? null) : null;

  const fijar = useCallback((lista: Hueco[], i: number) => {
    setElegido({ clave: claveDe(lista[i]), indice: i });
  }, []);

  /**
   * Avanza saltando lo ya resuelto: quien esta capturando quiere el siguiente
   * que pide algo, no volver a mirar lo que acaba de cerrar. Si no queda nada
   * pendiente en esa direccion, se queda donde esta.
   */
  const mover = useCallback(
    (paso: number) => {
      if (huecos.length === 0) return;
      for (let i = indice + paso; i >= 0 && i < huecos.length; i += paso) {
        if (!resueltas.has(claveDe(huecos[i]))) {
          fijar(huecos, i);
          return;
        }
      }
    },
    [huecos, indice, fijar, resueltas],
  );

  /**
   * Tras cerrar el hueco en foco: el proximo que siga abierto.
   *
   * Con la numeracion estable la tarjeta resuelta se queda en su sitio, asi
   * que el foco no se mueve solo: hay que moverlo a proposito o el analista
   * se queda mirando una palomita verde. Primero hacia adelante; si ya no hay
   * nada, hacia atras, para no dejar huecos abiertos arriba; si no queda
   * ninguno, se queda donde esta.
   */
  const siguientePendiente = useCallback(() => {
    const abierto = (i: number) => !resueltas.has(claveDe(huecos[i]));
    for (let i = indice + 1; i < huecos.length; i += 1) {
      if (abierto(i)) { fijar(huecos, i); return; }
    }
    for (let i = indice - 1; i >= 0; i -= 1) {
      if (abierto(i)) { fijar(huecos, i); return; }
    }
  }, [huecos, indice, fijar, resueltas]);

  return {
    actual,
    indice,
    total: huecos.length,
    siguiente: useCallback(() => mover(1), [mover]),
    anterior: useCallback(() => mover(-1), [mover]),
    siguientePendiente,
    irA: useCallback(
      (k: string) => {
        const i = huecos.findIndex((h) => claveDe(h) === k);
        if (i >= 0) fijar(huecos, i);
      },
      [huecos, fijar],
    ),
  };
}
