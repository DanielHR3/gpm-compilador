import { afterEach, describe, expect, it, vi } from "vitest";

import {
  camposDelManifiesto,
  crearExpediente,
  ErrorApi,
  leerCompuerta,
  leerExpediente,
  resolver,
  resolverCompuertaCampo,
  resolverCompuertaRamas,
  resolverDic08,
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

describe("resolverDic08", () => {
  it("postea la resolucion con la condicion", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ manifiesto: {}, huecos: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await resolverDic08("a".repeat(16), "p1::estado",
      { campo: "estado", igual: "hidalgo", operador: "!=", y: [] });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/expedientes/aaaaaaaaaaaaaaaa/resolver");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.resoluciones[0]).toMatchObject(
      { tipo: "dic08", ubicacion: "p1::estado" });
  });
});

describe("resolverCompuertaCampo", () => {
  it("postea tipo mmd04campo con el gate id y el campo", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ manifiesto: {}, huecos: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await resolverCompuertaCampo("a".repeat(16), "g1", "procede");
    const body = JSON.parse(
      (fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(body.resoluciones[0]).toEqual(
      { tipo: "mmd04campo", ubicacion: "g1", campo: "procede" });
  });
});

describe("resolverCompuertaRamas", () => {
  it("postea tipo mmd04rama con las ramas resueltas", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ manifiesto: {}, huecos: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const ramas = [
      { a: "t2", condicion: { campo: "procede", igual: "si", operador: "==" as const, y: [] } },
      { a: "t3", condicion: { campo: "procede", igual: "no", operador: "==" as const, y: [] } },
    ];
    await resolverCompuertaRamas("a".repeat(16), "g1", ramas);
    const body = JSON.parse(
      (fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(body.resoluciones[0]).toEqual(
      { tipo: "mmd04rama", ubicacion: "g1", ramas });
  });
});

describe("leerCompuerta", () => {
  it("hace GET a /compuerta/{gateId} y devuelve la estructura", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ predecesora: "t1", ramas: [
        { a: "t2", a_nombre: "Aprobar", etiqueta: "si" }] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const est = await leerCompuerta("a".repeat(16), "g1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/expedientes/aaaaaaaaaaaaaaaa/compuerta/g1", undefined);
    expect(est).toEqual({ predecesora: "t1", ramas: [
      { a: "t2", a_nombre: "Aprobar", etiqueta: "si" }] });
  });
});

describe("camposDelManifiesto", () => {
  it("aplana pantallas y catalogos", () => {
    const m = { pantallas: [{ campos: [
      { nombre: "estado", etiqueta: "Estado",
        catalogo: [{ etiqueta: "Hidalgo", valor: "hidalgo" }] }] }] };
    const cs = camposDelManifiesto(m as unknown as Record<string, unknown>);
    expect(cs).toEqual([{ nombre: "estado", etiqueta: "Estado",
      catalogo: [{ etiqueta: "Hidalgo", valor: "hidalgo" }] }]);
  });

  it("usa catalogo vacio si el campo no lo trae, y tolera formas raras", () => {
    const m = { pantallas: [
      { campos: [{ nombre: "folio", etiqueta: "Folio" }] },
      { campos: "no es un arreglo" },
      "no es un objeto",
    ] };
    const cs = camposDelManifiesto(m as unknown as Record<string, unknown>);
    expect(cs).toEqual([{ nombre: "folio", etiqueta: "Folio", catalogo: [] }]);
  });

  it("devuelve [] si el manifiesto no trae pantallas", () => {
    expect(camposDelManifiesto({} as Record<string, unknown>)).toEqual([]);
  });
});
