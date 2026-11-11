import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import CargaAsIs from "./CargaAsIs";

vi.mock("@/lib/api", () => ({
  leerCapacidades: vi.fn().mockResolvedValue({ proponer: true, motivo: null, pruebas: false }),
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

it("en modo de pruebas lo avisa antes de subir", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  vi.mocked(leerCapacidades).mockResolvedValueOnce({ proponer: true, motivo: null, pruebas: true });
  render(<CargaAsIs onPropuesta={() => {}} />);
  expect(await screen.findByRole("note", { name: /modo de pruebas/i })).toBeInTheDocument();
});

it("fuera del modo de pruebas no hay aviso", async () => {
  const { leerCapacidades } = await import("@/lib/api");
  render(<CargaAsIs onPropuesta={() => {}} />);
  await vi.waitFor(() => expect(leerCapacidades).toHaveBeenCalled());
  expect(screen.queryByRole("note", { name: /modo de pruebas/i })).not.toBeInTheDocument();
});

it("toda la zona abre el selector, no solo el boton del campo", async () => {
  // Reportado el 2026-09-24: «el dialogo ni siquiera abre». La caja punteada
  // invitaba a hacer clic en cualquier parte y solo respondia el boton
  // nativo; en la carga de carpeta toda la zona es clicable.
  render(<CargaAsIs onPropuesta={() => {}} />);
  const input = screen.getByLabelText(/^análisis as-is$/i) as HTMLInputElement;
  // La etiqueta activa el campo despachando un evento `click` sobre el: es lo
  // que abre el selector en un navegador.
  const abrir = vi.fn();
  input.addEventListener("click", abrir);
  await userEvent.click(screen.getByText(/arrastra el as-is aquí o haz clic para elegirlo/i));
  expect(abrir).toHaveBeenCalled();
});

it("arrastrar el archivo a la zona lo elige y lo nombra", async () => {
  render(<CargaAsIs onPropuesta={() => {}} />);
  const zona = screen.getByText(/arrastra el as-is aquí/i).closest("label") as HTMLElement;
  fireEvent.drop(zona, { dataTransfer: { files: [new File(["# x"], "Mi AS-IS.md")] } });
  expect(await screen.findByText("Mi AS-IS.md")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /proponer/i })).toBeEnabled();
});

it("la zona de documentos de apoyo tambien abre el selector y acepta arrastrar", async () => {
  render(<CargaAsIs onPropuesta={() => {}} />);
  const input = screen.getByLabelText(/documentos de apoyo/i) as HTMLInputElement;
  const abrir = vi.fn();
  input.addEventListener("click", abrir);
  await userEvent.click(screen.getByText(/arrastra aquí diagramas o pdf/i));
  expect(abrir).toHaveBeenCalled();
  const zona = screen.getByText(/arrastra aquí diagramas o pdf/i).closest("label") as HTMLElement;
  fireEvent.drop(zona, { dataTransfer: { files: [new File(["a"], "a.png"), new File(["b"], "b.pdf")] } });
  expect(await screen.findByText("2 documentos de apoyo")).toBeInTheDocument();
});

// Seguimiento (2026-11-11): si se llegó desde la campanita, el expediente nace ligado al trámite.
it("con un trámite elegido en la campanita lo dice y manda su ID de RUTS", async () => {
  const { proponerExpediente } = await import("@/lib/api");
  sessionStorage.setItem("gpmc.tramite-ligado", JSON.stringify({ ruts_id: "4321", nombre: "Licencia" }));
  vi.mocked(proponerExpediente).mockResolvedValue({ sid: "a".repeat(16), estado: "generando" });
  render(<CargaAsIs onPropuesta={() => {}} />);
  expect(screen.getByText(/Licencia/)).toBeInTheDocument();
  expect(screen.getByText(/RUTS 4321/)).toBeInTheDocument();
  await userEvent.upload(screen.getByLabelText("Análisis AS-IS"), new File(["# x"], "as-is.md", { type: "text/markdown" }));
  await userEvent.click(screen.getByRole("button", { name: /generar|proponer|redactar/i }));
  const fd = vi.mocked(proponerExpediente).mock.calls.at(-1)![0] as FormData;
  expect(fd.get("ruts_id")).toBe("4321");
  expect(sessionStorage.getItem("gpmc.tramite-ligado")).toBeNull();
});

it("«Quitar» desliga el trámite y ya no se manda el ID", async () => {
  const { proponerExpediente } = await import("@/lib/api");
  sessionStorage.setItem("gpmc.tramite-ligado", JSON.stringify({ ruts_id: "4321", nombre: "Licencia" }));
  vi.mocked(proponerExpediente).mockResolvedValue({ sid: "a".repeat(16), estado: "generando" });
  render(<CargaAsIs onPropuesta={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /quitar/i }));
  expect(screen.queryByText(/RUTS 4321/)).not.toBeInTheDocument();
  await userEvent.upload(screen.getByLabelText("Análisis AS-IS"), new File(["# x"], "as-is.md", { type: "text/markdown" }));
  await userEvent.click(screen.getByRole("button", { name: /generar|proponer|redactar/i }));
  expect((vi.mocked(proponerExpediente).mock.calls.at(-1)![0] as FormData).get("ruts_id")).toBeNull();
});
