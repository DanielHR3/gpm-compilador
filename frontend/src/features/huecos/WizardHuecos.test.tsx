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
