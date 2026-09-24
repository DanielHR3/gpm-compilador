import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import TarjetaPropuesta from "./TarjetaPropuesta";

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async (_id: string, codigo: string) => ({
      svg: `<svg data-testid="svg-mermaid"><text>${codigo.length}</text></svg>`,
    })),
  },
}));

const doc = {
  texto: "# Diccionario de Datos — X\n", version_prompt: "dicc-v1", ronda: 1, decision: "pendiente" as const,
  huecos: [{ nivel: "falta_dato", codigo: "GEN-01", ubicacion: "requisitos", propuesta: null,
    mensaje: "El AS-IS pide «CURP» y el Diccionario propuesto no lo captura como un campo de tipo Archivo." }],
};

it("muestra el texto editable, los huecos en palabras y la nota de que lo propuso un modelo", () => {
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={doc}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByRole("article", { name: /diccionario de datos/i })).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toHaveValue(doc.texto);
  expect(screen.getByText(/1 dato que falta/i)).toBeInTheDocument();
  expect(screen.getByText(/El AS-IS dice que el ciudadano entrega «CURP»/)).toBeInTheDocument();
  expect(screen.getByText(/lo propuso un modelo/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /aceptar con mis cambios/i })).toBeDisabled();
});

it("editar habilita «Aceptar con mis cambios» y manda corregida con el texto", async () => {
  const onDecidir = vi.fn();
  render(<TarjetaPropuesta titulo="TO-BE" clave="tobe" documento={doc}
    onDecidir={onDecidir} onSubir={() => {}} ocupado={false} />);
  await userEvent.type(screen.getByRole("textbox"), "más");
  const btn = screen.getByRole("button", { name: /aceptar con mis cambios/i });
  expect(btn).toBeEnabled();
  await userEvent.click(btn);
  expect(onDecidir).toHaveBeenCalledWith("corregida", doc.texto + "más");
});

it("aceptar tal cual manda aceptada sin texto; declinar vuelve la tarjeta zona de carga", async () => {
  const onDecidir = vi.fn();
  const { rerender } = render(<TarjetaPropuesta titulo="TO-BE" clave="tobe" documento={doc}
    onDecidir={onDecidir} onSubir={() => {}} ocupado={false} />);
  await userEvent.click(screen.getByRole("button", { name: /aceptar tal cual/i }));
  expect(onDecidir).toHaveBeenCalledWith("aceptada", undefined);
  rerender(<TarjetaPropuesta titulo="TO-BE" clave="tobe" documento={{ ...doc, decision: "declinada" }}
    onDecidir={onDecidir} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByLabelText(/subir mi to-be/i)).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});

it("sin documento (error o sin licencia) es zona de carga y sube el archivo", async () => {
  const onSubir = vi.fn();
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={null}
    onDecidir={() => {}} onSubir={onSubir} ocupado={false} />);
  const input = screen.getByLabelText(/subir mi diccionario/i);
  await userEvent.upload(input, new File(["# x"], "dd.md", { type: "text/markdown" }));
  expect(onSubir).toHaveBeenCalledWith(expect.any(File));
});

it("un documento aceptado se muestra cerrado, sin botones", () => {
  render(<TarjetaPropuesta titulo="TO-BE" clave="tobe" documento={{ ...doc, decision: "aceptada" }}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByText(/aceptado/i)).toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("la tarjeta del TO-BE dibuja el diagrama debajo del texto; la del Diccionario no", async () => {
  const tobe = { ...doc, texto: "```mermaid\nflowchart TD\n A --> B\n```" };
  const { rerender } = render(<TarjetaPropuesta titulo="TO-BE" clave="tobe" documento={tobe}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(await screen.findByTestId("svg-mermaid", {}, { timeout: 2000 })).toBeInTheDocument();
  rerender(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={tobe}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  await waitFor(() => expect(screen.queryByTestId("svg-mermaid")).not.toBeInTheDocument());
});
