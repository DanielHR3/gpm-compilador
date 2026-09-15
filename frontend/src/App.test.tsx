import { render, screen, within } from "@testing-library/react";
import { toast } from "sonner";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { generateCssVariables, tokensWeb } from "@/lib/tokens";

// `App` ahora importa `leerExpediente` (deep-link `/revisar/:sid`) y arrastra
// `WizardHuecos`; se stubea todo `@/lib/api` para que ningun `fetch` real
// dispare desde el arbol. En jsdom `pathname` es `/`, asi que el `useEffect`
// del deep-link sale sin llamar a nada.
vi.mock("@/lib/api", () => ({
  crearExpediente: vi.fn(),
  leerExpediente: vi.fn(),
  resolver: vi.fn(),
  reconocer: vi.fn(),
  urlGpm: () => "/api/v1/x/gpm",
  urlManifiesto: () => "/api/v1/x/manifiesto",
  ErrorApi: class extends Error {
    status = 0;
    archivos?: string[];
  },
}));

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

  it("monta el area de avisos, para que los toasts tengan donde salir", async () => {
    render(<App />);

    toast.success("el expediente se guardo");

    expect(
      await screen.findByText("el expediente se guardo"),
    ).toBeInTheDocument();
  });

  it("la navegación del proceso acompaña a la pantalla de carga", () => {
    render(<App />);

    const nav = screen.getByRole("navigation", { name: /proceso/i });
    expect(nav).toBeInTheDocument();
    expect(
      within(nav).getByRole("link", { current: "step" }),
    ).toHaveTextContent(/insumos/i);
  });
});
