/**
 * Tipos del dominio `/api/v1`, en el borde entre el servidor y la SPA.
 *
 * Espejo de lo que devuelve `src/gpmc/web/api.py`, con una sola traduccion
 * deliberada: el servidor emite `tiene_vistas` (snake_case) y aqui vive como
 * `tieneVistas` (camelCase). Esa conversion la hace `mapEstado` en `api.ts`.
 */

/** Vista serializable de un `Hueco` (`src/gpmc/nucleo/huecos.py::HuecoOut`). */
export type Hueco = {
  nivel: string;
  codigo: string;
  ubicacion: string;
  mensaje: string;
  propuesta: string | null;
};

/**
 * Estimacion de esfuerzo (`src/gpmc/estimador.py`). Se deja laxa a proposito
 * para SP1: el servidor la manda como `dataclasses.asdict(...)` y la SPA aun no
 * la consume campo a campo. Forma real conocida: `metricas`, `nivel`, `dias`,
 * `motivos`, `advertencia`.
 */
export type Estimacion = Record<string, unknown>;

/**
 * Cuerpo de las respuestas 200/201 de `/api/v1/expedientes`, ya en camelCase.
 * `manifiesto` queda como `Record<string, unknown>`: es el `model_dump` del
 * manifiesto Pydantic, que la SPA de SP1 no tipa todavia.
 */
export type EstadoExpediente = {
  sid: string;
  manifiesto: Record<string, unknown>;
  huecos: Hueco[];
  estimacion: Estimacion;
  problemas: string[];
  tieneVistas: boolean;
};

/**
 * Una resolucion de hueco para `POST /api/v1/expedientes/{sid}/resolver`
 * (`src/gpmc/web/api.py::ResolucionIn`).
 */
export type Resolucion = {
  tipo: "mmd03" | "meta01" | "meta02" | "api03";
  ubicacion: string;
  valor: string;
};

/**
 * Un hueco que impide entregar el `.gpm`, tal como lo lista el 409 de
 * `GET /api/v1/expedientes/{sid}/gpm`.
 */
export type Bloqueante = {
  codigo: string;
  ubicacion: string;
  mensaje: string;
};
