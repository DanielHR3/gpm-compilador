import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";
import { generateCssVariables, tokensWeb } from "@/lib/tokens";

describe("App (andamiaje SP1)", () => {
  it("muestra el botón 'Compilador GPM' (cadena React + shadcn + jsdom)", () => {
    render(<App />);
    expect(
      screen.getByRole("button", { name: "Compilador GPM" }),
    ).toBeInTheDocument();
  });

  it("los tokens salen de hidalgo-design-token-system (guinda #A02142)", () => {
    expect(tokensWeb.colors.brand.primary).toBe("#A02142");
    expect(tokensWeb.colors.action.primary).toBe("#A02142");
    expect(generateCssVariables()).toContain("--action-primary: #A02142");
  });
});
