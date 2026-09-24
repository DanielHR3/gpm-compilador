import { afterEach, describe, expect, it, vi } from "vitest";

import { decidirDocumento, leerGenerados, proponerExpediente, subirDocumento } from "./api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

afterEach(() => vi.restoreAllMocks());

describe("cliente de la Fase 3", () => {
  it("proponerExpediente devuelve sid y estado (202 o 200)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(202, { sid: "a".repeat(16), estado: "generando" }));
    const r = await proponerExpediente(new FormData());
    expect(r).toEqual({ sid: "a".repeat(16), estado: "generando" });
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe("/api/v1/expedientes/proponer");
  });

  it("leerGenerados devuelve el estado tal cual", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(200, { estado: "listo", motivo: null, nombre: "X", diccionario: null, tobe: null }),
    );
    expect((await leerGenerados("a".repeat(16))).estado).toBe("listo");
  });

  it("decidirDocumento distingue EstadoExpediente de GeneradosOut por 'manifiesto'", async () => {
    const f = vi.spyOn(globalThis, "fetch");
    f.mockResolvedValueOnce(json(200, { estado: "listo", motivo: null, nombre: null, diccionario: null, tobe: null }));
    const a = await decidirDocumento("a".repeat(16), "diccionario", "aceptada");
    expect(a.tipo).toBe("generados");
    f.mockResolvedValueOnce(json(200, {
      sid: "a".repeat(16), manifiesto: {}, huecos: [], estimacion: {}, problemas: [],
      tiene_vistas: false, reconocidos: [], adjuntos: [],
    }));
    const b = await decidirDocumento("a".repeat(16), "tobe", "corregida", "# mío");
    expect(b.tipo).toBe("expediente");
    if (b.tipo === "expediente") expect(b.estado.tieneVistas).toBe(false);
    const cuerpo = JSON.parse(f.mock.calls[1][1]?.body as string);
    expect(cuerpo).toEqual({ decision: "corregida", texto_final: "# mío" });
  });

  it("subirDocumento manda multipart con 'archivo'", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(200, { estado: "listo", motivo: null, nombre: null, diccionario: null, tobe: null }),
    );
    await subirDocumento("a".repeat(16), "tobe", new File(["x"], "t.md"));
    expect(f.mock.calls[0][0]).toBe(`/api/v1/expedientes/${"a".repeat(16)}/generados/tobe/subir`);
    expect((f.mock.calls[0][1]?.body as FormData).get("archivo")).toBeInstanceOf(File);
  });
});
