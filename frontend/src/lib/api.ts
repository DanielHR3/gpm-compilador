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
  Adjunto,
  Bloqueante,
  CampoManifiesto,
  ClaveDocumento,
  Condicion,
  EstadoExpediente,
  EstadoGenerados,
  EstructuraCompuerta,
  GeneradosOut,
  Hueco,
  PropuestasOut,
  Resolucion,
  ResultadoDecision,
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
    // `error` es la clave primaria de `/api/v1`; los 422 de FastAPI traen
    // `{"detail": [...]}` (o `detail` string en un `HTTPException`), asi que se
    // usa como respaldo antes de caer al generico `HTTP <status>`.
    const error =
      typeof o.error === "string"
        ? o.error
        : mensajeDeDetail(o.detail) ?? `HTTP ${status}`;
    const archivos = Array.isArray(o.archivos)
      ? (o.archivos as string[])
      : undefined;
    const bloqueantes = Array.isArray(o.bloqueantes)
      ? (o.bloqueantes as Bloqueante[])
      : undefined;
    return new ErrorApi(status, error, { archivos, bloqueantes });
  }
}

/**
 * Extrae un mensaje legible del `detail` de un 422 de FastAPI: string directo,
 * o array de `{ msg }`. Devuelve `null` si no hay nada aprovechable.
 */
function mensajeDeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) =>
        d && typeof d === "object" &&
        typeof (d as Record<string, unknown>).msg === "string"
          ? ((d as Record<string, unknown>).msg as string)
          : typeof d === "string"
            ? d
            : null,
      )
      .filter((m): m is string => m !== null);
    if (msgs.length > 0) return msgs.join("; ");
  }
  return null;
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
    reconocidos?: [string, string][];
    adjuntos?: Adjunto[];
    propuestas_pendientes?: boolean;
  };
  return {
    sid: o.sid,
    manifiesto: o.manifiesto,
    huecos: o.huecos,
    estimacion: o.estimacion,
    problemas: o.problemas,
    tieneVistas: o.tiene_vistas,
    // Un servidor viejo no lo manda: se cae a vacio en vez de reventar.
    reconocidos: o.reconocidos ?? [],
    adjuntos: o.adjuntos ?? [],
    // Un servidor viejo no lo manda: sin propuestas, como siempre.
    propuestasPendientes: o.propuestas_pendientes ?? false,
  };
}

/**
 * `POST /api/v1/expedientes` (multipart). No se fija `Content-Type`: el
 * navegador escribe el `boundary` del `multipart/form-data`.
 */
/** A qué zona va cada archivo de una carpeta, según `POST /clasificar`. */
export type Asignacion = {
  as_is: string | null;
  to_be: string | null;
  diccionario: string | null;
  vistas: string | null;
  adjuntos: string[];
  documentos: string[];
  ignorados: string[];
  avisos: string[];
};

/**
 * Reparte los nombres de una carpeta de expediente en las zonas del asistente.
 *
 * Manda SOLO los nombres, no los bytes: así el navegador puede pintar el
 * reparto antes de subir nada, y la carpeta no viaja dos veces. El criterio
 * vive en el servidor (`web/clasificador.py`), que reutiliza la normalización
 * de nombres del extractor.
 */
export async function clasificar(archivos: string[]): Promise<Asignacion> {
  return pedirJson<Asignacion>(`${BASE}/clasificar`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ archivos }),
  });
}

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
export interface CatalogoOut {
  clave: string;
  proveedor: string;
  tipo: "catalogo" | "consulta";
  url: string;
  sinonimos: string[];
  campos_respuesta: string[];
}
export interface CatalogosOut {
  catalogos: CatalogoOut[];
  nota: string;
}

/** `GET /api/v1/catalogos` — lo que el compilador sabe emitir. Solo lectura. */
export async function leerCatalogos(): Promise<CatalogosOut> {
  return pedirJson(`${BASE}/catalogos`);
}

export interface TramiteHistorial {
  sid: string;
  nombre: string;
  dependencia: string;
  /** ISO 8601 con zona: ultima vez que alguien trabajo en la sesion. */
  modificado: string;
}
export interface HistorialOut {
  tramites: TramiteHistorial[];
}

/** `GET /api/v1/historial` — expedientes del almacen, del mas reciente al mas viejo. */
export async function leerHistorial(): Promise<HistorialOut> {
  return pedirJson(`${BASE}/historial`);
}

