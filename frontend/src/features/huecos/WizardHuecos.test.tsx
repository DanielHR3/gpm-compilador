import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { Toaster } from "@/components/ui/sonner";
import WizardHuecos from "./WizardHuecos";

vi.mock("@/lib/api", () => ({
  resolver: vi.fn(), reconocer: vi.fn(),
  urlGpm: () => "/api/v1/x/gpm", urlManifiesto: () => "/api/v1/x/manifiesto",
}));

const estado = {
  sid: "a".repeat(16),
  manifiesto: { actores: [{ id: "ciudadano", nombre: "Ciudadano" }], pantallas: [], flujo: { tareas: [] } },
  huecos: [
    { nivel: "falta_dato", codigo: "META-01", ubicacion: "metadatos", mensaje: "falta el tiempo", propuesta: null },
    { nivel: "por_confirmar", codigo: "META-05", ubicacion: "metadatos", mensaje: "sin homoclave", propuesta: null },
  ],
  estimacion: {}, problemas: [], tieneVistas: false,
};

it("una tarjeta por hueco y barra de progreso", () => {
  render(<WizardHuecos estado={estado as any} onEstado={() => {}} />);
  // El mensaje aparece en la tarjeta y (al bloquear) en el motivo de bloqueo.
  expect(screen.getAllByText(/falta el tiempo/).length).toBeGreaterThan(0);
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});

