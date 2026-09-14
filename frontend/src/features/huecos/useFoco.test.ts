import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { Hueco } from "@/lib/types";

import { useFoco } from "./useFoco";

const h = (codigo: string): Hueco =>
  ({ nivel: "falta_dato", codigo, ubicacion: codigo, mensaje: "", propuesta: null }) as Hueco;

const lista = [h("A"), h("B"), h("C")];

/** La clave que usa el wizard: `codigo|ubicacion`. */
const k = (codigo: string) => `${codigo}|${codigo}`;

describe("useFoco", () => {
  test("arranca en el primero", () => {
    const { result } = renderHook(() => useFoco(lista));

    expect(result.current.actual?.codigo).toBe("A");
    expect(result.current.indice).toBe(0);
  });

  test("avanza y retrocede sin salirse de la lista", () => {
    const { result } = renderHook(() => useFoco(lista));

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
    const { result } = renderHook(() => useFoco(lista));

    act(() => result.current.irA(k("C")));

    expect(result.current.actual?.codigo).toBe("C");
  });

  test("cuando el hueco en foco se resuelve, el foco se queda en su lugar y toma el siguiente", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useFoco(items),
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
      ({ items }) => useFoco(items),
      { initialProps: { items: lista } },
    );

    act(() => result.current.irA(k("C")));
    rerender({ items: [h("A"), h("B")] });

    expect(result.current.actual?.codigo).toBe("B");
  });

  test("una lista vacia no tiene foco y no revienta", () => {
    const { result } = renderHook(() => useFoco([]));

    expect(result.current.actual).toBeNull();
    act(() => result.current.siguiente());
    expect(result.current.actual).toBeNull();
  });
});
