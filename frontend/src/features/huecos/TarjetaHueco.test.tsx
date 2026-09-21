import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  leerPropuestas: vi.fn(),
  decidirPropuesta: vi.fn(),
  resolver: vi.fn(),
  reconocer: vi.fn().mockResolvedValue({ huecos: [], reconocidos: [] }),
  resolverDic08: vi.fn(),
  camposDelManifiesto: () => [],
  leerCompuerta: vi.fn(),
  resolverCompuertaCampo: vi.fn(),
  resolverCompuertaRamas: vi.fn(),
  ErrorApi: class ErrorApi extends Error {},
}));

import TarjetaHueco from "./TarjetaHueco";

const sid = "a".repeat(16);

it("DIC-08: 'Lo configuro a mano' (ahora junto a Guardar) llama reconocer con codigo y ubicacion", async () => {
  const { reconocer } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::domicilio",
        mensaje: "no se pudo interpretar: «visible si es de otro estado»",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={onResuelto}
    />,
  );
  await userEvent.click(
    screen.getByRole("button", { name: /lo configuro a mano/i }),
  );
  expect(reconocer).toHaveBeenCalledWith(sid, "DIC-08", "p1::domicilio");
  expect(onResuelto).toHaveBeenCalled();
});

it("MMD-04: el enlace 'o lo configuro a mano' llama reconocer con codigo y ubicacion", async () => {
  const { reconocer } = await import("@/lib/api");
  const onResuelto = vi.fn();
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "MMD-04",
        ubicacion: "G",
        mensaje: "la compuerta no nombra ningun campo @@",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={onResuelto}
    />,
  );
  await userEvent.click(
    screen.getByRole("button", { name: /o lo configuro a mano/i }),
  );
  expect(reconocer).toHaveBeenCalledWith(sid, "MMD-04", "G");
  expect(onResuelto).toHaveBeenCalled();
});

it("META-04: dos clics seguidos en Guardar mandan una sola resolucion", async () => {
  const { resolver } = await import("@/lib/api");
  // La peticion queda en vuelo hasta que el test la suelte: el segundo clic
  // ocurre mientras la primera sigue abierta, que es el caso real del bug.
  let soltar!: (v: unknown) => void;
  vi.mocked(resolver).mockReturnValue(
    new Promise((res) => {
      soltar = res;
    }) as any,
  );

  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "META-04",
        ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  await userEvent.type(
    screen.getByLabelText(/nombre del tramite/i),
    "Constancia de residencia",
  );
  const boton = screen.getByRole("button", { name: /guardar/i });
  await userEvent.click(boton);
  await userEvent.click(boton);

  expect(resolver).toHaveBeenCalledTimes(1);
  expect(boton).toBeDisabled();

  soltar({ manifiesto: {}, huecos: [] });
});

it("META-04: mientras guarda, el boton lo dice y se anuncia como ocupado", async () => {
  const { resolver } = await import("@/lib/api");
  let soltar!: (v: unknown) => void;
  vi.mocked(resolver).mockReturnValue(
    new Promise((res) => {
      soltar = res;
    }) as any,
  );

  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "META-04",
        ubicacion: "metadatos",
        mensaje: "no se pudo determinar el nombre del tramite",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  await userEvent.type(
    screen.getByLabelText(/nombre del tramite/i),
    "Constancia de residencia",
  );
  await userEvent.click(screen.getByRole("button", { name: /guardar/i }));

  const ocupado = screen.getByRole("button", { name: /guardando/i });
  expect(ocupado).toHaveAttribute("aria-busy", "true");

  soltar({ manifiesto: {}, huecos: [] });
});

it("encabeza la tarjeta con el titulo en castellano, no con el codigo", () => {
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "MMD-03",
        ubicacion: "t-07",
        mensaje: "la tarea no dice quien la hace",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  expect(
    screen.getByRole("heading", { name: "Responsable de una tarea" }),
  ).toBeInTheDocument();
  // El codigo sigue existiendo, pero plegado en el detalle tecnico: lo que no
  // debe llevarlo es el encabezado.
  expect(screen.queryByRole("heading", { name: /MMD-03/ })).toBeNull();
  expect(screen.getByText(/ver detalle técnico/i).closest("details")).toHaveTextContent(
    "MMD-03",
  );
});

it("MMD-03: el mensaje crudo no se repite encima de la pregunta del control", () => {
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "MMD-03",
        ubicacion: "A",
        mensaje:
          "la tarea «📝 Usuario: Completar datos» no declara carril (:::clase); no se puede saber qué actor la ejecuta",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  // La pregunta la hace el control; el texto del compilador vive en el
  // detalle tecnico, no suelto encima.
  expect(
    screen.getByRole("heading", { name: /¿Quién hace «Completar datos»\?/ }),
  ).toBeInTheDocument();
  const sueltos = screen
    .queryAllByText(/no declara carril/)
    .filter((el) => el.closest("details") === null);
  expect(sueltos).toHaveLength(0);
});

