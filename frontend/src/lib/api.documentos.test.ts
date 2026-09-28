// frontend/src/lib/api.documentos.test.ts
import { afterEach, expect, it, vi } from "vitest";

import {
  aceptarVerificados, analizarDocumentos, decidirDestino, leerDocumentos, urlDescargaDocumentos,
} from "./api";

const SID = "a".repeat(16);
const BASE = `/api/v1/expedientes/${SID}/documentos`;

afterEach(() => vi.unstubAllGlobals());

function respuesta(cuerpo: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => cuerpo } as Response;
}

function conFetch(cuerpo: unknown, status = 200) {
  const f = vi.fn().mockResolvedValue(respuesta(cuerpo, status));
  vi.stubGlobal("fetch", f);
  return f;
}

it("lee los documentos de la sesión", async () => {
  const f = conFetch({ disponible: true, documentos: [] });
  expect((await leerDocumentos(SID)).disponible).toBe(true);
  expect(f.mock.calls[0][0]).toBe(BASE);
});

it("pide el análisis por POST", async () => {
  const f = conFetch({ estado: "analizando" }, 202);
  expect((await analizarDocumentos(SID)).estado).toBe("analizando");
  expect(f.mock.calls[0]).toEqual([`${BASE}/analizar`, { method: "POST" }]);
});

it("el candado cerrado sale como ErrorApi 409 con su motivo", async () => {
  conFetch({ error: "Hace falta la licencia." }, 409);
  await expect(analizarDocumentos(SID)).rejects.toMatchObject({
    status: 409, error: "Hace falta la licencia.",
  });
});

it("decide el destino de un documento", async () => {
  const f = conFetch({ disponible: true, documentos: [] });
  await decidirDestino(SID, "abc123", "elimina", "Se valida con la CURP.");
  const [url, init] = f.mock.calls[0];
  expect(url).toBe(`${BASE}/abc123/decision`);
  expect(JSON.parse(init.body)).toEqual({ destino: "elimina", motivo: "Se valida con la CURP." });
});

it("acepta de una vez lo verificado", async () => {
  const f = conFetch({ disponible: true, documentos: [] });
  await aceptarVerificados(SID);
  expect(f.mock.calls[0]).toEqual([`${BASE}/aceptar-verificados`, { method: "POST" }]);
});

it("da la URL de la descarga sin pedirla", () => {
  expect(urlDescargaDocumentos(SID)).toBe(`${BASE}/descarga`);
});
