import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";
import { generateCssVariables, tokensWeb } from "@/lib/tokens";

describe("App (SPA SP1)", () => {
  it("arranca en la pantalla de carga de insumos ('Extraer' deshabilitado sin Diccionario)", () => {
    render(<App />);
    const btn = screen.getByRole("button", { name: /extraer/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toBeDisabled();
  });

  it("los tokens salen de hidalgo-design-token-system (guinda #A02142)", () => {
    expect(tokensWeb.colors.brand.primary).toBe("#A02142");
    expect(tokensWeb.colors.action.primary).toBe("#A02142");
    expect(generateCssVariables()).toContain("--action-primary: #A02142");
  });
});
