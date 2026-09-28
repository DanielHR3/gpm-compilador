// frontend/src/features/documentos/TarjetaDocumento.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import type { DocumentoTramite } from "@/lib/types";

import TarjetaDocumento from "./TarjetaDocumento";

const DOC: DocumentoTramite = {
  id: "abc123", nombre: "Identificación oficial", cita_as_is: "identificación oficial vigente",
  destino: "elimina", campo: "", cita_to_be: "La identificación oficial se elimina",
  motivo: "Se valida con la CURP.", motivo_de: "ia", confianza: "alta", veredicto: "",
  origen: "agente", estado: "propuesto",
};

function pintar(doc: Partial<DocumentoTramite> = {}, onDecidir = vi.fn().mockResolvedValue(undefined)) {
  render(<TarjetaDocumento documento={{ ...DOC, ...doc }} onDecidir={onDecidir} />);
  return onDecidir;
}

it("enseña el documento, su destino, las dos citas y el motivo rotulado como IA", () => {
  pintar();
  const tarjeta = screen.getByRole("article", { name: "Identificación oficial" });
  expect(tarjeta).toHaveTextContent("Se elimina");
  expect(tarjeta).toHaveTextContent("Propuesto, sin revisar");
  expect(tarjeta).toHaveTextContent("identificación oficial vigente");
  expect(tarjeta).toHaveTextContent("La identificación oficial se elimina");
  expect(tarjeta).toHaveTextContent("Redacción de la IA");
  expect(tarjeta).toHaveTextContent("Confianza alta");
});

it("aceptar manda el destino propuesto", async () => {
  const onDecidir = pintar();
  await userEvent.click(screen.getByRole("button", { name: /aceptar/i }));
  expect(onDecidir).toHaveBeenCalledWith("elimina", "");
});

it("cambiar destino funciona con el selector y lleva el motivo", async () => {
  const onDecidir = pintar();
  const usuario = userEvent.setup();
  await usuario.selectOptions(screen.getByLabelText(/destino/i), "consulta");
  await usuario.type(screen.getByLabelText(/motivo/i), "Se consulta en RENAPO.");
  await usuario.click(screen.getByRole("button", { name: /guardar/i }));
  expect(onDecidir).toHaveBeenCalledWith("consulta", "Se consulta en RENAPO.");
});

it("sin destino no ofrece aceptar, solo elegir", () => {
  pintar({ destino: "sin_destino", veredicto: "cita_inventada", cita_to_be: "" });
  expect(screen.queryByRole("button", { name: /^aceptar/i })).toBeNull();
  expect(screen.getByLabelText(/destino/i)).toHaveValue("");
  expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled();
  expect(screen.getByRole("article")).toHaveTextContent(/no está en el TO-BE/i);
});

it("un eliminado ya decidido sin frase del TO-BE lo dice", () => {
  pintar({ estado: "aceptado", cita_to_be: "" });
  expect(screen.getByRole("article")).toHaveTextContent(/eliminado sin fundamento/i);
});

it("lo decidido dice por quién y deja corregir", () => {
  pintar({ estado: "corregido", motivo_de: "persona", motivo: "Lo dijo la dependencia." });
  const tarjeta = screen.getByRole("article");
  expect(tarjeta).toHaveTextContent("Corregido por una persona");
  expect(tarjeta).toHaveTextContent("Motivo que escribió el analista");
  expect(screen.queryByRole("button", { name: /^aceptar/i })).toBeNull();
});

it("si guardar falla lo dice y conserva lo elegido", async () => {
  pintar({}, vi.fn().mockRejectedValue(new Error("sin red")));
  const usuario = userEvent.setup();
  await usuario.selectOptions(screen.getByLabelText(/destino/i), "sistema");
  await usuario.click(screen.getByRole("button", { name: /guardar/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo guardar/i);
  expect(screen.getByLabelText(/destino/i)).toHaveValue("sistema");
});

it("una tarjeta ya decidida va compacta y abre el formulario al pedirlo", async () => {
  // Con diez documentos decididos, diez formularios abiertos alargaban la
  // pagina y tapaban lo que importa: que paso con cada documento.
  const onDecidir = pintar({ estado: "aceptado" });
  expect(screen.queryByLabelText(/destino/i)).toBeNull();
  const usuario = userEvent.setup();
  await usuario.click(screen.getByRole("button", { name: /cambiar destino/i }));
  await usuario.selectOptions(screen.getByLabelText(/destino/i), "sistema");
  await usuario.click(screen.getByRole("button", { name: /guardar/i }));
  expect(onDecidir).toHaveBeenCalledWith("sistema", "");
});

it("un eliminado que solo nombra el TO-BE lo dice, sin una cita vacía", () => {
  pintar({ cita_as_is: "" });
  const tarjeta = screen.getByRole("article");
  expect(tarjeta).toHaveTextContent("El AS-IS no lo nombra; lo dice el TO-BE.");
  expect(tarjeta).not.toHaveTextContent("En el AS-IS");
});
