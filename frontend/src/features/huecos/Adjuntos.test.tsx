import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ urlAdjunto: (s: string, n: string) => `/api/v1/expedientes/${s}/adjuntos/${n}` }));

import Adjuntos from "./Adjuntos";

const sid = "a".repeat(16);

it("sin adjuntos no ocupa sitio en la pantalla", () => {
  const { container } = render(<Adjuntos sid={sid} adjuntos={[]} />);
  expect(container).toBeEmptyDOMElement();
});

it("enseña el diagrama junto a los huecos, que es donde hace falta", async () => {
  render(
    <Adjuntos
      sid={sid}
      adjuntos={[{ nombre: "TO BE.png", tipo: "imagen" }]}
    />,
  );

  await userEvent.click(screen.getByRole("button", { name: /TO BE\.png/ }));

  const img = screen.getByRole("img", { name: /TO BE\.png/ });
  expect(img).toHaveAttribute("src", `/api/v1/expedientes/${sid}/adjuntos/TO BE.png`);
});

it("un PDF se abre aparte: no se puede mirar de reojo", () => {
  render(
    <Adjuntos sid={sid} adjuntos={[{ nombre: "Requisitos.pdf", tipo: "pdf" }]} />,
  );

  const enlace = screen.getByRole("link", { name: /Requisitos\.pdf/ });
  expect(enlace).toHaveAttribute("target", "_blank");
  expect(enlace).toHaveAttribute("rel", expect.stringContaining("noreferrer"));
});
