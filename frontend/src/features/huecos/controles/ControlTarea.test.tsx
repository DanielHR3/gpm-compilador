import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import ControlTarea from "./ControlTarea";

const hueco = {
  nivel: "por_confirmar" as const,
  codigo: "DOC-04",
  ubicacion: "documentos/Oficio",
  mensaje:
    "el documento «Oficio» se genera al terminar la tarea «Solicitud», la primera en la que ya están todos sus datos. Si debe salir en otra tarea (por ejemplo tras una firma), cámbialo a mano",
  propuesta: null,
};

const candidatas = [
  { id: "t1", nombre: "Solicitud", vale: true, actual: true },
  { id: "t2", nombre: "Revisión", vale: true, actual: false },
  { id: "t3", nombre: "Pago", vale: false, actual: false, motivo: "todavía no se capturan: folio" },
  { id: "fin", nombre: "Trámite concluido", vale: false, actual: false, motivo: "es el cierre del trámite" },
];

const combo = () => screen.getByRole("combobox", { name: /tarea en la que se genera/i });

it("trae elegida la tarea donde el documento está hoy", () => {
  render(<ControlTarea hueco={hueco} candidatas={candidatas} onConfirmar={vi.fn()} onDejar={vi.fn()} />);
  expect(combo()).toHaveValue("t1");
});

it("las tareas que no valen salen deshabilitadas con el motivo a la vista", () => {
  render(<ControlTarea hueco={hueco} candidatas={candidatas} onConfirmar={vi.fn()} onDejar={vi.fn()} />);
  const pago = screen.getByRole("option", { name: "Pago — todavía no se capturan: folio" });
  expect(pago).toBeDisabled();
  expect(screen.getByRole("option", { name: "Trámite concluido — es el cierre del trámite" })).toBeDisabled();
  expect(screen.getByRole("option", { name: "Revisión" })).toBeEnabled();
});

it("guardar manda la tarea elegida, y solo si cambió", async () => {
  const onConfirmar = vi.fn();
  render(<ControlTarea hueco={hueco} candidatas={candidatas} onConfirmar={onConfirmar} onDejar={vi.fn()} />);

  const guardar = screen.getByRole("button", { name: /guardar/i });
  expect(guardar).toBeDisabled();

  await userEvent.selectOptions(combo(), "t2");
  await userEvent.click(guardar);
  expect(onConfirmar).toHaveBeenCalledWith("t2");
});

it("dejarlo así confirma la tarea actual sin cambiar nada", async () => {
  const onDejar = vi.fn();
  render(<ControlTarea hueco={hueco} candidatas={candidatas} onConfirmar={vi.fn()} onDejar={onDejar} />);
  await userEvent.click(screen.getByRole("button", { name: /dejarlo así/i }));
  expect(onDejar).toHaveBeenCalled();
});
