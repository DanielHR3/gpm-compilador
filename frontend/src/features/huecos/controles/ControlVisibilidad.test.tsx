import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  camposDelManifiesto: () => [
    { nombre: "estado", etiqueta: "Estado", catalogo: [] },
  ],
}));

import ControlVisibilidad from "./ControlVisibilidad";

it("muestra la frase cruda y al guardar llama resolverDic08", async () => {
  const { resolverDic08 } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(
    <ControlVisibilidad
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::domicilio",
        mensaje: "no se pudo interpretar: «visible si es de otro estado»",
        propuesta: null,
      }}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={onResuelto}
    />,
  );
  // La frase cruda del Diccionario vive ahora en el detalle tecnico, plegado.
  expect(screen.getByText(/otro estado/)).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText(/campo de la condición 1/i), "estado");
  await userEvent.type(screen.getByLabelText(/valor de la condición 1/i), "hidalgo");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolverDic08).toHaveBeenCalledWith(
    "a".repeat(16),
    "p1::domicilio",
    expect.objectContaining({ campo: "estado", igual: "hidalgo" }),
  );
  expect(onResuelto).toHaveBeenCalled();
});

it("encabeza con una pregunta en castellano y nombra el campo por su etiqueta", () => {
  render(
    <ControlVisibilidad
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::rfc_dependencia",
        mensaje:
          "la condición de visibilidad de 'RFC de la Dependencia' (rfc_dependencia) no se pudo interpretar: «Visible solo cuando `@@procedencia` = Dependencia u organismo»; configúrala a mano",
        propuesta: null,
      }}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
    />,
  );

  expect(
    screen.getByRole("heading", { name: /cuándo debe verse «RFC de la Dependencia»/i }),
  ).toBeInTheDocument();
});

it("guarda lo tecnico plegado, sin perderlo", () => {
  render(
    <ControlVisibilidad
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::rfc_dependencia",
        mensaje:
          "la condición de visibilidad de 'RFC de la Dependencia' (rfc_dependencia) no se pudo interpretar: «Visible solo cuando `@@procedencia` = Dependencia u organismo»; configúrala a mano",
        propuesta: null,
      }}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
    />,
  );

  const detalle = screen.getByText(/ver detalle técnico/i).closest("details");
  expect(detalle).not.toBeNull();
  expect(detalle).not.toHaveAttribute("open");
  expect(detalle).toHaveTextContent("DIC-08");
  expect(detalle).toHaveTextContent("rfc_dependencia");
});

it("lee la regla armada como una frase, para poder comprobarla", async () => {
  render(
    <ControlVisibilidad
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::domicilio",
        mensaje: "no se pudo interpretar: «visible si es de otro estado»",
        propuesta: null,
      }}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
    />,
  );

  await userEvent.selectOptions(screen.getByLabelText(/campo de la condición 1/i), "estado");
  await userEvent.type(screen.getByLabelText(/valor de la condición 1/i), "Hidalgo");

  expect(screen.getByText(/Estado es igual a Hidalgo/)).toBeInTheDocument();
});

it("explica que hacer y ensena un ejemplo real antes de pedir la regla", () => {
  render(
    <ControlVisibilidad
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::rfc",
        mensaje: "no se pudo interpretar: «x»",
        propuesta: null,
      }}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
    />,
  );

  expect(screen.getByText(/Elige el campo que decide si este se ve/i)).toBeInTheDocument();
  expect(
    screen.getByText(/Muestra «RFC» solo cuando «Procedencia» sea igual a/i),
  ).toBeInTheDocument();
});
