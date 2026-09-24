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
  leerCapacidades: vi.fn().mockResolvedValue({ proponer: true, motivo: null, pruebas: false }),
  leerToBe: vi.fn().mockRejectedValue(new Error("sin TO-BE")),
  leerGenerados: vi.fn(),
  decidirDocumento: vi.fn(),
  subirDocumento: vi.fn(),
  proponerExpediente: vi.fn(),
  leerPropuestas: vi.fn(),
  decidirPropuesta: vi.fn(),
  crearExpediente: vi.fn(),
  leerExpediente: vi.fn(),
  leerCatalogos: vi.fn().mockResolvedValue({
    catalogos: [],
    nota: "Solo se listan los endpoints que el compilador emite.",
  }),
  leerHistorial: vi.fn().mockResolvedValue({ tramites: [] }),
  leerTablero: vi.fn().mockResolvedValue({
    total_tramites: 0, dependencias: [], ultimo_registro: null, requisitos: [],
    campos_compartidos: [], huecos: [], complejidad: [], catalogos: [], actividad: [],
    indicadores: { requisitos_distintos: 0, promedio_campos: 0, promedio_huecos: 0, con_integracion: 0 },
    matriz_huecos: { filas: [], columnas: [], celdas: [], maximo: 0 },
    matriz_requisitos: { filas: [], columnas: [], celdas: [], maximo: 0 },
    niveles: [], metricas_max: {},
  }),
  resolver: vi.fn(),
  reconocer: vi.fn(),
  urlGpm: () => "/api/v1/x/gpm",
  urlManifiesto: () => "/api/v1/x/manifiesto",
  ErrorApi: class extends Error {
    status = 0;
    archivos?: string[];
  },
}));
vi.mock("mermaid", () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: "<svg></svg>" })) },
}));

describe("App (SPA SP1)", () => {
  it("la raiz es el Inicio con los dos caminos", () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: /qué tienes del trámite/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent("Inicio");
  });

  it("/expediente abre la carga de siempre con sus migas", () => {
    window.history.pushState({}, "", "/expediente");
    render(<App />);
    expect(screen.getByRole("button", { name: /extraer/i })).toBeDisabled();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent(/Inicio.*Expediente completo/);
    window.history.pushState({}, "", "/");
  });

  it("/desde-as-is abre la carga del AS-IS con sus migas", () => {
    window.history.pushState({}, "", "/desde-as-is");
    render(<App />);
    expect(screen.getByRole("button", { name: /proponer to-be y diccionario/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /migas de pan/i })).toHaveTextContent(/Inicio.*Solo AS-IS/);
    window.history.pushState({}, "", "/");
  });

  it("/revisar/:sid de una sesion de carpeta: migas «Expediente completo › Revisión»", async () => {
    const { leerExpediente, leerGenerados, ErrorApi } = await import("@/lib/api");
    vi.mocked(leerExpediente).mockResolvedValue({
      sid: "d".repeat(16), manifiesto: { tramite: { nombre: "X" }, pantallas: [], flujo: { tareas: [], conexiones: [] } },
      huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false,
    } as any);
    const e = new (ErrorApi as any)("no"); e.status = 404;
    vi.mocked(leerGenerados).mockRejectedValue(e);
    window.history.pushState({}, "", `/revisar/${"d".repeat(16)}`);
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: /migas de pan/i });
    await vi.waitFor(() => expect(nav).toHaveTextContent(/Expediente completo.*Revisión/));
    window.history.pushState({}, "", "/");
  });

  it("/revisar/:sid con /generados caido por red: migas «Inicio › Revisión», sin romper", async () => {
    const { leerExpediente, leerGenerados } = await import("@/lib/api");
    vi.mocked(leerExpediente).mockResolvedValue({
      sid: "e".repeat(16), manifiesto: { tramite: { nombre: "X" }, pantallas: [], flujo: { tareas: [], conexiones: [] } },
      huecos: [], estimacion: {}, problemas: [], tieneVistas: false, reconocidos: [], adjuntos: [], propuestasPendientes: false,
    } as any);
    vi.mocked(leerGenerados).mockRejectedValue(new TypeError("Failed to fetch"));
    window.history.pushState({}, "", `/revisar/${"e".repeat(16)}`);
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: /migas de pan/i });
    await vi.waitFor(() => expect(nav).toHaveTextContent(/Revisión/));
    expect(nav).not.toHaveTextContent(/Expediente completo|Solo AS-IS/);
    window.history.pushState({}, "", "/");
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

  it("en /catalogos pinta la seccion de catalogos y no la carga de insumos", async () => {
    // Otras pruebas de este archivo asumen pathname "/": la ruta se fija
    // aqui y se restaura al final, no en un beforeEach global.
    window.history.replaceState({}, "", "/catalogos");
    try {
      render(<App />);
      // `AppHeader` pinta el titulo en un <span>, asi que el unico heading
      // llamado «Catálogos» es el <h1> de la vista.
      expect(await screen.findByRole("heading", { name: /catálogos/i })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /extraer/i })).toBeNull();
    } finally {
      window.history.replaceState({}, "", "/");
    }
  });

  it("en /historial pinta el historial y no la carga de insumos (antes era HTML del servidor)", async () => {
    window.history.replaceState({}, "", "/historial");
    try {
      render(<App />);
      expect(await screen.findByRole("heading", { name: /historial/i })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /extraer/i })).toBeNull();
    } finally {
      window.history.replaceState({}, "", "/");
    }
  });

  it("en /tablero pinta el tablero y no la carga de insumos", async () => {
    window.history.replaceState({}, "", "/tablero");
    try {
      render(<App />);
      expect(await screen.findByRole("heading", { name: /^tablero$/i })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /extraer/i })).toBeNull();
    } finally {
      window.history.replaceState({}, "", "/");
    }
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

describe("App y la Fase 3", () => {
  it("un 409 en /revisar/:sid abre la pantalla de Propuestas en vez de decir que expiro", async () => {
    const { leerExpediente, leerGenerados, ErrorApi } = await import("@/lib/api");
    const e = new (ErrorApi as any)("en propuestas"); e.status = 409;
    vi.mocked(leerExpediente).mockRejectedValue(e);
    vi.mocked(leerGenerados).mockResolvedValue({ estado: "generando", motivo: null, nombre: "Constancia", diccionario: null, tobe: null });
    window.history.pushState({}, "", `/revisar/${"c".repeat(16)}`);
    render(<App />);
    expect(await screen.findByText(/uno o dos minutos/i)).toBeInTheDocument();
    expect(screen.queryByText(/la sesion expiro/i)).not.toBeInTheDocument();
    window.history.pushState({}, "", "/");
  });
});
