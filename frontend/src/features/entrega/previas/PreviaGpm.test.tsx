import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import PreviaGpm from "./PreviaGpm";

const GPM = JSON.stringify({
  nombre: "Constancia de Residencia", homoclave: "HGO-001", tiempo_entrega: "3 días hábiles", costo: "0",
  Tareas: [
    { id: "1", nombre: "Solicitud", inicial: "1", asignacion: "autoservicio", terminal: "0",
      Pasos: [{ formulario_id: "10", modo: "edicion" }] },
    { id: "2", nombre: "Revisión", inicial: "0", asignacion: "grupo", terminal: "1",
      GruposUsuarios: [{ nombre: "Funcionario" }], Pasos: [{ formulario_id: "11", modo: "edicion" }] },
  ],
  Formularios: [
    { id: "10", nombre: "Solicitud", Campos: [
      { nombre: "curp", etiqueta: "CURP", tipo: "text", validacion: "required|exact_length[18]", dependiente_campo: "" },
      { nombre: "doc", etiqueta: "Comprobante", tipo: "file", validacion: "required", dependiente_campo: "" },
    ] },
    { id: "11", nombre: "Revisión", Campos: [
      { nombre: "dictamen", etiqueta: "Dictamen", tipo: "select", validacion: "",
        extra: JSON.stringify({ catalog_type: "manual", catalog_url: "", catalog_values: "aprobado:Aprobado|rechazado:Rechazado" }) },
      { nombre: "motivo", etiqueta: "Motivo", tipo: "textarea", validacion: "", dependiente_campo: "@@dictamen=='rechazado'" },
    ] },
  ],
  Acciones: [{ nombre: "Folio", tipo: "php", tarea_id: "2", momento: "despues" }],
  Conexiones: [{ tarea_id_origen: "1", tarea_id_destino: "2", tipo: "evaluacion", regla: "@@dictamen=='aprobado'" }],
});

it("resume el .gpm: trámite, formularios con campos, tareas, conexiones y acciones", () => {
  render(<PreviaGpm texto={GPM} />);

  expect(screen.getByRole("heading", { name: /Constancia de Residencia/ })).toBeInTheDocument();
  expect(screen.getByText("HGO-001")).toBeInTheDocument();

  const f1 = screen.getByRole("article", { name: /Formulario.*Solicitud/ });
  const curp = within(f1).getByText("CURP").closest("li")!;
  expect(curp).toHaveTextContent(/curp/);
  expect(curp).toHaveTextContent(/Texto/);
  expect(curp).toHaveTextContent(/obligatorio/i);
  expect(within(f1).getByText("Comprobante").closest("li")).toHaveTextContent(/Archivo/);

  const f2 = screen.getByRole("article", { name: /Formulario.*Revisión/ });
  expect(within(f2).getByText("Dictamen").closest("li")).toHaveTextContent("Aprobado, Rechazado");
  expect(within(f2).getByText("Motivo").closest("li")).toHaveTextContent(/visible si.*dictamen=='rechazado'/);

  const tareas = screen.getByRole("region", { name: /tareas/i });
  expect(within(tareas).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    expect.stringMatching(/Solicitud.*autoservicio.*inicia/i),
    expect.stringMatching(/Revisión.*Funcionario.*termina/i),
  ]);
  const conexiones = screen.getByRole("region", { name: /conexiones/i });
  expect(within(conexiones).getByRole("listitem")).toHaveTextContent(/Solicitud → Revisión.*@@dictamen=='aprobado'/);
  const acciones = screen.getByRole("region", { name: /acciones/i });
  expect(within(acciones).getByRole("listitem")).toHaveTextContent(/Folio.*después de.*Revisión/);
});

it("«Ver el JSON» enseña el archivo sangrado y avisa que va en una sola línea", async () => {
  render(<PreviaGpm texto={GPM} />);
  await userEvent.click(screen.getByRole("button", { name: /ver el json/i }));

  const pre = document.querySelector("pre")!;
  expect(pre.textContent).toContain('"homoclave": "HGO-001"');
  expect(screen.getByText(/una sola línea/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /ver el resumen/i }));
  expect(document.querySelector("pre")).toBeNull();
});

it("si el texto no es JSON lo enseña tal cual, sin reventar", () => {
  render(<PreviaGpm texto={"no es json"} />);
  expect(document.querySelector("pre")).toHaveTextContent("no es json");
});