export interface ConteoTablero { nombre: string; tramites: number; porcentaje: number; etiqueta?: string }
export interface HuecoTablero { codigo: string; tramites: number; total: number }
export interface ComplejidadTablero {
  clave: string; nombre: string; dependencia: string; nivel: string;
  metricas: { tareas: number; bifurcaciones: number; vistas: number; campos: number; acciones: number; integraciones: number };
}
export interface TableroOut {
  total_tramites: number;
  dependencias: { nombre: string; tramites: number }[];
  ultimo_registro: string | null;
  requisitos: ConteoTablero[];
  campos_compartidos: ConteoTablero[];
  huecos: HuecoTablero[];
  complejidad: ComplejidadTablero[];
  catalogos: { clave: string; proveedor?: string; descripcion?: string; tramites: number }[];
  actividad: { semana: string; tramites: number }[];
  indicadores: { requisitos_distintos: number; promedio_campos: number; promedio_huecos: number; con_integracion: number };
  matriz_huecos: MatrizTablero;
  matriz_requisitos: MatrizTablero;
  niveles: { nivel: string; tramites: number }[];
  metricas_max: Record<string, number>;
}
export interface MatrizTablero { filas: string[]; columnas: string[]; celdas: number[][]; maximo: number }

/** `GET /api/v1/tablero?dependencia=` — cuentas del tablero de Simplificación. Solo agregados. */
export async function leerTablero(dependencia?: string): Promise<TableroOut> {
  const q = dependencia ? `?dependencia=${encodeURIComponent(dependencia)}` : "";
  return pedirJson(`${BASE}/tablero${q}`);
}

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

/** Cuerpo de respuesta comun a `resolverDic08`/`resolverCompuertaCampo`/`resolverCompuertaRamas`. */
type EstadoResolver = { manifiesto: Record<string, unknown>; huecos: Hueco[] };

/**
 * `POST /api/v1/expedientes/{sid}/resolver` con `tipo: "dic08"` — fija
 * `condicion_visible` en el campo de `ubicacion` (`"pantalla::campo"`).
 */
export async function resolverDic08(
  sid: string,
  ubicacion: string,
  condicion: Condicion,
): Promise<EstadoResolver> {
  return pedirJson(`${BASE}/expedientes/${sid}/resolver`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resoluciones: [{ tipo: "dic08", ubicacion, condicion }],
    }),
  });
}

/**
 * `POST /api/v1/expedientes/{sid}/resolver` con `tipo: "mmd04campo"` — fija
 * el `@@campo` de la compuerta `gateId` y dispara el reensamblado del flujo.
 */
export async function resolverCompuertaCampo(
  sid: string,
  gateId: string,
  campo: string,
): Promise<EstadoResolver> {
  return pedirJson(`${BASE}/expedientes/${sid}/resolver`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resoluciones: [{ tipo: "mmd04campo", ubicacion: gateId, campo }],
    }),
  });
}

/**
 * `POST /api/v1/expedientes/{sid}/resolver` con `tipo: "mmd04rama"` — fija
 * una `Condicion` por cada rama de la compuerta `gateId` (respaldo cuando
 * `resolverCompuertaCampo` no basta).
 */
export async function resolverCompuertaRamas(
  sid: string,
  gateId: string,
  ramas: { a: string; condicion: Condicion }[],
): Promise<EstadoResolver> {
  return pedirJson(`${BASE}/expedientes/${sid}/resolver`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resoluciones: [{ tipo: "mmd04rama", ubicacion: gateId, ramas }],
    }),
  });
}

/**
 * `GET /api/v1/expedientes/{sid}/compuerta/{gate_id}` — estructura de una
 * compuerta (predecesora + ramas) para el respaldo por rama de `MMD-04`.
 */
export async function leerCompuerta(
  sid: string,
  gateId: string,
): Promise<EstructuraCompuerta> {
  return pedirJson(`${BASE}/expedientes/${sid}/compuerta/${gateId}`);
}

/**
 * Aplana `manifiesto.pantallas[].campos[]` en la lista de campos que consume
 * `ConstructorRegla`. El manifiesto llega del servidor como JSON no tipado
 * fuerte (`Record<string, unknown>`), asi que cada nivel se valida con
 * narrowing antes de leerlo; cualquier forma inesperada se descarta en vez de
 * lanzar. Un campo sin `catalogo` (o con uno mal formado) recibe `[]`.
 */
