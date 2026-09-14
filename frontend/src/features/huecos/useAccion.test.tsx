import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import { ErrorApi } from "@/lib/api";

import { useAccion } from "./useAccion";

/** Promesa que el test resuelve o rechaza a mano, para observar el estado intermedio. */
function diferida<T>() {
  let resolver!: (v: T) => void;
  let rechazar!: (e: unknown) => void;
  const promesa = new Promise<T>((res, rej) => {
    resolver = res;
    rechazar = rej;
  });
  return { promesa, resolver, rechazar };
}

describe("useAccion", () => {
  test("marca `guardando` mientras la peticion esta en vuelo", async () => {
    const { promesa, resolver } = diferida<string>();
    const { result } = renderHook(() => useAccion());

    expect(result.current.guardando).toBe(false);

    act(() => {
      void result.current.ejecutar(() => promesa);
    });
    expect(result.current.guardando).toBe(true);

    await act(async () => {
      resolver("ok");
      await promesa;
    });
    await waitFor(() => expect(result.current.guardando).toBe(false));
  });

  test("captura un ErrorApi en `error` sin propagar la excepcion", async () => {
    const { result } = renderHook(() => useAccion());
    const fallo = new ErrorApi(422, "la ubicacion no existe");

    let devuelto: unknown = "sin-tocar";
    await act(async () => {
      devuelto = await result.current.ejecutar(() => Promise.reject(fallo));
    });

    expect(devuelto).toBeUndefined();
    expect(result.current.error).toBe(fallo);
    expect(result.current.guardando).toBe(false);
  });

  test("ignora una segunda llamada mientras la primera sigue en vuelo", async () => {
    const { promesa, resolver } = diferida<string>();
    let llamadas = 0;
    const { result } = renderHook(() => useAccion());

    const accion = () => {
      llamadas += 1;
      return promesa;
    };

    act(() => {
      void result.current.ejecutar(accion);
    });
    act(() => {
      void result.current.ejecutar(accion);
    });

    expect(llamadas).toBe(1);

    await act(async () => {
      resolver("ok");
      await promesa;
    });
  });

  test("limpia el error anterior al reintentar", async () => {
    const { result } = renderHook(() => useAccion());

    await act(async () => {
      await result.current.ejecutar(() =>
        Promise.reject(new ErrorApi(500, "se cayo")),
      );
    });
    expect(result.current.error).not.toBeNull();

    await act(async () => {
      await result.current.ejecutar(() => Promise.resolve("ok"));
    });
    expect(result.current.error).toBeNull();
  });

  test("deja escapar un error que no sea de la API", async () => {
    const { result } = renderHook(() => useAccion());
    const bug = new TypeError("undefined is not a function");

    await expect(
      act(async () => {
        await result.current.ejecutar(() => Promise.reject(bug));
      }),
    ).rejects.toBe(bug);
  });
});

/** Componente minimo que ejerce el hook a traves de la UI real. */
function Sonda({ accion }: { accion: () => Promise<unknown> }) {
  const { ejecutar, guardando } = useAccion();
  return (
    <>
      <Toaster />
      <button type="button" disabled={guardando} onClick={() => void ejecutar(accion)}>
        Guardar
      </button>
    </>
  );
}

describe("useAccion — avisos", () => {
  test("anuncia el mensaje de la API en un toast cuando la peticion falla", async () => {
    render(
      <Sonda
        accion={() => Promise.reject(new ErrorApi(409, "el expediente expiro"))}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("el expediente expiro")).toBeInTheDocument();
  });
});
