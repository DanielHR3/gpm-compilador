/**
 * El ejemplo de la tarjeta DIC-08 hablaba de «RFC» y «Procedencia», campos de
 * otro tramite. Quien lo abria los buscaba en su pantalla y no los encontraba.
 * Aqui se fija que, cuando el expediente tiene con que, el ejemplo se arme con
 * sus propios campos.
 */
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  camposDelManifiesto: () => [
    { nombre: "curp", etiqueta: "CURP", catalogo: [] },
    {
      nombre: "estatus_tramite",
      etiqueta: "Estatus del Trámite",
      catalogo: [{ valor: "pendiente", etiqueta: "Pendiente de regularización" }],
    },
  ],
}));

import ControlVisibilidad from "./ControlVisibilidad";

const HUECO = {
  nivel: "falta_dato" as const,
  codigo: "DIC-08",
  ubicacion: "p2::notificacion_sancion",
  mensaje:
    "la condición de visibilidad de 'Notificación de Sanción' " +
    "(notificacion_sancion) no se pudo interpretar: «Visible solo si " +
    "\"Estatus del Trámite\" = Pendiente de regularización»; configúrala a mano",
  propuesta: null,
};

function pintar() {
  render(
    <ControlVisibilidad
      hueco={HUECO}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
    />,
  );
}

it("el ejemplo usa los campos del propio expediente", () => {
  pintar();

  expect(
    screen.getByText(
      /Muestra «Notificación de Sanción» solo cuando «Estatus del Trámite» sea igual a «Pendiente de regularización»/,
    ),
  ).toBeInTheDocument();
});

it("ya no ensena los campos de otro tramite", () => {
  pintar();

  expect(screen.queryByText(/Procedencia/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Dependencia u organismo/)).not.toBeInTheDocument();
});

it("la fila de la regla se lee como una frase que nombra el campo", () => {
  pintar();

  // "Muéstralo solo cuando:" no nombraba nada: el "lo" obligaba a recordar de
  // que campo hablaba la tarjeta mientras se elegia en tres desplegables.
  expect(
    screen.getByText(/Muestra «Notificación de Sanción» solo cuando$/),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Muéstralo solo cuando/)).not.toBeInTheDocument();
});

it("los operadores se leen como continuacion de la frase, no como comparaciones", () => {
  pintar();

  const comparacion = screen.getByLabelText(/comparación de la condición 1/i);
  const textos = [...comparacion.querySelectorAll("option")].map((o) => o.textContent);

  expect(textos).toEqual(["sea", "no sea"]);
});

it("el boton de anadir condicion continua la frase", () => {
  pintar();

  expect(
    screen.getByRole("button", { name: /y además debe cumplirse que/i }),
  ).toBeInTheDocument();
});

it("la frase de confirmacion nombra el campo en vez de decir «el campo»", async () => {
  const { default: userEvent } = await import("@testing-library/user-event");
  pintar();

  await userEvent.selectOptions(
    screen.getByLabelText(/campo de la condición 1/i),
    "estatus_tramite",
  );
  await userEvent.selectOptions(
    screen.getByLabelText(/valor de la condición 1/i),
    "pendiente",
  );

  expect(
    screen.getByText(/«Notificación de Sanción» se mostrará solo si/),
  ).toBeInTheDocument();
  expect(screen.queryByText(/el campo se muestra solo si/)).not.toBeInTheDocument();
});
