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
