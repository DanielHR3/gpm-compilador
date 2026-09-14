import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import NavegacionLateral from "./NavegacionLateral";

const sid = "a".repeat(16);

/** El <nav> que envuelve los pasos, para no chocar con otros roles del arbol. */
const pasos = () => screen.getByRole("navigation", { name: /proceso/i });

describe("NavegacionLateral", () => {
  test("sin expediente marca Insumos como el paso actual", () => {
    render(<NavegacionLateral sid={null} />);

    const actual = within(pasos()).getByRole("link", { current: "step" });
    expect(actual).toHaveTextContent(/insumos/i);
  });

  test("sin expediente, Revision, Simulacion y Descarga no son enlaces", () => {
    render(<NavegacionLateral sid={null} />);

    const nav = within(pasos());
    expect(nav.queryByRole("link", { name: /revisión/i })).toBeNull();
    expect(nav.queryByRole("link", { name: /simulación/i })).toBeNull();
    expect(nav.queryByRole("link", { name: /descarga/i })).toBeNull();
    // Siguen visibles: el analista tiene que ver el camino completo.
    expect(nav.getByText(/simulación/i)).toBeInTheDocument();
  });

  test("con expediente marca Revision como el paso actual", () => {
    render(<NavegacionLateral sid={sid} />);

    expect(
      within(pasos()).getByRole("link", { current: "step" }),
    ).toHaveTextContent(/revisión/i);
  });

  test("con expediente, Simulacion apunta al simulador de ese sid", () => {
    render(<NavegacionLateral sid={sid} />);

    expect(
      within(pasos()).getByRole("link", { name: /simulación/i }),
    ).toHaveAttribute("href", `/simulador/${sid}`);
  });

  test("Historial esta siempre disponible", () => {
    render(<NavegacionLateral sid={null} />);

    expect(screen.getByRole("link", { name: /historial/i })).toHaveAttribute(
      "href",
      "/historial",
    );
  });
});
