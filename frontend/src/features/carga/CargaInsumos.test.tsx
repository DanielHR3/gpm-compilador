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

// El 422 de `/expedientes` manda `archivos: ["NOMBRE: motivo", ...]` igual que
// el 413, pero el banner solo los pintaba en la rama del 413: el analista veia
// "no se pudo leer el documento" sobre cuatro zonas de carga y no sabia cual de
// los archivos era. En "Alta de aviso de testamento" eran los dos PDF (AS-IS y
// TO-BE), escaneados, y el backend ya decia exactamente eso.
it("un 422 de lectura dice QUE archivo no se pudo leer y por que", async () => {
  const { crearExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("no se pudo leer el documento");
  e.status = 422;
  e.archivos = [
    "AS- IS AVISOS DE TESTAMENTO.pdf: el PDF está escaneado (es una imagen, no texto). " +
      "Adjúntalo como documento de apoyo y sube el Diccionario en Word o Markdown",
    "TO- BE Aviso de testamento.pdf: el PDF está escaneado (es una imagen, no texto).",
  ];
  (crearExpediente as any).mockRejectedValue(e);
  render(<CargaInsumos onListo={() => {}} />);
  await userEvent.upload(
    screen.getByLabelText(/^diccionario$/i),
    new File(["# x"], "dd.md", { type: "text/markdown" }),
  );
  await userEvent.click(screen.getByRole("button", { name: /revisar|extraer/i }));

  expect(await screen.findByText(/AS- IS AVISOS DE TESTAMENTO\.pdf/)).toBeInTheDocument();
  expect(screen.getByText(/TO- BE Aviso de testamento\.pdf/)).toBeInTheDocument();
  expect(screen.getAllByText(/escaneado/i).length).toBeGreaterThan(0);
});

it("un error sin lista de archivos sigue mostrando solo el mensaje", async () => {
  const { crearExpediente, ErrorApi } = await import("@/lib/api");
  const e = new (ErrorApi as any)("sesión no encontrada");
  e.status = 404;
  (crearExpediente as any).mockRejectedValue(e);
  render(<CargaInsumos onListo={() => {}} />);
  await userEvent.upload(
    screen.getByLabelText(/^diccionario$/i),
    new File(["# x"], "dd.md", { type: "text/markdown" }),
  );
  await userEvent.click(screen.getByRole("button", { name: /revisar|extraer/i }));
  expect(await screen.findByText(/sesión no encontrada/)).toBeInTheDocument();
});
