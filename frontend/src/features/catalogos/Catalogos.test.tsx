import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  leerCatalogos: vi.fn().mockResolvedValue({
    catalogos: [
      { clave: "mgee", proveedor: "INEGI", tipo: "catalogo",
        url: "https://gaia.inegi.org.mx/wscatgeo/v2/mgee",
        sinonimos: ["estado", "inegi"], campos_respuesta: [] },
      { clave: "consultacurpn", proveedor: "SIPUBEH", tipo: "consulta",
        url: "https://sipubeh.hidalgo.gob.mx/efirma/api/consultacurpn?curp=@@{padre}",
        sinonimos: ["curp", "sipubeh"], campos_respuesta: ["nombres", "apePat", "apeMat"] },
    ],
    nota: "Solo se listan los endpoints que el compilador emite. Los que exigen credencial no salen aquí.",
  }),
}));

import Catalogos from "./Catalogos";

it("pinta una fila por catalogo con proveedor, que hace y que lo activa", async () => {
  render(<Catalogos />);
  const fila = await screen.findByRole("row", { name: /INEGI/ });
  expect(fila).toHaveTextContent(/lista/i);          // "catalogo" se lee como lista
  expect(fila).toHaveTextContent(/estado/);
  const curp = screen.getByRole("row", { name: /SIPUBEH/ });
  expect(curp).toHaveTextContent(/consulta/i);
  expect(curp).toHaveTextContent(/nombres, apePat, apeMat/);
});

it("dice cuantos conoce y que lo de credencial no se lista", async () => {
  render(<Catalogos />);
  expect(await screen.findByText(/2 endpoints/)).toBeInTheDocument();
  expect(screen.getByText(/exigen credencial/i)).toBeInTheDocument();
});

it("mientras carga no pinta la tabla vacia como si no hubiera nada", () => {
  render(<Catalogos />);
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.getByText(/cargando/i)).toBeInTheDocument();
});
