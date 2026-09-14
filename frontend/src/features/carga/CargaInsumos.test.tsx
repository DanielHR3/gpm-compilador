import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import CargaInsumos from "./CargaInsumos";

vi.mock("@/lib/api", () => ({
  crearExpediente: vi.fn(),
  ErrorApi: class extends Error { status = 0; archivos?: string[]; },
}));

it("el boton Extraer se habilita al elegir un Diccionario", async () => {
  render(<CargaInsumos onListo={() => {}} />);
  const btn = screen.getByRole("button", { name: /extraer/i });
  expect(btn).toBeDisabled();
  const input = screen.getByLabelText(/diccionario/i);
  await userEvent.upload(input, new File(["# x"], "dd.md", { type: "text/markdown" }));
  expect(btn).toBeEnabled();
});

it("muestra el error de tamano cuando la API lanza 413", async () => {
  const { crearExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("grande"); e.status = 413; e.archivos = ["enorme.md"];
  (crearExpediente as any).mockRejectedValue(e);
  render(<CargaInsumos onListo={() => {}} />);
  const input = screen.getByLabelText(/diccionario/i);
  await userEvent.upload(input, new File(["# x"], "dd.md", { type: "text/markdown" }));
  await userEvent.click(screen.getByRole("button", { name: /extraer/i }));
  expect(await screen.findByText(/enorme\.md/)).toBeInTheDocument();
  expect(screen.getByText(/10 MB/i)).toBeInTheDocument();
});

it("ofrece plantilla de ejemplo para Diccionario y para To Be", () => {
  render(<CargaInsumos onListo={() => {}} />);
  expect(
    screen.getByRole("link", { name: /plantilla.*diccionario/i }),
  ).toHaveAttribute("href", "/descargar-plantilla");
  expect(
    screen.getByRole("link", { name: /plantilla.*to be/i }),
  ).toHaveAttribute("href", "/descargar-plantilla-tobe");
});

it("un drop real asigna el archivo y muestra su nombre en la zona", () => {
  render(<CargaInsumos onListo={() => {}} />);
  const zona = screen.getByLabelText(/^to be$/i).closest("div") as HTMLElement;
  const archivo = new File(["x"], "arrastrado.md", { type: "text/markdown" });
  fireEvent.drop(zona, { dataTransfer: { files: [archivo] } });
  expect(screen.getByTestId("nombre-to_be")).toHaveTextContent("arrastrado.md");
});

it("se pueden adjuntar los diagramas y PDF que el compilador no lee", async () => {
  const { crearExpediente } = await import("@/lib/api");
  vi.mocked(crearExpediente).mockResolvedValue({ sid: "a".repeat(16) } as any);

  render(<CargaInsumos onListo={vi.fn()} />);

  const dicc = new File(["# d"], "Diccionario.md", { type: "text/markdown" });
  const png = new File(["x"], "TO BE.png", { type: "image/png" });
  await userEvent.upload(screen.getByLabelText(/^diccionario$/i), dicc);
  await userEvent.upload(screen.getByLabelText(/documentos de apoyo/i), png);
  await userEvent.click(screen.getByRole("button", { name: /revisar|extraer/i }));

  const fd = vi.mocked(crearExpediente).mock.calls.at(-1)![0] as FormData;
  expect(fd.getAll("adjuntos").map((f) => (f as File).name)).toEqual(["TO BE.png"]);
});

it("se pueden subir las plantillas de los documentos que genera el tramite", async () => {
  const { crearExpediente } = await import("@/lib/api");
  vi.mocked(crearExpediente).mockResolvedValue({ sid: "a".repeat(16) } as any);

  render(<CargaInsumos onListo={vi.fn()} />);

  const dicc = new File(["# d"], "Diccionario.md", { type: "text/markdown" });
  const oficio = new File(["Hola {{nombre}}"], "oficio.md", { type: "text/markdown" });
  await userEvent.upload(screen.getByLabelText(/^diccionario$/i), dicc);
  await userEvent.upload(screen.getByLabelText(/documentos que genera/i), oficio);
  await userEvent.click(screen.getByRole("button", { name: /revisar|extraer/i }));

  const fd = vi.mocked(crearExpediente).mock.calls.at(-1)![0] as FormData;
  expect(fd.getAll("documentos").map((f) => (f as File).name)).toEqual(["oficio.md"]);
});

it("la zona de plantillas acepta Word y PDF, no solo .md", () => {
  render(<CargaInsumos onListo={vi.fn()} />);
  const accept = screen.getByLabelText(/documentos que genera/i).getAttribute("accept") ?? "";
  expect(accept).toContain(".docx");
  expect(accept).toContain(".pdf");
});
