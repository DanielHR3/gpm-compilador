import { expect, it } from "vitest";

import { redactarEvento } from "./lenguaje";

const fila = (accion: string, detalle = "") => ({ fecha: "2026-10-16T18:00:00+00:00", usuario: "x", dependencia: "", accion, sid: null, detalle, ip: null });

it("traduce las acciones y separa el código de rechazo", () => {
  expect(redactarEvento(fila("hueco.reconocer", "DIC-07"))).toEqual({ frase: "Reconoció la inconsistencia DIC-07 («lo configuro a mano»)", rechazo: null, fallo: false });
  expect(redactarEvento(fila("gpm.descargar", "produccion (409)"))).toMatchObject({ rechazo: 409, fallo: false });
  expect(redactarEvento(fila("gpm.descargar", "produccion (409)")).frase).toMatch(/Descargó el \.gpm de producción — el servidor la rechazó \(409\)/);
  expect(redactarEvento(fila("error.servidor", "RuntimeError en GET /x #abc (500)"))).toMatchObject({ fallo: true, rechazo: null });
});

it("un código desconocido se enseña tal cual, no se esconde", () => {
  expect(redactarEvento(fila("algo.nuevo", "x")).frase).toBe("algo.nuevo (x)");
});
