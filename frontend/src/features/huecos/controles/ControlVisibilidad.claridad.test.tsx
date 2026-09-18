/**
 * La tarjeta de DIC-08 la contesta alguien de Simplificacion, no quien programa
 * el compilador. Estas pruebas fijan las tres cosas que se lo impedian:
 * la frase que ella misma escribio estaba plegada bajo "Ver detalle tecnico",
 * el ejemplo de arriba era de otro tramite, y la unica salida valida cuando la
 * condicion no depende de ningun campo estaba hasta el final.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  resolverDic08: vi.fn().mockResolvedValue({ manifiesto: {}, huecos: [] }),
  camposDelManifiesto: () => [
    { nombre: "estado", etiqueta: "Estado", pantalla: 0, catalogo: [] },
  ],
}));

import ControlVisibilidad from "./ControlVisibilidad";

const HUECO = {
  nivel: "falta_dato" as const,
  codigo: "DIC-08",
  ubicacion: "p1::campos_con_error",
  mensaje:
    "la condición de visibilidad de 'Campos con Error' (campos_con_error) no se " +
    "pudo interpretar: «Solo si la validación de formato detecta errores al enviar»",
  propuesta: null,
};

function pintar(extra = {}) {
  return render(
    <ControlVisibilidad
      hueco={HUECO}
      sid={"a".repeat(16)}
      manifiesto={{}}
      onResuelto={vi.fn()}
      {...extra}
    />,
  );
}

it("la frase del Diccionario se lee sin abrir nada, junto a la pregunta", () => {
  pintar();
  const cita = screen.getByTestId("frase-diccionario");
  expect(cita).toHaveTextContent(/Solo si la validación de formato detecta errores/);
  // Y no vive dentro del panel tecnico plegado.
  const tecnico = screen.getByTestId("frase-diccionario").closest("details");
  expect(tecnico).toBeNull();
});

it("el ejemplo de otro tramite queda plegado, no encabezando la tarjeta", async () => {
  pintar();
  const resumen = screen.getByRole("group", { name: /ejemplo/i });
  // Cerrado de inicio: el ejemplo no compite con la frase real.
  expect(resumen).not.toHaveAttribute("open");
  await userEvent.click(within(resumen).getByText(/ejemplo/i));
  expect(
    within(resumen).getByText(/Muestra «RFC» solo cuando «Procedencia»/i),
  ).toBeInTheDocument();
});

it("la caja del valor no sugiere el valor de otro tramite", () => {
  pintar();
  expect(screen.getByLabelText(/valor de la condición 1/i)).toHaveAttribute(
    "placeholder",
    "este valor",
  );
});

it("cuando la frase no depende de un campo, configurar a mano es una salida visible", async () => {
  const onReconocer = vi.fn();
  pintar({ onReconocer });
  expect(
    screen.getByText(/no depende de otro campo del formulario/i),
  ).toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: /lo configuro a mano/i }),
  );
  expect(onReconocer).toHaveBeenCalled();
});

it("sin onReconocer no dibuja la salida: la tarjeta sigue sirviendo sola", () => {
  pintar();
  expect(
    screen.queryByRole("button", { name: /lo configuro a mano/i }),
  ).toBeNull();
});