it("un bloqueante de codigo desconocido no deja sin salida: lista el motivo y conserva el simulador, sin enlace al .gpm", () => {
  const est = {
    ...estado,
    huecos: [
      {
        nivel: "bloqueante",
        codigo: "INS-01",
        ubicacion: "",
        mensaje: "no se encontro la Propuesta TO-BE",
        propuesta: null,
      },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  // El motivo del bloqueo se explica en pantalla.
  expect(
    screen.getByText(/Falta 1 inconsistencia por revisar antes de descargar el \.gpm/),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText(/no se encontro la Propuesta TO-BE/).length,
  ).toBeGreaterThan(0);
  // Hay salida: el simulador sigue enlazado.
  expect(
    screen.getByRole("link", { name: /simulador/i }),
  ).toHaveAttribute("href", "/simulador/" + "a".repeat(16));
  // El .gpm SI esta cerrado.
  expect(screen.queryByRole("link", { name: /\.gpm/i })).toBeNull();
});

it("pinta los avisos del analisis de flujo (problemas[])", () => {
  const est = { ...estado, problemas: ["ciclo sin salida en la tarea 3"] };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  expect(
    screen.getByText(/ciclo sin salida en la tarea 3/),
  ).toBeInTheDocument();
});

it("META-01 se resuelve por la API y sube el estado, sin recargar", async () => {
  const { resolver } = await import("@/lib/api");
  (resolver as any).mockResolvedValue({ ...estado, huecos: [estado.huecos[1]] });
  const onEstado = vi.fn();
  render(<WizardHuecos estado={estado as any} onEstado={onEstado} />);
  await userEvent.type(screen.getByLabelText(/tiempo/i), "5 dias habiles");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolver).toHaveBeenCalledWith("a".repeat(16),
    [{ tipo: "meta01", ubicacion: "metadatos", valor: "5 dias habiles" }]);
  expect(onEstado).toHaveBeenCalled();
});

it("META-04 (nombre del tramite) se resuelve con un ControlTexto real, no solo el boton de reconocer", async () => {
  const { resolver } = await import("@/lib/api");
  const est = {
    ...estado,
    huecos: [
      { nivel: "falta_dato", codigo: "META-04", ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite", propuesta: null },
    ],
  };
  (resolver as any).mockResolvedValue({ ...est, huecos: [] });
  const onEstado = vi.fn();
  render(<WizardHuecos estado={est as any} onEstado={onEstado} />);
  await userEvent.type(screen.getByLabelText(/nombre/i), "Constancia de residencia");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
  expect(resolver).toHaveBeenCalledWith("a".repeat(16),
    [{ tipo: "meta04", ubicacion: "metadatos", valor: "Constancia de residencia" }]);
  expect(onEstado).toHaveBeenCalled();
});

it("MMD-03 muestra un ControlActor con los actores del manifiesto", async () => {
  const est = {
    ...estado,
    huecos: [
      { nivel: "falta_dato", codigo: "MMD-03", ubicacion: "flujo.tareas[0]", mensaje: "quien resuelve", propuesta: null },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  const combo = screen.getByRole("combobox");
  expect(combo).toBeInTheDocument();
  await userEvent.click(combo);
  expect(await screen.findByRole("option", { name: "Ciudadano" })).toBeInTheDocument();
});

it("avisa que el hueco quedo resuelto y cuantos faltan", async () => {
  const { resolver } = await import("@/lib/api");
  // Al resolver META-01 la API devuelve la lista sin ese hueco: queda META-05.
  vi.mocked(resolver).mockResolvedValue({
    manifiesto: estado.manifiesto,
    huecos: [estado.huecos[1]],
  } as any);

  render(
    <>
      <Toaster />
      <WizardHuecos estado={estado as any} onEstado={() => {}} />
    </>,
  );

  await userEvent.type(
    screen.getByLabelText(/tiempo de resolucion/i),
    "5 dias",
  );
  await userEvent.click(screen.getAllByRole("button", { name: /guardar/i })[0]);

  expect(await screen.findByText(/META-01 resuelto/)).toBeInTheDocument();
  expect(await screen.findByText(/queda 1 inconsistencia/i)).toBeInTheDocument();
});

it("cada tarjeta va envuelta en el contenedor que permite animar su salida", () => {
  // El PLAZO de salida se prueba, sin relojes reales, en useListaConSalida.test.ts.
  // Aqui solo interesa que el wizard use ese hook: atarlo al temporizador desde
  // esta prueba la vuelve una carrera (240 ms contra la maquina).
  const { container } = render(
    <WizardHuecos estado={estado as any} onEstado={() => {}} />,
  );

  const envoltorios = container.querySelectorAll("[data-saliendo]");
  expect(envoltorios).toHaveLength(estado.huecos.length);
  envoltorios.forEach((e) => {
    expect(e).toHaveAttribute("data-saliendo", "false");
    expect(e).toHaveClass("tarjeta-entrando");
  });
});

it("agrupa los huecos por severidad y rotula cada grupo con su cuenta", () => {
  const est = {
    ...estado,
    huecos: [
      estado.huecos[0], // META-01, falta_dato
      estado.huecos[1], // META-05, por_confirmar
      {
        nivel: "bloqueante",
        codigo: "INS-01",
        ubicacion: "",
        mensaje: "no se encontro la Propuesta TO-BE",
        propuesta: null,
      },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);

  // Solo los grupos de severidad: son los que rotulan su cuenta entre
  // paréntesis. El bloque de instrucciones también es un `group` (todo
  // <details> lo es) y no interesa aquí.
  const grupos = screen.getAllByRole("group", { name: /\(\d+\)$/ });
  expect(grupos.map((g) => g.getAttribute("aria-label"))).toEqual([
    "Bloquean la descarga (1)",
    "Falta un dato (1)",
    "Solo confirmar (1)",
  ]);
});

it("el riel de entrega se mantiene accesible aunque la puerta siga cerrada", () => {
  const est = {
    ...estado,
    huecos: [
      {
        nivel: "bloqueante",
        codigo: "INS-01",
        ubicacion: "",
        mensaje: "falta el TO-BE",
        propuesta: null,
      },
    ],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);

  const riel = screen.getByRole("complementary", { name: /entrega/i });
  expect(within(riel).getByRole("link", { name: /simulador/i })).toBeInTheDocument();
  expect(within(riel).queryByRole("link", { name: /\.gpm/i })).toBeNull();
});

it("cada aviso de flujo es su propia tarjeta, no una viñeta de una lista", () => {
  const est = {
    ...estado,
    problemas: ["ciclo sin salida en la tarea 3", "dos tareas comparten id"],
  };
  const { container } = render(
    <WizardHuecos estado={est as any} onEstado={() => {}} />,
  );

  const avisos = screen.getAllByRole("article");
  expect(avisos).toHaveLength(2);
  expect(avisos[0]).toHaveTextContent("ciclo sin salida en la tarea 3");
  expect(container.querySelector("ul.list-disc")).toBeNull();
});

it("al volver a la pantalla, lo ya reconocido cuenta como resuelto", () => {
  // El servidor conserva lo reconocido; antes la SPA lo perdia al recargar y
  // el analista veia su trabajo como pendiente.
  const est = {
    ...estado,
    reconocidos: [["META-01", "metadatos"]] as [string, string][],
  };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);

  expect(screen.getByText(/de 2 resueltos/)).toHaveTextContent(
    "1 de 2 resueltos",
  );
  // Y la puerta del .gpm deja de estar cerrada por ese hueco.
  expect(
    screen.getByRole("complementary", { name: /entrega/i }),
  ).toHaveTextContent(/todo listo para entregar/i);
});

/** Un expediente con `n` huecos de captura, para probar los dos modos. */
/** El contador parte el numero en su propio <span>: hay que mirar el texto entero. */
const textoDe = (frase: string) => (_: string, el: Element | null) =>
  el?.textContent?.replace(/\s+/g, " ").trim() === frase;

/** Como textoDe, pero por el inicio: el contador anade «· N cerrados» al final. */
const empiezaCon = (frase: string) => (_: string, el: Element | null) =>
  el?.tagName === "P" &&
  (el.textContent ?? "").replace(/\s+/g, " ").trim().startsWith(frase);

const conHuecos = (n: number) => ({
  ...estado,
  huecos: Array.from({ length: n }, (_, i) => ({
    nivel: "falta_dato",
    codigo: "META-01",
    ubicacion: `u${i}`,
    mensaje: `hueco ${i}`,
    propuesta: null,
  })),
});

it("con pocos huecos arranca en la lista completa", () => {
  render(<WizardHuecos estado={conHuecos(5) as any} onEstado={() => {}} />);

  expect(screen.getByRole("radio", { name: /lista/i })).toBeChecked();
  expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(5);
});

it("con muchos huecos arranca en foco: una tarjeta a la vez", () => {
  render(<WizardHuecos estado={conHuecos(30) as any} onEstado={() => {}} />);

  expect(screen.getByRole("radio", { name: /uno a la vez/i })).toBeChecked();
  expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(1);
  expect(screen.getByText(textoDe("Inconsistencia 1 de 30"))).toBeInTheDocument();
});

it("se puede cambiar de modo a mano", async () => {
  render(<WizardHuecos estado={conHuecos(30) as any} onEstado={() => {}} />);

  await userEvent.click(screen.getByRole("radio", { name: /lista/i }));

  expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(30);
});

it("en foco, avanzar mueve al hueco siguiente", async () => {
  render(<WizardHuecos estado={conHuecos(30) as any} onEstado={() => {}} />);

  await userEvent.click(screen.getByRole("button", { name: /siguiente/i }));

  expect(screen.getByText(textoDe("Inconsistencia 2 de 30"))).toBeInTheDocument();
});

it("en foco, guardar salta solo al siguiente hueco pendiente", async () => {
  // Con la numeracion estable la tarjeta resuelta se queda en su sitio, en
  // verde; si el foco no se mueve, el analista tiene que pulsar "Siguiente"
  // despues de cada guardado.
  const { resolver } = await import("@/lib/api");
  const est = conHuecos(30);
  vi.mocked(resolver).mockResolvedValue({
    manifiesto: est.manifiesto,
    huecos: est.huecos.slice(1),
  } as any);

  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  expect(screen.getByText(textoDe("Inconsistencia 1 de 30"))).toBeInTheDocument();

  await userEvent.type(screen.getByLabelText(/tiempo de resolucion/i), "5 dias");
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));

  // Tras guardar, el contador dice «Inconsistencia 2 de 30 · 1 cerrados».
  expect(await screen.findByText(empiezaCon("Inconsistencia 2 de 30"))).toBeInTheDocument();
});

it("explica qué es una inconsistencia y qué implica 'lo configuro a mano'", () => {
  render(<WizardHuecos estado={estado as any} onEstado={() => {}} />);
  expect(
    screen.getByText(/Resuelve cada tarjeta y se habilita la descarga/),
  ).toBeInTheDocument();
  // Lo importante: que "lo configuro a mano" no se venda como un atajo gratis.
  expect(screen.getByText(/No desaparece el trabajo, lo mueve/)).toBeInTheDocument();
});

it("con la puerta abierta, el riel dice cuál .gpm es cuál", () => {
  const est = { ...estado, huecos: [], reconocidos: [] as [string, string][] };
  render(<WizardHuecos estado={est as any} onEstado={() => {}} />);
  const riel = screen.getByRole("complementary", { name: /entrega/i });
  expect(within(riel).getByText(/es el que se importa de verdad/)).toBeInTheDocument();
  expect(within(riel).getByText(/sin llenar nada/)).toBeInTheDocument();
});
