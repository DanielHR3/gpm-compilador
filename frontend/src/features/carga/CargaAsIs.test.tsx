import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import CargaAsIs from "./CargaAsIs";

vi.mock("@/lib/api", () => ({
  proponerExpediente: vi.fn(),
  // Acepta las dos formas: `new ErrorApi("msg")` (las pruebas) y
  // `new ErrorApi(status, "msg")` (la firma real, que usa comoErrorDeCarga).
  ErrorApi: class extends Error {
    status = 0;
    error = "";
    archivos?: string[];
    constructor(a: number | string, b?: string) {
      super(typeof a === "string" ? a : b);
      this.status = typeof a === "number" ? a : 0;
      this.error = this.message;
    }
  },
}));

async function subirAsIs() {
  await userEvent.upload(screen.getByLabelText(/^análisis as-is$/i), new File(["# x"], "as.md"));
  await userEvent.click(screen.getByRole("button", { name: /proponer/i }));
}

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

it("un archivo demasiado grande se nombra, con el limite, como en la carga de carpeta", async () => {
  const { proponerExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("archivo demasiado grande"); e.status = 413; e.archivos = ["enorme.md"];
  vi.mocked(proponerExpediente).mockRejectedValue(e);
  render(<CargaAsIs onPropuesta={() => {}} />);
  await subirAsIs();
  const alerta = await screen.findByRole("alert");
  expect(alerta).toHaveTextContent(/demasiado grande/i);
  expect(alerta).toHaveTextContent(/10 MB/);
  expect(alerta).toHaveTextContent("enorme.md");
});

it("un archivo ilegible dice cual y por que", async () => {
  const { proponerExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("no se pudo leer el documento"); e.status = 422;
  e.archivos = ["escaneado.pdf: el PDF no tiene texto"];
  vi.mocked(proponerExpediente).mockRejectedValue(e);
  render(<CargaAsIs onPropuesta={() => {}} />);
  await subirAsIs();
  const alerta = await screen.findByRole("alert");
  expect(alerta).toHaveTextContent("escaneado.pdf");
  expect(alerta).toHaveTextContent(/no tiene texto/);
});

it("si se cae la red lo dice en pantalla en vez de no decir nada", async () => {
  const { proponerExpediente } = await import("@/lib/api");
  vi.mocked(proponerExpediente).mockRejectedValue(new TypeError("Failed to fetch"));
  render(<CargaAsIs onPropuesta={() => {}} />);
  await subirAsIs();
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo conectar con el servidor/i);
  expect(screen.getByRole("button", { name: /proponer/i })).toBeEnabled();
});
