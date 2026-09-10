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

it("ofrece el enlace a la plantilla de ejemplo", () => {
  render(<CargaInsumos onListo={() => {}} />);
  expect(
    screen.getByRole("link", { name: /plantilla de ejemplo/i }),
  ).toHaveAttribute("href", "/descargar-plantilla");
});

it("un drop real asigna el archivo y muestra su nombre en la zona", () => {
  render(<CargaInsumos onListo={() => {}} />);
  const zona = screen.getByLabelText(/^to be$/i).closest("div") as HTMLElement;
  const archivo = new File(["x"], "arrastrado.md", { type: "text/markdown" });
  fireEvent.drop(zona, { dataTransfer: { files: [archivo] } });
  expect(screen.getByTestId("nombre-to_be")).toHaveTextContent("arrastrado.md");
});
