import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import RielEntrega from "./RielEntrega";
import type { Hueco } from "@/lib/types";

const HUECO: Hueco = {
  nivel: "falta_dato",
  codigo: "DIC-07",
  ubicacion: "p1::modalidad",
  mensaje: "el campo 'Modalidad' es select pero no se extrajo ninguna opción",
  propuesta: null,
};

function pintar(desbloqueado = false) {
  render(
    <RielEntrega
      sid={"a".repeat(16)}
      desbloqueado={desbloqueado}
      bloqueantes={desbloqueado ? [] : [HUECO]}
    />,
  );
}

it("dice si la puerta está abierta y qué la mantiene cerrada", () => {
  pintar();

  expect(screen.getByText("1 por revisar")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
});

it("con todo resuelto lo dice sin listar códigos", () => {
  pintar(true);

  expect(screen.getByText(/todo listo para entregar/i)).toBeInTheDocument();
  expect(screen.queryByText("DIC-07")).not.toBeInTheDocument();
});

it("apunta al panel de descargas, también con el expediente bloqueado", () => {
  // Las observaciones se bajan desde ahi y hacen mas falta justo cuando algo
  // bloquea: son lo que hay que mandarle a quien documento el tramite.
  pintar();

  expect(screen.getByRole("link", { name: /ver las descargas/i })).toHaveAttribute(
    "href",
    "#entrega",
  );
});

it("conserva las dos puertas que no son archivos", () => {
  // La aprobacion no tiene otra entrada en toda la SPA.
  pintar();

  expect(screen.getByRole("link", { name: /abrir simulador/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /abrir aprobación/i })).toBeInTheDocument();
});

it("ya no carga las descargas: se mudaron al panel", () => {
  pintar(true);

  expect(screen.queryByText(/\.gpm \(producción\)/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /descargar observaciones/i }),
  ).not.toBeInTheDocument();
});
