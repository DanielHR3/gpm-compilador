import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useUrlDeRevision } from "./useUrlDeRevision";

const SID = "b".repeat(16);

beforeEach(() => window.history.replaceState({}, "", "/"));

describe("useUrlDeRevision", () => {
  it("sin expediente abierto no toca la barra de direcciones", () => {
    renderHook(() => useUrlDeRevision(null));

    expect(window.location.pathname).toBe("/");
  });

  it("al abrir un expediente la ruta pasa a ser /revisar/:sid", () => {
    renderHook(() => useUrlDeRevision(SID));

    expect(window.location.pathname).toBe(`/revisar/${SID}`);
  });

  it("deja la pantalla anterior en el historial, para poder volver", () => {
    // Es el punto entero del arreglo: «Salir del Simulador» hace
    // history.back(), y sin una entrada propia se volvia a `/`.
    renderHook(() => useUrlDeRevision(SID));

    expect(window.history.state?.gpmcRevision).toBe(SID);
  });

  it("no vuelve a empujar si ya se esta en la ruta de ese expediente", () => {
    // Cada hueco resuelto reescribe el estado; empujar en cada uno llenaria el
    // historial de copias y haria falta pulsar Atras veinte veces para salir.
    const { rerender } = renderHook(({ s }) => useUrlDeRevision(s), {
      initialProps: { s: SID as string | null },
    });
    const largo = window.history.length;

    rerender({ s: SID });
    rerender({ s: SID });

    expect(window.history.length).toBe(largo);
    expect(window.location.pathname).toBe(`/revisar/${SID}`);
  });
});

describe("useUrlDeRevision desde una pantalla de carga", () => {
  it("reemplaza /expediente y /desde-as-is en vez de apilar: Atras no deja la direccion y la pantalla desfasadas", () => {
    for (const carga of ["/expediente", "/desde-as-is"]) {
      window.history.pushState({}, "", carga);
      const antes = window.history.length;
      renderHook(() => useUrlDeRevision("f".repeat(16)));
      expect(window.location.pathname).toBe(`/revisar/${"f".repeat(16)}`);
      expect(window.history.length).toBe(antes);
    }
    window.history.pushState({}, "", "/");
  });
});
