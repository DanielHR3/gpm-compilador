import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import AvisoModoPruebas from "./AvisoModoPruebas";

it("dice que es una prueba interna y con que se procesa", () => {
  render(<AvisoModoPruebas />);
  const aviso = screen.getByRole("note", { name: /modo de pruebas/i });
  expect(aviso).toHaveTextContent(/uso interno de la DSA y la DGT/);
  expect(aviso).toHaveTextContent(/Gemini/);
  expect(aviso).toHaveTextContent(/credenciales de OpenAI/);
});
