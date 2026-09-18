import { afterEach, expect, it, vi } from "vitest";

import { decidirPropuesta, leerPropuestas } from "./api";

afterEach(() => vi.restoreAllMocks());

it("leerPropuestas y decidirPropuesta pegan a las rutas nuevas", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ estado: "listo", motivo: null, propuestas: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  await leerPropuestas("a".repeat(16));
  expect(String(fetchMock.mock.calls[0][0])).toBe("/api/v1/expedientes/aaaaaaaaaaaaaaaa/propuestas");

  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }),
  );
  await decidirPropuesta("a".repeat(16), "p1", "corregida", { campo: "x", igual: "y", operador: "==", y: [] });
  const [url, init] = fetchMock.mock.calls[1];
  expect(String(url)).toBe("/api/v1/expedientes/aaaaaaaaaaaaaaaa/propuestas/p1/decision");
  expect(JSON.parse((init as RequestInit).body as string)).toEqual({
    decision: "corregida",
    condicion_final: { campo: "x", igual: "y", operador: "==", y: [] },
  });
});
