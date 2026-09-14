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
function primeroAccionable(huecos: Hueco[]): number {
  const i = huecos.findIndex((h) => h.nivel !== "por_confirmar");
  return i >= 0 ? i : 0;
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
export function useFoco(huecos: Hueco[]) {
  const [elegido, setElegido] = useState<{ clave: string; indice: number }>(
    () => {
      if (huecos.length === 0) return { clave: "", indice: 0 };
      const i = primeroAccionable(huecos);
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

  const mover = useCallback(
    (paso: number) => {
      if (huecos.length === 0) return;
      fijar(huecos, Math.min(Math.max(indice + paso, 0), huecos.length - 1));
    },
    [huecos, indice, fijar],
  );

  return {
    actual,
    indice,
    total: huecos.length,
    siguiente: useCallback(() => mover(1), [mover]),
    anterior: useCallback(() => mover(-1), [mover]),
    irA: useCallback(
      (k: string) => {
        const i = huecos.findIndex((h) => claveDe(h) === k);
        if (i >= 0) fijar(huecos, i);
      },
      [huecos, fijar],
    ),
  };
}