export function camposDelManifiesto(
  manifiesto: Record<string, unknown>,
): CampoManifiesto[] {
  const pantallas = manifiesto.pantallas;
  if (!Array.isArray(pantallas)) return [];

  const resultado: CampoManifiesto[] = [];
  for (const [indice, pantalla] of pantallas.entries()) {
    if (typeof pantalla !== "object" || pantalla === null) continue;
    const campos = (pantalla as Record<string, unknown>).campos;
    if (!Array.isArray(campos)) continue;

    for (const campo of campos) {
      if (typeof campo !== "object" || campo === null) continue;
      const c = campo as Record<string, unknown>;
      if (typeof c.nombre !== "string") continue;
      const etiqueta = typeof c.etiqueta === "string" ? c.etiqueta : "";
      const catalogoRaw = Array.isArray(c.catalogo) ? c.catalogo : [];
      const catalogo = catalogoRaw
        .filter(
          (e): e is Record<string, unknown> =>
            typeof e === "object" && e !== null &&
            typeof (e as Record<string, unknown>).etiqueta === "string" &&
            typeof (e as Record<string, unknown>).valor === "string",
        )
        .map((e) => ({
          etiqueta: e.etiqueta as string,
          valor: e.valor as string,
        }));
      resultado.push({ nombre: c.nombre, etiqueta, catalogo, pantalla: indice });
    }
  }
  return resultado;
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

/**
 * Un documento de apoyo del expediente.
 *
 * El nombre viaja en la ruta y puede traer espacios o acentos —«TO BE.png»—,
 * asi que se codifica; el servidor lo sanea otra vez al recibirlo.
 */
export function urlAdjunto(sid: string, nombre: string): string {
  return `${BASE}/expedientes/${sid}/adjuntos/${encodeURIComponent(nombre)}`;
}

/** `GET /api/v1/expedientes/{sid}/propuestas` — estado del generador y propuestas aceptables sin decidir. */
export async function leerPropuestas(sid: string): Promise<PropuestasOut> {
  return pedirJson<PropuestasOut>(`${BASE}/expedientes/${sid}/propuestas`);
}

/**
 * Anota qué hizo el analista con una propuesta. NO escribe en el manifiesto:
 * eso lo hace `resolverDic08`, que se llama antes. Si este registro falla,
 * la resolución ya quedó; es el registro lo que se reintenta.
 */
export async function decidirPropuesta(
  sid: string,
  id: string,
  decision: "aceptada" | "corregida" | "descartada",
  condicionFinal?: Condicion | null,
): Promise<{ ok: true }> {
  return pedirJson<{ ok: true }>(`${BASE}/expedientes/${sid}/propuestas/${id}/decision`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ decision, condicion_final: condicionFinal ?? null }),
  });
}

/** `POST /api/v1/expedientes/proponer` — crea la sesion con solo el AS-IS y lanza la generacion. */
export async function proponerExpediente(
  fd: FormData,
): Promise<{ sid: string; estado: EstadoGenerados }> {
  return pedirJson(`${BASE}/expedientes/proponer`, { method: "POST", body: fd });
}

/** `GET /api/v1/expedientes/{sid}/generados` — estado y borradores de la Fase 3. */
export async function leerGenerados(sid: string): Promise<GeneradosOut> {
  return pedirJson<GeneradosOut>(`${BASE}/expedientes/${sid}/generados`);
}

/**
 * El servidor contesta con dos formas distintas segun si el par quedo
 * resuelto. Se distinguen por `manifiesto`, que solo trae el expediente.
 */
function aResultado(raw: unknown): ResultadoDecision {
  const o = (raw ?? {}) as Record<string, unknown>;
  return "manifiesto" in o
    ? { tipo: "expediente", estado: mapEstado(raw) }
    : { tipo: "generados", generados: raw as GeneradosOut };
}

/** `POST /api/v1/expedientes/{sid}/generados/{documento}/decision`. */
export async function decidirDocumento(
  sid: string,
  documento: ClaveDocumento,
  decision: "aceptada" | "corregida" | "declinada",
  textoFinal?: string | null,
): Promise<ResultadoDecision> {
  const raw = await pedirJson<unknown>(
    `${BASE}/expedientes/${sid}/generados/${documento}/decision`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decision, texto_final: textoFinal ?? null }),
    },
  );
  return aResultado(raw);
}

/** `POST /api/v1/expedientes/{sid}/generados/{documento}/subir` (multipart `archivo`). */
export async function subirDocumento(
  sid: string,
  documento: ClaveDocumento,
  archivo: File,
): Promise<ResultadoDecision> {
  const fd = new FormData();
  fd.append("archivo", archivo);
  const raw = await pedirJson<unknown>(
    `${BASE}/expedientes/${sid}/generados/${documento}/subir`,
    { method: "POST", body: fd },
  );
  return aResultado(raw);
}
