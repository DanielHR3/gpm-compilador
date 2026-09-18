import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  urlGpm: () => "/api/v1/x/gpm",
  urlManifiesto: () => "/api/v1/x/manifiesto",
}));

import RielEntrega from "./RielEntrega";
import type { EstadoExpediente, Hueco } from "@/lib/types";

const HUECO: Hueco = {
  nivel: "falta_dato",
  codigo: "DIC-07",
  ubicacion: "p1::modalidad",
  mensaje:
    "el campo 'Modalidad' es select pero no se extrajo ninguna opción (ni en " +
    "'Catálogo de Valores' ni en 'Límite/Especificaciones'); el compilador lo " +
    "emite como campo de texto",
  propuesta: null,
};

const estado = {
  sid: "a".repeat(16),
  manifiesto: { tramite: { nombre: "Trámite de Prueba" }, pantallas: [{ id: "p1", nombre: "Solicitud", campos: [] }] },
  huecos: [HUECO],
} as unknown as EstadoExpediente;

function pintar() {
  render(
    <RielEntrega
      sid={estado.sid}
      desbloqueado={false}
      bloqueantes={[HUECO]}
      tieneVistas={false}
      fraseBloqueo={(n) => `Faltan ${n}`}
      estado={estado}
    />,
  );
}

it("ofrece descargar las observaciones, debajo del manifiesto", () => {
  pintar();

  const enlaces = screen.getAllByRole("link").map((a) => a.textContent);
  const boton = screen.getByRole("button", { name: /descargar observaciones/i });

  expect(boton).toBeInTheDocument();
  expect(enlaces.some((t) => /descargar manifiesto/i.test(t ?? ""))).toBe(true);
});

it("las observaciones se pueden descargar aunque el expediente esté bloqueado", () => {
  // Es justo cuando mas falta hacen: lo que bloquea es lo que hay que mandar.
  pintar();

  expect(
    screen.getByRole("button", { name: /descargar observaciones/i }),
  ).toBeEnabled();
});

it("al pulsarlo arma un archivo con el nombre del trámite", async () => {
  const creados: Blob[] = [];
  const urlOriginal = URL.createObjectURL;
  URL.createObjectURL = vi.fn((b: Blob) => {
    creados.push(b);
    return "blob:falso";
  }) as unknown as typeof URL.createObjectURL;
  URL.revokeObjectURL = vi.fn();
  pintar();

  await userEvent.click(screen.getByRole("button", { name: /descargar observaciones/i }));

  expect(creados).toHaveLength(1);
  expect(await creados[0].text()).toContain("Trámite de Prueba");
  URL.createObjectURL = urlOriginal;
});
