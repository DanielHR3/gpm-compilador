import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  leerGrupos: vi.fn(),
}));

import { leerGrupos } from "@/lib/api";

import ControlGrupo from "./ControlGrupo";

const hueco = {
  nivel: "por_confirmar" as const,
  codigo: "ACT-01",
  ubicacion: "area",
  mensaje:
    "las tareas de «Area» se restringen al grupo «Area», que es el nombre del responsable y no un grupo de la plataforma",
  propuesta: null,
};

const caja = () => screen.getByLabelText(/grupo de usuarios en la plataforma/i);

beforeEach(() => {
  vi.mocked(leerGrupos).mockResolvedValue(["licitaciones_admin", "verificacion_vehicular"]);
});

it("sugiere los grupos ya vistos en la plataforma", async () => {
  const { container } = render(<ControlGrupo hueco={hueco} onConfirmar={vi.fn()} onDejar={vi.fn()} />);
  await waitFor(() =>
    expect(container.querySelectorAll("datalist option")).toHaveLength(2),
  );
  expect(caja()).toHaveAttribute("list", container.querySelector("datalist")?.id);
});

it("guarda lo escrito, sin los espacios de los lados", async () => {
  const onConfirmar = vi.fn();
  render(<ControlGrupo hueco={hueco} onConfirmar={onConfirmar} onDejar={vi.fn()} />);
  await userEvent.type(caja(), " verificacion_vehicular ");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(onConfirmar).toHaveBeenCalledWith("verificacion_vehicular");
});

it("avisa si lo escrito no parece un identificador, pero deja guardarlo", async () => {
  const onConfirmar = vi.fn();
  render(<ControlGrupo hueco={hueco} onConfirmar={onConfirmar} onDejar={vi.fn()} />);
  await userEvent.type(caja(), "Verificación Vehicular");
  expect(screen.getByText(/no parece un identificador/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(onConfirmar).toHaveBeenCalledWith("Verificación Vehicular");
});

it("un identificador limpio no lleva aviso", async () => {
  render(<ControlGrupo hueco={hueco} onConfirmar={vi.fn()} onDejar={vi.fn()} />);
  await userEvent.type(caja(), "verificacion_vehicular");
  expect(screen.queryByText(/no parece un identificador/i)).not.toBeInTheDocument();
});

it("si la lista de sugerencias falla, la caja sigue sirviendo", async () => {
  vi.mocked(leerGrupos).mockRejectedValue(new Error("sin red"));
  const onConfirmar = vi.fn();
  render(<ControlGrupo hueco={hueco} onConfirmar={onConfirmar} onDejar={vi.fn()} />);
  await userEvent.type(caja(), "mi_grupo");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(onConfirmar).toHaveBeenCalledWith("mi_grupo");
});

it("se puede dejar el grupo como está", async () => {
  const onDejar = vi.fn();
  render(<ControlGrupo hueco={hueco} onConfirmar={vi.fn()} onDejar={onDejar} />);
  await userEvent.click(screen.getByRole("button", { name: /dejarlo así/i }));
  expect(onDejar).toHaveBeenCalled();
});
