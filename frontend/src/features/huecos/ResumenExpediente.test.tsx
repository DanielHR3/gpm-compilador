import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import ResumenExpediente from "./ResumenExpediente";

const manifiesto = {
  tramite: { nombre: "Publicación en el Periódico Oficial", dependencia: "Secretaría de Gobierno" },
  actores: [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }],
  pantallas: [
    { id: "p1", campos: [{ nombre: "curp" }, { nombre: "rfc", condicion_visible: { campo: "x" } }] },
    { id: "p2", campos: [{ nombre: "dom" }] },
  ],
  flujo: { tareas: [{ id: "t1" }, { id: "t2" }], conexiones: [{ cuando: "x" }] },
};

it("encabeza con el trámite y su dependencia", () => {
  render(<ResumenExpediente manifiesto={manifiesto} estimacion={{}} />);

  expect(
    screen.getByRole("heading", { name: "Publicación en el Periódico Oficial" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Secretaría de Gobierno")).toBeInTheDocument();
});

it("devuelve las cifras de lo que el compilador leyó del documento", () => {
  const { container } = render(
    <ResumenExpediente manifiesto={manifiesto} estimacion={{}} />,
  );

  const cifras = within(container).getAllByRole("figure");
  expect(cifras.map((f) => f.getAttribute("aria-label"))).toEqual([
    "2 pantallas", "3 campos", "2 tareas", "4 responsables",
  ]);
});

it("dice cuánto costará construirlo, que es la consecuencia del documento", () => {
  render(
    <ResumenExpediente
      manifiesto={manifiesto}
      estimacion={{ nivel: "Complejo", dias: "40 a 50 dias habiles" }}
    />,
  );

  expect(screen.getByText(/40 a 50 dias habiles/)).toBeInTheDocument();
  // El nivel se presenta tal cual, sin anteponerle "complejidad": el backend
  // lo escribe como adjetivo y salia "complejidad complejo".
  expect(screen.getByText("Complejo")).toBeInTheDocument();
  expect(screen.queryByText(/complejidad/i)).toBeNull();
});

it("sin nombre confirmado no inventa un encabezado", () => {
  render(
    <ResumenExpediente
      manifiesto={{ ...manifiesto, tramite: { nombre: "[por confirmar]" } }}
      estimacion={{}}
    />,
  );

  expect(screen.getByRole("heading", { name: /trámite sin nombre/i })).toBeInTheDocument();
});
