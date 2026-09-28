// frontend/src/lib/api.comparativa.test.ts
import { afterEach, expect, it, vi } from "vitest";

import { declararMetrica, leerComparativa, urlDocumentoComparativa } from "./api";

const SID = "a".repeat(16);

afterEach(() => vi.unstubAllGlobals());

function respuesta(cuerpo: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => cuerpo } as Response;
}

it("lee la comparativa de la sesión", async () => {
  const fetchFalso = vi.fn().mockResolvedValue(respuesta({ disponible: false, motivo: "x" }));
  vi.stubGlobal("fetch", fetchFalso);

  const c = await leerComparativa(SID);

  expect(fetchFalso.mock.calls[0][0]).toBe(`/api/v1/expedientes/${SID}/comparativa`);
  expect(c.disponible).toBe(false);
});

it("declara una métrica por POST con JSON", async () => {
  const fetchFalso = vi.fn().mockResolvedValue(respuesta({ disponible: true }));
  vi.stubGlobal("fetch", fetchFalso);

  await declararMetrica(SID, "visitas", "2", "0");

  const [url, init] = fetchFalso.mock.calls[0];
  expect(url).toBe(`/api/v1/expedientes/${SID}/comparativa/declarar`);
  expect(init.method).toBe("POST");
  expect(JSON.parse(init.body)).toEqual({ clave: "visitas", antes: "2", despues: "0" });
});

it("un 422 al declarar sale como ErrorApi", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respuesta({ error: "no es una métrica" }, 422)));

  await expect(declararMetrica(SID, "visitas", "2", "0")).rejects.toMatchObject({ status: 422 });
});

it("da la URL del documento sin pedirlo", () => {
  expect(urlDocumentoComparativa(SID)).toBe(
    `/api/v1/expedientes/${SID}/comparativa/documento`,
  );
});
