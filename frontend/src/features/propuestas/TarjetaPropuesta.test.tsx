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

const vista = [{ id: "p1", nombre: "Solicitud", actor: "Ciudadano",
  campos: [{ etiqueta: "CURP", tipo: "text", obligatorio: true, opciones: [], condicion: null }] }];
const doc = {
  texto: "# Diccionario de Datos — X\n", version_prompt: "dicc-v1", ronda: 1, decision: "pendiente" as const,
  huecos: [{ nivel: "falta_dato", codigo: "GEN-01", ubicacion: "requisitos", propuesta: null,
    mensaje: "El AS-IS pide «CURP» y el Diccionario propuesto no lo captura como un campo de tipo Archivo." }],
  vista,
};
const tobe = { ...doc, vista: undefined, texto: "```mermaid\nflowchart TD\n A --> B\n```" };

it("el Diccionario abre como pantallas; «Editar texto» muestra el Markdown y conserva lo editado", async () => {
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={doc}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByRole("article", { name: /pantalla 1 · ciudadano · solicitud/i })).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.getByText(/1 dato que falta/i)).toBeInTheDocument();
  expect(screen.getByText(/El AS-IS dice que el ciudadano entrega «CURP»/)).toBeInTheDocument();
  expect(screen.getByText(/lo propuso un modelo/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /aceptar con mis cambios/i })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  await userEvent.type(screen.getByRole("textbox"), "más");
  await userEvent.click(screen.getByRole("button", { name: /ver como pantallas/i }));
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /aceptar con mis cambios/i })).toBeEnabled();
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  expect(screen.getByRole("textbox")).toHaveValue(doc.texto + "más");
});

it("si el compilador no leyo pantallas, abre el texto con el aviso", () => {
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={{ ...doc, vista: [] }}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByText(/no pudo leer pantallas/i)).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toHaveValue(doc.texto);
});

it("editar habilita «Aceptar con mis cambios» y manda corregida con el texto", async () => {
  const onDecidir = vi.fn();
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={doc}
    onDecidir={onDecidir} onSubir={() => {}} ocupado={false} />);
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  await userEvent.type(screen.getByRole("textbox"), "más");
  await userEvent.click(screen.getByRole("button", { name: /aceptar con mis cambios/i }));
  expect(onDecidir).toHaveBeenCalledWith("corregida", doc.texto + "más");
});

it("aceptar tal cual manda aceptada sin texto; declinar vuelve la tarjeta zona de carga", async () => {
  const onDecidir = vi.fn();
  const { rerender } = render(<TarjetaPropuesta titulo="Propuesta TO-BE" clave="tobe" documento={tobe}
    onDecidir={onDecidir} onSubir={() => {}} ocupado={false} />);
  await userEvent.click(screen.getByRole("button", { name: /aceptar tal cual/i }));
  expect(onDecidir).toHaveBeenCalledWith("aceptada", undefined);
  rerender(<TarjetaPropuesta titulo="Propuesta TO-BE" clave="tobe" documento={{ ...tobe, decision: "declinada" }}
    onDecidir={onDecidir} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByLabelText(/subir mi to-be/i)).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});

it("sin documento (error o sin licencia) es zona de carga y sube el archivo", async () => {
  const onSubir = vi.fn();
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={null}
    onDecidir={() => {}} onSubir={onSubir} ocupado={false} />);
  await userEvent.upload(screen.getByLabelText(/subir mi diccionario/i), new File(["# x"], "dd.md", { type: "text/markdown" }));
  expect(onSubir).toHaveBeenCalledWith(expect.any(File));
});

it("un documento aceptado se muestra cerrado, sin botones", () => {
  render(<TarjetaPropuesta titulo="Propuesta TO-BE" clave="tobe" documento={{ ...tobe, decision: "aceptada" }}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.getByText(/aceptado/i)).toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("el TO-BE abre con el diagrama grande; «Editar texto» pone texto y diagrama lado a lado", async () => {
  render(<TarjetaPropuesta titulo="Propuesta TO-BE" clave="tobe" documento={tobe}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(await screen.findByTestId("svg-mermaid", {}, { timeout: 2000 })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Acercar" })).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /editar texto/i }));
  expect(screen.getByRole("textbox")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId("svg-mermaid")).toBeInTheDocument());
  await userEvent.click(screen.getByRole("button", { name: /ver el diagrama grande/i }));
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});

it("el Diccionario no dibuja diagrama", () => {
  render(<TarjetaPropuesta titulo="Diccionario de Datos" clave="diccionario" documento={{ ...doc, texto: tobe.texto }}
    onDecidir={() => {}} onSubir={() => {}} ocupado={false} />);
  expect(screen.queryByText(/diagrama compilable/i)).not.toBeInTheDocument();
});
