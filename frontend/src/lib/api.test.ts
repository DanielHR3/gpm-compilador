import { afterEach, describe, expect, it, vi } from "vitest";

import {
  crearExpediente,
  ErrorApi,
  leerExpediente,
  resolver,
  urlGpm,
} from "./api";
import type { Resolucion } from "./types";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("crearExpediente", () => {
  it("devuelve el estado en 201", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true, status: 201,
      json: async () => ({ sid: "a".repeat(16), manifiesto: {}, huecos: [],
        estimacion: {}, problemas: [], tiene_vistas: false }),
    }));
    const est = await crearExpediente(new FormData());
    expect(est.sid).toHaveLength(16);
  });

  it("lanza ErrorApi con los nombres en 413", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 413, json: async () => ({ error: "grande", archivos: ["x.md"] }),
    }));
    await expect(crearExpediente(new FormData())).rejects.toMatchObject(
      { status: 413, archivos: ["x.md"] });
  });
});

describe("crearExpediente (borde del multipart)", () => {
  it("mapea tiene_vistas -> tieneVistas y no fija Content-Type", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 201,
      json: async () => ({ sid: "b".repeat(16), manifiesto: {}, huecos: [],
        estimacion: {}, problemas: [], tiene_vistas: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const est = await crearExpediente(new FormData());
    expect(est.tieneVistas).toBe(true);
    expect(est).not.toHaveProperty("tiene_vistas");

    const init = (fetchMock.mock.calls[0][1] ?? {}) as RequestInit;
    expect(init.headers).toBeUndefined();
    expect(init.body).toBeInstanceOf(FormData);
  });
});

describe("resolver", () => {
  it("devuelve {manifiesto, huecos} y postea un cuerpo con resoluciones", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ manifiesto: { a: 1 }, huecos: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const resoluciones: Resolucion[] = [
      { tipo: "meta01", ubicacion: "metadatos", valor: "5 días" },
    ];
    const res = await resolver("s".repeat(16), resoluciones);
    expect(res).toEqual({ manifiesto: { a: 1 }, huecos: [] });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toHaveProperty("resoluciones");
  });
});

describe("leerExpediente", () => {
  it("rechaza con un ErrorApi de status 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 404, json: async () => ({ error: "sesión no encontrada" }),
    }));
    await expect(leerExpediente("x".repeat(16))).rejects.toBeInstanceOf(ErrorApi);
    await expect(leerExpediente("x".repeat(16))).rejects.toMatchObject({ status: 404 });
  });
});

describe("urlGpm", () => {
  it("construye la URL de descarga sin hacer fetch", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(urlGpm("x".repeat(16), "pruebas")).toBe(
      "/api/v1/expedientes/xxxxxxxxxxxxxxxx/gpm?modo=pruebas");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
