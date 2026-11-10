import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import Campanita from "./Campanita";
import * as api from "@/lib/api";

const solicitud = (ruts_id: string, nueva: boolean) => ({
  ruts_id, nombre: `Trámite ${ruts_id}`, dependencia: "Secretaría X", enviado_por: "luis",
  ruts: { costo: "", tiempo_entrega: "", description: "" }, recibida: "2026-11-10T11:00:00", nueva,
});

beforeEach(() => vi.restoreAllMocks());

it("enseña cuántas nuevas hay y la lista con su AS-IS", async () => {
  vi.spyOn(api, "leerSolicitudes").mockResolvedValue({ solicitudes: [solicitud("4321", true), solicitud("1", false)], nuevas: 1 });
  render(<Campanita />);
  const boton = await screen.findByRole("button", { name: /solicitudes de simplifica: 1 nueva/i });
  await userEvent.click(boton);
  expect(await screen.findByText("Trámite 4321")).toBeInTheDocument();
  expect(screen.getByText(/RUTS 4321 · Secretaría X · enviado por luis/)).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: /descargar as-is/i })[0]).toHaveAttribute("href", "/api/v1/solicitudes/4321/as-is");
});

it("marcar como vista la quita de las nuevas", async () => {
  vi.spyOn(api, "leerSolicitudes")
    .mockResolvedValueOnce({ solicitudes: [solicitud("4321", true)], nuevas: 1 })
    .mockResolvedValue({ solicitudes: [solicitud("4321", false)], nuevas: 0 });
  const marcar = vi.spyOn(api, "marcarSolicitudVista").mockResolvedValue(undefined);
  render(<Campanita />);
  await userEvent.click(await screen.findByRole("button", { name: /1 nueva/i }));
  await userEvent.click(await screen.findByRole("button", { name: /marcar como vista/i }));
  expect(marcar).toHaveBeenCalledWith("4321");
  await waitFor(() => expect(screen.getByRole("button", { name: /solicitudes de simplifica: sin nuevas/i })).toBeInTheDocument());
});

it("si el servidor no tiene la ruta o falla, la campanita no estorba", async () => {
  vi.spyOn(api, "leerSolicitudes").mockRejectedValue(new Error("404"));
  const { container } = render(<Campanita />);
  await waitFor(() => expect(container).toBeEmptyDOMElement());
});
