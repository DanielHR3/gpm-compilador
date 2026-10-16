import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import PreviaManifiesto from "./PreviaManifiesto";

const MANIFIESTO = {
  tramite: { nombre: "Constancia de Residencia", dependencia: "Secretaría General",
             ruts: { tiempo_entrega: "3 días hábiles" } },
  actores: [{ id: "ciudadano", nombre: "Ciudadano" }, { id: "funcionario", nombre: "Funcionario", tipo: "grupo" }],
  pantallas: [
    { id: "p1", nombre: "Solicitud", actor: "ciudadano", campos: [
      { nombre: "curp", etiqueta: "CURP", obligatorio: true },
      { nombre: "dictamen", etiqueta: "Dictamen", tipo: "select", obligatorio: true,
        catalogo: [{ etiqueta: "Aprobado", valor: "aprobado" }, { etiqueta: "Rechazado", valor: "rechazado" }] },
      { nombre: "motivo", etiqueta: "Motivo", tipo: "textarea", obligatorio: false,
        condicion_visible: { campo: "dictamen", igual: "rechazado" } },
    ] },
    { id: "p2", nombre: "Emisión", actor: "funcionario", campos: [] },
  ],
  flujo: {
    tareas: [
      { id: "P1", nombre: "Solicitud", actor: "ciudadano", inicial: true, pantallas: [{ id: "p1" }] },
      { id: "P2", nombre: "Emisión", actor: "funcionario", terminal: true, pantallas: [{ id: "p2" }] },
    ],
    conexiones: [{ de: "P1", a: "P2", cuando: { campo: "dictamen", igual: "aprobado" } }],
  },
};

it("pinta el trámite, los actores, las pantallas con sus campos y el flujo", () => {
  render(<PreviaManifiesto manifiesto={MANIFIESTO} />);

  expect(screen.getByRole("heading", { name: /Constancia de Residencia/ })).toBeInTheDocument();
  expect(screen.getByText("Secretaría General")).toBeInTheDocument();
  expect(screen.getByText("3 días hábiles")).toBeInTheDocument();

  const actores = screen.getByRole("region", { name: /actores/i });
  expect(within(actores).getByText("Ciudadano")).toBeInTheDocument();
  expect(within(actores).getByText(/Funcionario/)).toHaveTextContent(/grupo/);

  // Las pantallas se pintan como en Propuestas: una tarjeta por pantalla y
  // una chica por campo, con el actor en el titulo.
  const p1 = screen.getByRole("article", { name: /Pantalla 1 · Ciudadano · Solicitud/ });
  expect(within(p1).getByText("CURP")).toBeInTheDocument();
  expect(within(p1).getByText("Aprobado · Rechazado")).toBeInTheDocument();
  expect(within(p1).getByText(/Visible solo si dictamen = rechazado/)).toBeInTheDocument();
  expect(within(screen.getByRole("article", { name: /Emisión/ })).getByText(/sin campos/i)).toBeInTheDocument();

  const flujo = screen.getByRole("region", { name: /flujo/i });
  expect(within(flujo).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    expect.stringMatching(/Solicitud.*Ciudadano.*inicia/i),
    expect.stringMatching(/Emisión.*Funcionario.*termina/i),
    expect.stringMatching(/Solicitud → Emisión.*dictamen = aprobado/),
  ]);
});

it("con un manifiesto sin flujo ni actores no revienta", () => {
  render(<PreviaManifiesto manifiesto={{ tramite: { nombre: "X" }, pantallas: [] }} />);
  expect(screen.getByRole("heading", { name: "X" })).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: /flujo/i })).toBeNull();
});
