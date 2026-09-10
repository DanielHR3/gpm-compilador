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
