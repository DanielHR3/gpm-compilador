import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import ControlTexto from "./ControlTexto";

it("META-01 dice que escribir y propone un ejemplo dentro de la caja", () => {
  render(
    <ControlTexto
      hueco={{
        nivel: "falta_dato",
        codigo: "META-01",
        ubicacion: "metadatos",
        mensaje: "no se encontro el tiempo de respuesta declarado",
        propuesta: null,
      }}
      onConfirmar={vi.fn()}
    />,
  );

  expect(screen.getByText(/cuánto tarda el trámite/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/tiempo de resolucion/i)).toHaveAttribute(
    "placeholder",
    "15 días hábiles",
  );
});

it("META-04 propone un nombre de tramite de verdad", () => {
  render(
    <ControlTexto
      hueco={{
        nivel: "falta_dato",
        codigo: "META-04",
        ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite",
        propuesta: null,
      }}
      onConfirmar={vi.fn()}
    />,
  );

  expect(screen.getByLabelText(/nombre del tramite/i)).toHaveAttribute(
    "placeholder",
    "Constancia de Residencia",
  );
});
