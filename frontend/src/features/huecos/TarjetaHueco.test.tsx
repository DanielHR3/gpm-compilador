import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolver: vi.fn(),
  reconocer: vi.fn().mockResolvedValue({ huecos: [], reconocidos: [] }),
  resolverDic08: vi.fn(),
  camposDelManifiesto: () => [],
  leerCompuerta: vi.fn(),
  resolverCompuertaCampo: vi.fn(),
  resolverCompuertaRamas: vi.fn(),
  ErrorApi: class ErrorApi extends Error {},
}));

import TarjetaHueco from "./TarjetaHueco";

const sid = "a".repeat(16);

it("DIC-08: el enlace 'o lo configuro a mano' llama reconocer con codigo y ubicacion", async () => {
  const { reconocer } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::domicilio",
        mensaje: "no se pudo interpretar: «visible si es de otro estado»",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={onResuelto}
    />,
  );
  await userEvent.click(
    screen.getByRole("button", { name: /o lo configuro a mano/i }),
  );
  expect(reconocer).toHaveBeenCalledWith(sid, "DIC-08", "p1::domicilio");
  expect(onResuelto).toHaveBeenCalled();
});

it("MMD-04: el enlace 'o lo configuro a mano' llama reconocer con codigo y ubicacion", async () => {
  const { reconocer } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "MMD-04",
        ubicacion: "G",
        mensaje: "la compuerta no nombra ningun campo @@",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={onResuelto}
    />,
  );
  await userEvent.click(
    screen.getByRole("button", { name: /o lo configuro a mano/i }),
  );
  expect(reconocer).toHaveBeenCalledWith(sid, "MMD-04", "G");
  expect(onResuelto).toHaveBeenCalled();
});

it("META-04: dos clics seguidos en Guardar mandan una sola resolucion", async () => {
  const { resolver } = await import("@/lib/api");
  // La peticion queda en vuelo hasta que el test la suelte: el segundo clic
  // ocurre mientras la primera sigue abierta, que es el caso real del bug.
  let soltar!: (v: unknown) => void;
  vi.mocked(resolver).mockReturnValue(
    new Promise((res) => {
      soltar = res;
    }) as any,
  );

  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "META-04",
        ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  await userEvent.type(
    screen.getByLabelText(/nombre del tramite/i),
    "Constancia de residencia",
  );
  const boton = screen.getByRole("button", { name: /guardar/i });
  await userEvent.click(boton);
  await userEvent.click(boton);

  expect(resolver).toHaveBeenCalledTimes(1);
  expect(boton).toBeDisabled();

  soltar({ manifiesto: {}, huecos: [] });
});

it("META-04: mientras guarda, el boton lo dice y se anuncia como ocupado", async () => {
  const { resolver } = await import("@/lib/api");
  let soltar!: (v: unknown) => void;
  vi.mocked(resolver).mockReturnValue(
    new Promise((res) => {
      soltar = res;
    }) as any,
  );

  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "META-04",
        ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  await userEvent.type(
    screen.getByLabelText(/nombre del tramite/i),
    "Constancia de residencia",
  );
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));

  const ocupado = screen.getByRole("button", { name: /guardando/i });
  expect(ocupado).toHaveAttribute("aria-busy", "true");

  soltar({ manifiesto: {}, huecos: [] });
});
