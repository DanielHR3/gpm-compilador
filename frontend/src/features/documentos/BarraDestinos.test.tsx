// frontend/src/features/documentos/BarraDestinos.test.tsx
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import type { ResumenDocumentos } from "@/lib/types";

import BarraDestinos from "./BarraDestinos";

const resumen = (por: Partial<ResumenDocumentos["por_destino"]>): ResumenDocumentos => ({
  total: 0, decididos: 0, ya_no_se_piden: 0, agregados: [], completo: false, titular: "",
  simplificacion: [],
  por_destino: { elimina: 0, conserva: 0, consulta: 0, sistema: 0, sin_destino: 0, ...por },
});

it("pinta un tramo por destino con su cuenta escrita, y una leyenda", () => {
  render(<BarraDestinos resumen={resumen({ elimina: 3, conserva: 2, sin_destino: 1 })} />);

  expect(screen.getByRole("img", { name: /documentos por destino/i })).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: "Se elimina: 3" })).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: "Se conserva: 2" })).toBeInTheDocument();
  expect(screen.getByRole("listitem", { name: "Sin destino: 1" })).toBeInTheDocument();
  expect(screen.queryByRole("listitem", { name: /consulta/i })).toBeNull();
  expect(screen.queryByRole("table")).toBeNull();
});

it("sin documentos no pinta una barra vacía", () => {
  render(<BarraDestinos resumen={resumen({})} />);
  expect(screen.queryByRole("img")).toBeNull();
});
