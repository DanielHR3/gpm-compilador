import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import CargaAsIs from "./CargaAsIs";

vi.mock("@/lib/api", () => ({
  proponerExpediente: vi.fn(),
  ErrorApi: class extends Error {
    status = 0;
    error = "";
    archivos?: string[];
    constructor(m: string) { super(m); this.error = m; }
  },
}));

it("el boton se habilita con el AS-IS y manda el AS-IS y los adjuntos", async () => {
  const { proponerExpediente } = await import("@/lib/api");
  vi.mocked(proponerExpediente).mockResolvedValue({ sid: "b".repeat(16), estado: "generando" });
  const onPropuesta = vi.fn();
  render(<CargaAsIs onPropuesta={onPropuesta} />);
  const btn = screen.getByRole("button", { name: /proponer to-be y diccionario/i });
  expect(btn).toBeDisabled();
  expect(screen.getByText(/redacta un borrador/i)).toBeInTheDocument();
  await userEvent.upload(screen.getByLabelText(/^análisis as-is$/i), new File(["# x"], "as.md", { type: "text/markdown" }));
  await userEvent.upload(screen.getByLabelText(/documentos de apoyo/i), new File(["png"], "d.png", { type: "image/png" }));
  expect(btn).toBeEnabled();
  await userEvent.click(btn);
  const fd = vi.mocked(proponerExpediente).mock.calls[0][0];
  expect(fd.get("as_is")).toBeInstanceOf(File);
  expect(fd.getAll("adjuntos")).toHaveLength(1);
  expect(onPropuesta).toHaveBeenCalledWith("b".repeat(16));
});

it("un error del servidor se muestra y no navega", async () => {
  const { proponerExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("archivo demasiado grande"); e.status = 413;
  vi.mocked(proponerExpediente).mockRejectedValue(e);
  const onPropuesta = vi.fn();
  render(<CargaAsIs onPropuesta={onPropuesta} />);
  await userEvent.upload(screen.getByLabelText(/^análisis as-is$/i), new File(["# x"], "as.md"));
  await userEvent.click(screen.getByRole("button", { name: /proponer/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/demasiado grande/);
  expect(onPropuesta).not.toHaveBeenCalled();
});
