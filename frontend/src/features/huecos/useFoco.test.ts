import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { Hueco } from "@/lib/types";

import { useFoco } from "./useFoco";

const h = (codigo: string, nivel: Hueco["nivel"] = "falta_dato"): Hueco =>
  ({ nivel, codigo, ubicacion: codigo, mensaje: "", propuesta: null }) as Hueco;

const lista = [h("A"), h("B"), h("C")];

/** La clave que usa el wizard: `codigo|ubicacion`. */
const k = (codigo: string) => `${codigo}|${codigo}`;

describe("useFoco", () => {
  test("arranca en el primero", () => {
    const { result } = renderHook(() => useFoco(lista, new Set()));

    expect(result.current.actual?.codigo).toBe("A");
    expect(result.current.indice).toBe(0);
  });

  test("avanza y retrocede sin salirse de la lista", () => {
    const { result } = renderHook(() => useFoco(lista, new Set()));

    act(() => result.current.siguiente());
    act(() => result.current.siguiente());
    act(() => result.current.siguiente());
    expect(result.current.indice).toBe(2);

    act(() => result.current.anterior());
    act(() => result.current.anterior());
    act(() => result.current.anterior());
    expect(result.current.indice).toBe(0);
  });

  test("puede saltar directo a un hueco por su clave", () => {
    const { result } = renderHook(() => useFoco(lista, new Set()));

    act(() => result.current.irA(k("C")));

    expect(result.current.actual?.codigo).toBe("C");
  });

  test("cuando el hueco en foco se resuelve, el foco se queda en su lugar y toma el siguiente", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useFoco(items, new Set()),
      { initialProps: { items: lista } },
    );

    act(() => result.current.irA(k("B")));
    expect(result.current.actual?.codigo).toBe("B");

    // B desaparece de la lista: el foco NO debe saltar al principio.
    rerender({ items: [h("A"), h("C")] });

    expect(result.current.actual?.codigo).toBe("C");
  });

  test("si se resuelve el ultimo, el foco retrocede en vez de quedar en la nada", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useFoco(items, new Set()),
      { initialProps: { items: lista } },
    );

    act(() => result.current.irA(k("C")));
    rerender({ items: [h("A"), h("B")] });

    expect(result.current.actual?.codigo).toBe("B");
  });

  test("una lista vacia no tiene foco y no revienta", () => {
    const { result } = renderHook(() => useFoco([], new Set()));

    expect(result.current.actual).toBeNull();
    act(() => result.current.siguiente());
    expect(result.current.actual).toBeNull();
  });

  test("arranca en el primer hueco accionable, no en uno de solo confirmar", () => {
    // Publicacion abre con META-05 (homoclave), una tarjeta sin nada que hacer:
    // gastar ahi el primer golpe de vista del modo foco no ayuda a nadie.
    const { result } = renderHook(() =>
      useFoco([h("META-05", "por_confirmar"), h("META-03", "por_confirmar"), h("DIC-08")], new Set()),
    );

    expect(result.current.actual?.codigo).toBe("DIC-08");
  });

  test("si todo es de solo confirmar, arranca en el primero y no se queda sin foco", () => {
    const { result } = renderHook(() =>
      useFoco([h("META-05", "por_confirmar"), h("META-03", "por_confirmar")], new Set()),
    );

    expect(result.current.actual?.codigo).toBe("META-05");
  });

  test("la numeracion NO se recorre al resolver: la lista es la original", () => {
    // Antes la lista encogia y el hueco 32 pasaba a ser el 31: el analista
    // perdia la referencia justo despues de guardar.
    const { result, rerender } = renderHook(
      ({ resueltas }) => useFoco(lista, resueltas),
      { initialProps: { resueltas: new Set<string>() } },
    );

    act(() => result.current.irA(k("A")));
    rerender({ resueltas: new Set([k("A")]) });

    expect(result.current.total).toBe(3);
  });

  test("avanzar salta los que ya estan resueltos", () => {
    const { result } = renderHook(() => useFoco(lista, new Set([k("B")])));

    act(() => result.current.irA(k("A")));
    act(() => result.current.siguiente());

    expect(result.current.actual?.codigo).toBe("C");
  });

  test("arranca en el primero pendiente, no en uno ya resuelto", () => {
    const { result } = renderHook(() => useFoco(lista, new Set([k("A")])));

    expect(result.current.actual?.codigo).toBe("B");
  });

  test("al cerrar el hueco en foco, siguientePendiente salta al proximo que sigue abierto", () => {
    // Con la numeracion estable, la tarjeta resuelta se queda en su sitio: el
    // foco tiene que moverse a proposito o el analista se queda mirando una
    // palomita verde.
    const { result, rerender } = renderHook(
      ({ resueltas }) => useFoco(lista, resueltas),
      { initialProps: { resueltas: new Set<string>() } },
    );
    act(() => result.current.irA(k("A")));

    rerender({ resueltas: new Set([k("A")]) });
    act(() => result.current.siguientePendiente());

    expect(result.current.actual?.codigo).toBe("B");
  });

  test("si no queda nada pendiente hacia adelante, vuelve al primero pendiente hacia atras", () => {
    // Terminar el ultimo no debe dejar al analista en una palomita mientras
    // arriba siguen huecos abiertos.
    const { result, rerender } = renderHook(
      ({ resueltas }) => useFoco(lista, resueltas),
      { initialProps: { resueltas: new Set([k("B")]) } },
    );
    act(() => result.current.irA(k("C")));

    rerender({ resueltas: new Set([k("B"), k("C")]) });
    act(() => result.current.siguientePendiente());

    expect(result.current.actual?.codigo).toBe("A");
  });

  test("si ya no queda ninguno pendiente, se queda donde esta sin reventar", () => {
    const { result, rerender } = renderHook(
      ({ resueltas }) => useFoco(lista, resueltas),
      { initialProps: { resueltas: new Set([k("A"), k("B")]) } },
    );
    act(() => result.current.irA(k("C")));

    rerender({ resueltas: new Set([k("A"), k("B"), k("C")]) });
    act(() => result.current.siguientePendiente());

    expect(result.current.actual?.codigo).toBe("C");
  });
});
