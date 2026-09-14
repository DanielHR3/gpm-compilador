import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { useListaConSalida } from "./useListaConSalida";

type Item = { id: string };
const claveDe = (i: Item) => i.id;

const a = { id: "a" };
const b = { id: "b" };
const c = { id: "c" };

describe("useListaConSalida", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  test("devuelve los items intactos mientras nada desaparece", () => {
    const { result } = renderHook(() => useListaConSalida([a, b], claveDe, 200));

    expect(result.current.map((e) => e.item)).toEqual([a, b]);
    expect(result.current.every((e) => !e.saliendo)).toBe(true);
  });

  test("retiene el item que desaparecio, marcado como saliendo", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useListaConSalida(items, claveDe, 200),
      { initialProps: { items: [a, b] } },
    );

    rerender({ items: [b] });

    expect(result.current.map((e) => e.item.id)).toEqual(["a", "b"]);
    expect(result.current[0].saliendo).toBe(true);
    expect(result.current[1].saliendo).toBe(false);
  });

  test("lo suelta cuando se cumple el plazo", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useListaConSalida(items, claveDe, 200),
      { initialProps: { items: [a, b] } },
    );

    rerender({ items: [b] });
    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(result.current.map((e) => e.item.id)).toEqual(["b"]);
  });

  test("conserva la posicion que ocupaba el item que sale", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useListaConSalida(items, claveDe, 200),
      { initialProps: { items: [a, b, c] } },
    );

    rerender({ items: [a, c] });

    expect(result.current.map((e) => e.item.id)).toEqual(["a", "b", "c"]);
    expect(result.current[1].saliendo).toBe(true);
  });

  test("un item que reaparece antes del plazo deja de estar saliendo", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useListaConSalida(items, claveDe, 200),
      { initialProps: { items: [a, b] } },
    );

    rerender({ items: [b] });
    expect(result.current[0].saliendo).toBe(true);

    rerender({ items: [a, b] });
    expect(result.current.map((e) => e.item.id)).toEqual(["a", "b"]);
    expect(result.current.every((e) => !e.saliendo)).toBe(true);
  });
});
