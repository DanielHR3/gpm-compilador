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
  // TODO(SP2): full estimacion card + grouped problemas view. SP1 solo pinta
  // `problemas` como lista y una linea con `estimacion.nivel`/`dias`.
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

/**
 * Una clausula "Y" de una `Condicion` (`src/gpmc/nucleo/manifiesto.py::Clausula`).
 */
export type Clausula = {
  campo: string;
  igual: string;
  operador: "==" | "!=";
};

/**
 * Condicion de visibilidad/transicion, con clausulas "Y" opcionales
 * (`src/gpmc/nucleo/manifiesto.py::Condicion`). `y` siempre viaja explicito
 * (nunca `undefined`) para que el cliente no tenga que distinguir "sin Y" de
 * "todavia no se cargo".
 */
export type Condicion = Clausula & { y: Clausula[] };

/**
 * Una rama de compuerta, tal como la expone
 * `GET /api/v1/expedientes/{sid}/compuerta/{gate_id}`
 * (`src/gpmc/extractores/expediente.py::ramas_de_compuerta`).
 */
export type RamaCompuerta = {
  a: string;
  a_nombre: string;
  etiqueta: string;
};

/** Cuerpo 200 de `GET /api/v1/expedientes/{sid}/compuerta/{gate_id}`. */
export type EstructuraCompuerta = {
  predecesora: string;
  ramas: RamaCompuerta[];
};

/**
 * Un campo del manifiesto, aplanado desde `manifiesto.pantallas[].campos[]`
 * por `camposDelManifiesto` (`api.ts`). `catalogo` es `[]` si el campo no
 * trae uno.
 */
export type CampoManifiesto = {
  nombre: string;
  etiqueta: string;
  catalogo: { etiqueta: string; valor: string }[];
};
