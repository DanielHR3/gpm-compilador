import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import WizardHuecos from "./WizardHuecos";

vi.mock("@/lib/api", () => ({
  resolver: vi.fn(), reconocer: vi.fn(),
  urlGpm: () => "/api/v1/x/gpm", urlManifiesto: () => "/api/v1/x/manifiesto",
}));

const estado = {
  sid: "a".repeat(16),
  manifiesto: { actores: [{ id: "ciudadano", nombre: "Ciudadano" }], pantallas: [], flujo: { tareas: [] } },
  huecos: [
    { nivel: "falta_dato", codigo: "META-01", ubicacion: "metadatos", mensaje: "falta el tiempo", propuesta: null },
    { nivel: "por_confirmar", codigo: "META-05", ubicacion: "metadatos", mensaje: "sin homoclave", propuesta: null },
  ],
  estimacion: {}, problemas: [], tieneVistas: false,
};

it("una tarjeta por hueco y barra de progreso", () => {
  render(<WizardHuecos estado={estado as any} onEstado={() => {}} />);
  // El mensaje aparece en la tarjeta y (al bloquear) en el motivo de bloqueo.
  expect(screen.getAllByText(/falta el tiempo/).length).toBeGreaterThan(0);
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});

it("un bloqueante de codigo desconocido no deja sin salida: lista el motivo y conserva el simulador, sin enlace al .gpm", () => {
  const est = {
    ...estado,
    huecos: [
      {
        nivel: "bloqueante",
        codigo: "INS-01",
        ubicacion: "",
        mensaje: "no se encontro la Propuesta TO-BE",
        propuesta: null,
      },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  // El motivo del bloqueo se explica en pantalla.
  expect(
    screen.getByText(/Faltan 1 huecos por resolver antes de descargar el \.gpm/),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText(/no se encontro la Propuesta TO-BE/).length,
  ).toBeGreaterThan(0);
  // Hay salida: el simulador sigue enlazado.
  expect(
    screen.getByRole("link", { name: /simulador/i }),
  ).toHaveAttribute("href", "/simulador/" + "a".repeat(16));
  // El .gpm SI esta cerrado.
  expect(screen.queryByRole("link", { name: /\.gpm/i })).toBeNull();
});

it("pinta los avisos del analisis de flujo (problemas[])", () => {
  const est = { ...estado, problemas: ["ciclo sin salida en la tarea 3"] };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  expect(
    screen.getByText(/ciclo sin salida en la tarea 3/),
  ).toBeInTheDocument();
});

it("META-01 se resuelve por la API y sube el estado, sin recargar", async () => {
  const { resolver } = await import("@/lib/api");
  (resolver as any).mockResolvedValue({ ...estado, huecos: [estado.huecos[1]] });
  const onEstado = vi.fn();
  render(<WizardHuecos estado={estado as any} onEstado={onEstado} />);
  await userEvent.type(screen.getByLabelText(/tiempo/i), "5 dias habiles");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolver).toHaveBeenCalledWith("a".repeat(16),
    [{ tipo: "meta01", ubicacion: "metadatos", valor: "5 dias habiles" }]);
  expect(onEstado).toHaveBeenCalled();
});

it("META-04 (nombre del tramite) se resuelve con un ControlTexto real, no solo el boton de reconocer", async () => {
  const { resolver } = await import("@/lib/api");
  const est = {
    ...estado,
    huecos: [
      { nivel: "falta_dato", codigo: "META-04", ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite", propuesta: null },
    ],
  };
  (resolver as any).mockResolvedValue({ ...est, huecos: [] });
  const onEstado = vi.fn();
  render(<WizardHuecos estado={est as any} onEstado={onEstado} />);
  await userEvent.type(screen.getByLabelText(/nombre/i), "Constancia de residencia");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolver).toHaveBeenCalledWith("a".repeat(16),
    [{ tipo: "meta04", ubicacion: "metadatos", valor: "Constancia de residencia" }]);
  expect(onEstado).toHaveBeenCalled();
});

it("MMD-03 muestra un ControlActor con los actores del manifiesto", async () => {
  const est = {
    ...estado,
    huecos: [
      { nivel: "falta_dato", codigo: "MMD-03", ubicacion: "flujo.tareas[0]", mensaje: "quien resuelve", propuesta: null },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  const combo = screen.getByRole("combobox");
  expect(combo).toBeInTheDocument();
  await userEvent.click(combo);
  expect(await screen.findByRole("option", { name: "Ciudadano" })).toBeInTheDocument();
});

// El carril del diagrama dejo de ser bloqueante: MMD-03 llega colapsado en un
// solo hueco `por_confirmar` sobre "flujo" (ver `_colapsar_mmd03` en
// `extractores/expediente.py`). Ese hueco no nombra ninguna tarea, asi que un
// ControlActor sobre el mandaria `ubicacion: "flujo"` a `/resolver` y el
// backend contestaria 422 -- el mismo callejon sin salida que se acaba de
// cerrar. Se muestra como informativo.
it("MMD-03 colapsado (por_confirmar) no ofrece ControlActor", () => {
  const est = {
    ...estado,
    huecos: [
      { nivel: "por_confirmar", codigo: "MMD-03", ubicacion: "flujo",
        mensaje: "4 nodo(s) del diagrama TO-BE no declaran carril", propuesta: null },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(screen.getByText(/no declaran carril/)).toBeInTheDocument();
});

it("MMD-03 por nodo ofrece tambien la salida 'lo configuro a mano'", () => {
  const est = {
    ...estado,
    huecos: [
      { nivel: "falta_dato", codigo: "MMD-03", ubicacion: "T1", mensaje: "quien resuelve", propuesta: null },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  expect(screen.getByRole("combobox")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /a mano/i })).toBeInTheDocument();
});
