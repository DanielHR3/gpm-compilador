/**
 * Cliente tipado del REST `/api/v1` (`src/gpmc/web/api.py`).
 *
 * Todo `fetch` es relativo (`/api/v1/...`, mismo origen que la SPA servida en
 * `/app`). Los endpoints JSON pasan por `pedirJson`, que convierte cualquier
 * respuesta 4xx/5xx en un `ErrorApi`. Los dos endpoints de descarga (`gpm`,
 * `manifiesto`) solo exponen su URL: los consume `<a href>` o un `fetch` del
 * llamante, no este modulo.
 */

import type {
  Bloqueante,
  EstadoExpediente,
  Hueco,
  Resolucion,
} from "./types";

const BASE = "/api/v1";

/**
 * Error de cualquier respuesta no-ok de `/api/v1`. Todo cuerpo 4xx trae
 * `error`; el 413 de `crear` añade `archivos`, el 409 de `gpm` añade
 * `bloqueantes`.
 */
export class ErrorApi extends Error {
  readonly status: number;
  readonly error: string;
  readonly archivos?: string[];
  readonly bloqueantes?: Bloqueante[];

  constructor(
    status: number,
    error: string,
    extra?: { archivos?: string[]; bloqueantes?: Bloqueante[] },
  ) {
    super(error);
    this.name = "ErrorApi";
    this.status = status;
    this.error = error;
    if (extra?.archivos) this.archivos = extra.archivos;
    if (extra?.bloqueantes) this.bloqueantes = extra.bloqueantes;
  }

  /** Construye el error desde el cuerpo JSON (ya parseado) de la respuesta. */
  static desde(status: number, cuerpo: unknown): ErrorApi {
    const o =
      typeof cuerpo === "object" && cuerpo !== null
        ? (cuerpo as Record<string, unknown>)
        : {};
    const error = typeof o.error === "string" ? o.error : `HTTP ${status}`;
    const archivos = Array.isArray(o.archivos)
      ? (o.archivos as string[])
      : undefined;
    const bloqueantes = Array.isArray(o.bloqueantes)
      ? (o.bloqueantes as Bloqueante[])
      : undefined;
    return new ErrorApi(status, error, { archivos, bloqueantes });
  }
}

/** `fetch` + `res.json()`; lanza `ErrorApi` en cualquier `!res.ok`. */
async function pedirJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let cuerpo: unknown;
    try {
      cuerpo = await res.json();
    } catch {
      cuerpo = undefined;
    }
    throw ErrorApi.desde(res.status, cuerpo);
  }
  return (await res.json()) as T;
}

/**
 * Traduce el estado crudo del servidor (`tiene_vistas`, snake_case) al tipo de
 * la SPA (`tieneVistas`, camelCase). Único punto de conversión del borde,
 * compartido por `crearExpediente` y `leerExpediente`.
 */
function mapEstado(raw: unknown): EstadoExpediente {
  const o = (raw ?? {}) as {
    sid: string;
    manifiesto: Record<string, unknown>;
    huecos: Hueco[];
    estimacion: Record<string, unknown>;
    problemas: string[];
    tiene_vistas: boolean;
  };
  return {
    sid: o.sid,
    manifiesto: o.manifiesto,
    huecos: o.huecos,
    estimacion: o.estimacion,
    problemas: o.problemas,
    tieneVistas: o.tiene_vistas,
  };
}

/**
 * `POST /api/v1/expedientes` (multipart). No se fija `Content-Type`: el
 * navegador escribe el `boundary` del `multipart/form-data`.
 */
export async function crearExpediente(
  files: FormData,
): Promise<EstadoExpediente> {
  const raw = await pedirJson<unknown>(`${BASE}/expedientes`, {
    method: "POST",
    body: files,
  });
  return mapEstado(raw);
}

/** `GET /api/v1/expedientes/{sid}`. */
export async function leerExpediente(sid: string): Promise<EstadoExpediente> {
  const raw = await pedirJson<unknown>(`${BASE}/expedientes/${sid}`);
  return mapEstado(raw);
}

/** `POST /api/v1/expedientes/{sid}/resolver` — aplica resoluciones de huecos. */
export async function resolver(
  sid: string,
  resoluciones: Resolucion[],
): Promise<{ manifiesto: Record<string, unknown>; huecos: Hueco[] }> {
  return pedirJson(`${BASE}/expedientes/${sid}/resolver`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resoluciones }),
  });
}

/**
 * `POST /api/v1/expedientes/{sid}/reconocer` — marca un hueco `falta_dato`
 * como "se configura a mano en la plataforma".
 */
export async function reconocer(
  sid: string,
  codigo: string,
  ubicacion: string,
): Promise<{ huecos: Hueco[]; reconocidos: [string, string][] }> {
  return pedirJson(`${BASE}/expedientes/${sid}/reconocer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo, ubicacion }),
  });
}

/** URL de descarga del `.gpm` (no hace `fetch`). */
export function urlGpm(
  sid: string,
  modo: "produccion" | "pruebas" = "produccion",
): string {
  return `${BASE}/expedientes/${sid}/gpm?modo=${modo}`;
}

/** URL del `manifiesto.yaml` en texto (no hace `fetch`). */
export function urlManifiesto(sid: string): string {
  return `${BASE}/expedientes/${sid}/manifiesto`;
}
