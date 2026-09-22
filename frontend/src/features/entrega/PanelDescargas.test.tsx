import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  urlGpm: (_sid: string, modo: string) => `/api/v1/x/gpm?modo=${modo}`,
  urlManifiesto: () => "/api/v1/x/manifiesto",
}));

import PanelDescargas from "./PanelDescargas";
import type { EstadoExpediente, Hueco } from "@/lib/types";

const HUECO: Hueco = {
  nivel: "bloqueante",
  codigo: "FLU-01",
  ubicacion: "flujo",
  mensaje: "el flujo sale en línea recta",
  propuesta: null,
};

const estado = {
  sid: "a".repeat(16),
  manifiesto: {
    tramite: { nombre: "Trámite de Prueba" },
    pantallas: [{ id: "p1", nombre: "Solicitud", campos: [{ nombre: "curp" }] }],
    flujo: { tareas: [{ id: "t1" }], conexiones: [] },
    acciones: [],
  },
  huecos: [HUECO],
  tieneVistas: false,
} as unknown as EstadoExpediente;

function pintar(desbloqueado = true) {
  render(
    <PanelDescargas
      sid={estado.sid}
      desbloqueado={desbloqueado}
      bloqueantes={desbloqueado ? [] : [HUECO]}
      fraseBloqueo={(n) => `Faltan ${n} por resolver`}
      estado={estado}
    />,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("pinta una tarjeta por cada cosa que se puede descargar", () => {
  pintar();

  expect(screen.getByRole("heading", { name: ".gpm (producción)" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: ".gpm (pruebas)" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Observaciones" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Manifiesto" })).toBeInTheDocument();
});

it("el panel dice qué entendió el compilador, una sola vez", () => {
  pintar();

  expect(screen.getAllByText(/1 pantalla · 1 campo/)).toHaveLength(1);
});

it("producción y pruebas no se ven iguales", () => {
  // Elegir mal cuesta una importacion a produccion que hay que deshacer: el
  // de verdad lleva el boton lleno; el de pruebas, contorno y franja arena.
  pintar();

  const produccion = screen.getByRole("heading", { name: ".gpm (producción)" }).closest("[data-enfasis]");
  const pruebas = screen.getByRole("heading", { name: ".gpm (pruebas)" }).closest("[data-enfasis]");

  expect(produccion).toHaveAttribute("data-enfasis", "primaria");
  expect(pruebas).toHaveAttribute("data-enfasis", "secundaria");
});

it("con el expediente bloqueado el .gpm no se puede bajar y dice por qué", () => {
  pintar(false);

  // El motivo se dice una vez, en la cabecera; cada tarjeta cerrada solo se
  // marca. Repetir la frase larga tres veces en la misma vista no informa mas.
  expect(screen.getByText(/Faltan 1 por resolver/)).toBeInTheDocument();
  expect(screen.getAllByText("Bloqueado")).toHaveLength(2);
  const bajar = screen.getAllByRole("button", { name: /^Descargar$/ });
  // Los dos .gpm quedan cerrados; observaciones y manifiesto siguen abiertos.
  expect(bajar.filter((b) => (b as HTMLButtonElement).disabled)).toHaveLength(2);
});

it("la vista previa de las observaciones se arma aquí, sin ir al servidor", async () => {
  const pedir = vi.fn();
  vi.stubGlobal("fetch", pedir);
  pintar();

  await userEvent.click(
    screen.getByRole("button", { name: /vista previa de Observaciones/i }),
  );

  expect(await screen.findByText(/Trámite de Prueba/)).toBeInTheDocument();
  expect(pedir).not.toHaveBeenCalled();
});

it("la vista previa del .gpm pide el archivo al servidor", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, text: async () => '{"nombre":"Trámite de Prueba"}' })),
  );
  pintar();

  await userEvent.click(
    screen.getByRole("button", { name: /vista previa de \.gpm \(producción\)/i }),
  );

  await waitFor(() =>
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/x/gpm?modo=produccion"),
  );
});

it("si el archivo no se puede leer lo dice, no deja la ventana en blanco", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500 })));
  pintar();

  await userEvent.click(
    screen.getByRole("button", { name: /vista previa de Manifiesto/i }),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo/i);
});

it("«Descarga» del menú aterriza aquí", () => {
  // El ancla `#entrega` vive en este panel: es donde estan las descargas.
  pintar();

  const panel = document.querySelector("#entrega") as HTMLElement;
  expect(panel).toBeTruthy();
  expect(panel.getAttribute("tabindex")).toBe("-1");
});

it("al aterrizar destella un momento y se apaga, no se queda enmarcado", () => {
  // Un anillo de foco permanente alrededor de toda la seccion parecia un
  // error. El salto se senala con un destello que termina solo — por reloj,
  // no por `animationend`: con movimiento reducido la animacion no corre y
  // ese evento nunca llegaria.
  vi.useFakeTimers();
  try {
    pintar();
    const panel = document.querySelector("#entrega") as HTMLElement;

    fireEvent.focus(panel);
    expect(panel).toHaveAttribute("data-destello", "true");

    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(panel).not.toHaveAttribute("data-destello");
  } finally {
    vi.useRealTimers();
  }
});

it("el manifiesto se guarda, no se abre en la pestaña", () => {
  // El servidor lo sirve como `text/yaml` sin `Content-Disposition`: sin el
  // atributo `download`, un boton que dice «Descargar» abria el YAML en
  // pantalla. El `.gpm` si trae cabecera propia y se deja en paz.
  pintar();

  const enlaces = screen.getAllByRole("link", { name: /descargar/i });
  const manifiesto = enlaces.find((a) => a.getAttribute("href") === "/api/v1/x/manifiesto");
  const gpm = enlaces.find((a) => a.getAttribute("href")?.includes("modo=produccion"));

  expect(manifiesto).toHaveAttribute("download", expect.stringContaining(".yaml"));
  expect(gpm).not.toHaveAttribute("download");
});

it("entrar con #entrega en la url baja hasta aquí", () => {
  // El navegador resuelve el ancla antes de que la SPA pinte el panel, asi
  // que el salto se hace al montar o no se hace nunca.
  const bajar = vi.fn();
  window.Element.prototype.scrollIntoView = bajar;
  window.location.hash = "#entrega";

  pintar();

  expect(bajar).toHaveBeenCalled();
  window.location.hash = "";
});
