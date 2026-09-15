import { useEffect, useRef, useState } from "react";

export type Entrada<T> = { item: T; saliendo: boolean };

/**
 * Mantiene montado, durante `ms`, el item que acaba de desaparecer de `items`,
 * y lo devuelve marcado como `saliendo` en la posicion que ocupaba.
 *
 * Existe porque al resolver un hueco la respuesta de la API trae la lista ya
 * sin el: React lo desmonta en el mismo commit y no queda nada a lo que
 * aplicarle una animacion de salida. Retenerlo aqui —y no en la tarjeta— evita
 * que cada tarjeta tenga que conocer el ciclo de vida de la lista.
 *
 * El plazo debe ser el de la animacion: si se queda corto la tarjeta salta, y
 * si se pasa, la lista se siente trabada.
 */
export function useListaConSalida<T>(
  items: T[],
  claveDe: (item: T) => string,
  ms: number,
): Entrada<T>[] {
  // Lo que se pinto la vez anterior, para saber que desaparecio y donde estaba.
  const previo = useRef<T[]>(items);
  const [saliendo, setSaliendo] = useState<Map<string, { item: T; indice: number }>>(
    new Map(),
  );

  const claves = new Set(items.map(claveDe));

  useEffect(() => {
    const idos = previo.current
      .map((item, indice) => ({ item, indice }))
      .filter(({ item }) => !claves.has(claveDe(item)));

    previo.current = items;
    if (idos.length === 0) {
      // Un item que reaparecio antes del plazo deja de estar saliendo.
      setSaliendo((antes) => {
        if (antes.size === 0) return antes;
        const resto = new Map(antes);
        for (const k of claves) resto.delete(k);
        return resto.size === antes.size ? antes : resto;
      });
      return;
    }

    setSaliendo((antes) => {
      const siguiente = new Map(antes);
      for (const ido of idos) siguiente.set(claveDe(ido.item), ido);
      return siguiente;
    });

    const t = setTimeout(() => {
      setSaliendo((antes) => {
        const resto = new Map(antes);
        for (const ido of idos) resto.delete(claveDe(ido.item));
        return resto;
      });
    }, ms);
    return () => clearTimeout(t);
    // `claves` se deriva de `items`; basta con observar la lista.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, ms]);

  if (saliendo.size === 0) {
    return items.map((item) => ({ item, saliendo: false }));
  }

  // Se reinsertan los que salen en el hueco que dejaron, de menor a mayor
  // indice, para que la tarjeta no salte de sitio mientras se desvanece.
  const salida: Entrada<T>[] = items
    .filter((item) => !saliendo.has(claveDe(item)))
    .map((item) => ({ item, saliendo: false }));
  const pendientes = [...saliendo.values()].sort((x, y) => x.indice - y.indice);
  for (const { item, indice } of pendientes) {
    salida.splice(Math.min(indice, salida.length), 0, { item, saliendo: true });
  }
  return salida;
}