it("un hueco de solo confirmar dice que no hay nada que llenar y se puede cerrar", async () => {
  const { reconocer } = await import("@/lib/api");
  render(
    <TarjetaHueco
      hueco={{
        nivel: "por_confirmar",
        codigo: "META-05",
        ubicacion: "metadatos",
        mensaje: "no se encontro homoclave; en tramites nuevos es normal, la asigna GPM",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  // Antes no habia ningun control: la tarjeta enunciaba un hecho y dejaba al
  // analista sin saber si tenia que hacer algo.
  expect(screen.getByText(/no tienes que llenar nada/i)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /entendido/i }));

  expect(reconocer).toHaveBeenCalledWith(sid, "META-05", "metadatos");
});


// El carril del diagrama dejo de ser bloqueante: MMD-03 llega colapsado en un
// solo hueco `por_confirmar` sobre "flujo" (ver `_colapsar_mmd03` en
// `extractores/expediente.py`). Ese hueco no nombra ninguna tarea, asi que un
// ControlActor sobre el mandaria `ubicacion: "flujo"` a `/resolver` y el backend
// contestaria 422 -- el mismo callejon sin salida que se acaba de cerrar.
const MMD03_COLAPSADO = {
  nivel: "por_confirmar" as const,
  codigo: "MMD-03",
  ubicacion: "flujo",
  mensaje:
    "3 nodo(s) del diagrama TO-BE no declaran carril (`classDef` + `:::clase`): " +
    "QA, QP, QM. El actor de cada tarea se tomó del Diccionario de Datos.",
  propuesta: null,
};

it("MMD-03 colapsado: no ofrece selector de actor, y sí dice qué pasa", () => {
  render(
    <TarjetaHueco
      hueco={MMD03_COLAPSADO}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  // Sin control, nadie redacta la pregunta: el mensaje crudo tiene que salir.
  expect(screen.getByText(/no declaran carril/)).toBeInTheDocument();
});

it("MMD-03 por nodo: sí ofrece selector, y también la salida a mano", () => {
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "MMD-03",
        ubicacion: "T1",
        mensaje: "la tarea «Captura la solicitud» no declara carril",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );

  expect(screen.getByRole("combobox")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /o lo configuro a mano/i }),
  ).toBeInTheDocument();
});

it("«lo configuro a mano» es un botón visible, no un texto gris", () => {
  // Es la decisión con más consecuencias del flujo —mueve el trabajo a la
  // plataforma— y estaba pintada como un enlace de 12 px que nadie ve.
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-08",
        ubicacion: "p1::rfc",
        mensaje: "la condición de visibilidad de 'RFC' (rfc) no se pudo interpretar: «x»",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={"a".repeat(16)}
      onResuelto={vi.fn()}
    />,
  );
  const b = screen.getByRole("button", { name: /a mano/i });
  expect(b.className).toMatch(/border/);
  expect(b.className).not.toMatch(/hover:underline/);
});

it("la tarjeta pinta el mensaje redactado, no el crudo del compilador", () => {
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-02",
        ubicacion: "p1",
        mensaje:
          "el catálogo de 'Estatus del Trámite' está declarado como pendiente en el Diccionario; no se emite",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );
  expect(
    screen.getByText(/quedó marcada como pendiente/),
  ).toBeInTheDocument();
  expect(screen.queryByText(/no se emite/)).not.toBeInTheDocument();
});

it("DIC-09: no ofrece «Lo configuro a mano», que ahi no se puede hacer", () => {
  // Visto en pantalla el 2026-09-21 con Reposicion cargada. Un nombre tecnico
  // repetido viene del Diccionario: en la plataforma NO hay nada que
  // configurar, asi que ese boton manda a la persona a un sitio sin solucion.
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-09",
        ubicacion: "p8",
        mensaje:
          "el nombre técnico '@@estatus_tramite' lo declaran dos campos; parece el mismo dato mostrado de nuevo",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );
  expect(screen.queryByRole("button", { name: /lo configuro a mano/i })).toBeNull();
  expect(screen.getByText(/se corrige en el Diccionario/i)).toBeTruthy();
});

it("DIC-09: manda al documento de observaciones, que es como llega a Simplificacion", () => {
  render(
    <TarjetaHueco
      hueco={{
        nivel: "falta_dato",
        codigo: "DIC-09",
        ubicacion: "p8",
        mensaje: "el nombre técnico '@@x' lo declaran dos campos",
        propuesta: null,
      }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );
  expect(screen.getByText(/Descargar observaciones/i)).toBeTruthy();
});

it("los demas huecos sin control siguen ofreciendo «Lo configuro a mano»", () => {
  // El contrapeso: sin el, quitar el boton a TODOS dejaria las dos de arriba
  // en verde y romperia la salida de los demas codigos.
  render(
    <TarjetaHueco
      hueco={{ nivel: "falta_dato", codigo: "DIC-02", ubicacion: "p1", mensaje: "lista pendiente", propuesta: null }}
      manifiesto={{}}
      sid={sid}
      onResuelto={vi.fn()}
    />,
  );
  expect(screen.getByRole("button", { name: /lo configuro a mano/i })).toBeTruthy();
});
