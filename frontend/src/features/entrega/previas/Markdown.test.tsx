import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import Markdown from "./Markdown";

it("pinta encabezados, listas, citas, negritas y párrafos del documento de observaciones", () => {
  const texto = [
    "# Observaciones al expediente — Constancia",
    "",
    "## Diccionario  (2)",
    "",
    "### Pantalla «Solicitud»",
    "",
    "**CURP**",
    "",
    "Falta el **catálogo** del campo.",
    "",
    "> En el Diccionario se escribió: «Sí/No»",
    "",
    "- primera viñeta",
    "- segunda viñeta",
    "",
    "1. paso uno",
    "2. paso dos",
    "",
    "_Requiere convenio._",
  ].join("\n");

  render(<Markdown texto={texto} />);

  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Observaciones al expediente");
  expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Diccionario (2)");
  expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("Pantalla «Solicitud»");
  expect(screen.getByText("CURP").tagName).toBe("STRONG");
  expect(screen.getByText("catálogo").tagName).toBe("STRONG");
  expect(screen.getByText(/En el Diccionario se escribió/).closest("blockquote")).not.toBeNull();
  expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "primera viñeta", "segunda viñeta", "paso uno", "paso dos",
  ]);
  expect(screen.getByText("Requiere convenio.").tagName).toBe("EM");
});

it("no interpreta HTML que venga dentro del texto", () => {
  render(<Markdown texto={"<img src=x onerror=alert(1)> **ok**"} />);
  expect(document.querySelector("img")).toBeNull();
  expect(screen.getByText(/<img/)).toBeInTheDocument();
});
