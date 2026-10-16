import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import MenuEntrega from "./MenuEntrega";
import type { Hueco } from "@/lib/types";

const HUECO: Hueco = {
  nivel: "falta_dato",
  codigo: "DIC-07",
  ubicacion: "p1::modalidad",
  mensaje: "el campo 'Modalidad' es select pero no se extrajo ninguna opción",
  propuesta: null,
};

const SID = "a".repeat(16);

function pintar(puerta: { desbloqueado: boolean; bloqueantes: Hueco[] } | null) {
  render(<MenuEntrega sid={SID} puerta={puerta} />);
  return userEvent.setup();
}

it("el botón resume el semáforo sin abrir el menú", () => {
  pintar({ desbloqueado: false, bloqueantes: [HUECO] });

  expect(screen.getByRole("button", { name: /entrega.*1 por revisar/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /abrir simulador/i })).not.toBeInTheDocument();
});

it("con todo resuelto el botón dice que está listo", () => {
  pintar({ desbloqueado: true, bloqueantes: [] });

  expect(screen.getByRole("button", { name: /entrega.*listo/i })).toBeInTheDocument();
});

it("al abrirlo lista los códigos que bloquean y apunta a las descargas", async () => {
  // Las observaciones se bajan desde `#entrega` y hacen mas falta justo
  // cuando algo bloquea: son lo que hay que mandarle a quien documento.
  const user = pintar({ desbloqueado: false, bloqueantes: [HUECO] });

  await user.click(screen.getByRole("button", { name: /entrega/i }));

  expect(await screen.findByRole("link", { name: /ver las descargas/i })).toHaveAttribute(
    "href",
    "#entrega",
  );
  expect(screen.getByText("1")).toBeInTheDocument();
  // Con la puerta cerrada hay salida: el simulador sigue enlazado y el .gpm no.
  expect(screen.getByRole("link", { name: /abrir simulador/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /\.gpm/i })).toBeNull();
});

it("conserva las puertas que no son archivos", async () => {
  // La aprobacion no tiene otra entrada en toda la SPA.
  const user = pintar({ desbloqueado: true, bloqueantes: [] });

  await user.click(screen.getByRole("button", { name: /entrega/i }));

  expect(await screen.findByRole("link", { name: /abrir simulador/i })).toHaveAttribute(
    "href",
    `/simulador/${SID}`,
  );
  expect(screen.getByRole("link", { name: /abrir aprobación/i })).toHaveAttribute(
    "href",
    `/aprobacion/${SID}`,
  );
  expect(screen.getByRole("link", { name: /antes y después/i })).toHaveAttribute(
    "href",
    `/revisar/${SID}/comparativa`,
  );
  expect(screen.getByRole("link", { name: /documentos del trámite/i })).toHaveAttribute(
    "href",
    `/revisar/${SID}/documentos`,
  );
  expect(screen.queryByText("DIC-07")).not.toBeInTheDocument();
});

it("sin puerta conocida ofrece los enlaces y calla el semáforo", async () => {
  // En «Antes y despues» y «Documentos» la SPA no carga el expediente: el
  // menu sirve de atajo, pero no inventa un estado que no leyo.
  const user = pintar(null);

  const boton = screen.getByRole("button", { name: /entrega/i });
  expect(boton).not.toHaveAccessibleName(/listo|por revisar/i);

  await user.click(boton);

  expect(await screen.findByRole("link", { name: /abrir simulador/i })).toBeInTheDocument();
  expect(screen.queryByText(/listo para entregar|por revisar/i)).not.toBeInTheDocument();
});

it("al superusuario le ofrece «Ver quién hizo qué», filtrado por el trámite", async () => {
  render(<MenuEntrega sid={SID} puerta={null} admin />);
  await userEvent.setup().click(screen.getByRole("button", { name: /entrega/i }));
  expect(await screen.findByRole("link", { name: /quién hizo qué/i })).toHaveAttribute("href", `/auditoria?sid=${SID}`);
});

it("a un analista no le enseña la auditoría", async () => {
  render(<MenuEntrega sid={SID} puerta={null} />);
  await userEvent.setup().click(screen.getByRole("button", { name: /entrega/i }));
  await screen.findByRole("link", { name: /abrir simulador/i });
  expect(screen.queryByRole("link", { name: /quién hizo qué/i })).toBeNull();
});
