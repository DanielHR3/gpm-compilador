import { describe, expect, it } from "vitest";

import type { EstadoExpediente } from "@/lib/types";

import { descargasDe } from "./descargas";

const ESTADO = {
  sid: "a".repeat(16),
  manifiesto: {
    tramite: { nombre: "Reposición" },
    pantallas: [
      { id: "p1", nombre: "Solicitud", campos: [{ nombre: "curp" }, { nombre: "placa" }] },
      { id: "p2", nombre: "Revisión", campos: [{ nombre: "ok" }] },
    ],
    flujo: { tareas: [{ id: "t1" }, { id: "t2" }], conexiones: [] },
    actores: [{ id: "ciudadano" }],
    acciones: [{ tipo: "documento", nombre: "Oficio" }, { tipo: "folio", nombre: "Folio" }],
  },
  huecos: [{ codigo: "DIC-07" }, { codigo: "FLU-01" }],
  tieneVistas: false,
} as unknown as EstadoExpediente;

function claves(e = ESTADO, desbloqueado = true) {
  return descargasDe(e, desbloqueado, "Faltan 2").map((d) => d.clave);
}

describe("lo que se puede descargar", () => {
  it("ofrece los dos .gpm, las observaciones y el manifiesto", () => {
    expect(claves()).toEqual([
      "gpm_produccion",
      "gpm_pruebas",
      "observaciones",
      "manifiesto",
    ]);
  });

  it("las vistas solo se ofrecen si el expediente las trae", () => {
    expect(claves()).not.toContain("vistas");
    expect(claves({ ...ESTADO, tieneVistas: true })).toContain("vistas");
  });

  it("con el expediente bloqueado solo se cierran los .gpm", () => {
    // Las observaciones hacen mas falta justo cuando algo bloquea: son lo que
    // hay que mandarle a quien documento el tramite.
    const bloqueadas = descargasDe(ESTADO, false, "Faltan 2")
      .filter((d) => d.bloqueada)
      .map((d) => d.clave);

    expect(bloqueadas).toEqual(["gpm_produccion", "gpm_pruebas"]);
  });

  it("un .gpm cerrado dice por qué", () => {
    const gpm = descargasDe(ESTADO, false, "Faltan 2 por resolver")[0];

    expect(gpm.motivo).toBe("Faltan 2 por resolver");
  });

  it("nada queda cerrado cuando el expediente está listo", () => {
    expect(descargasDe(ESTADO, true, "Faltan 2").some((d) => d.bloqueada)).toBe(false);
  });

  it("cada tarjeta cuenta lo que el compilador entendió", () => {
    const gpm = descargasDe(ESTADO, true, "")[0];

    expect(gpm.detalles.join(" ")).toContain("2 pantallas");
    expect(gpm.detalles.join(" ")).toContain("3 campos");
    expect(gpm.detalles.join(" ")).toContain("1 documento");
  });

  it("las observaciones cuentan las inconsistencias, no las pantallas", () => {
    const obs = descargasDe(ESTADO, true, "").find((d) => d.clave === "observaciones");

    expect(obs?.detalles.join(" ")).toContain("2 inconsistencias");
  });
});
