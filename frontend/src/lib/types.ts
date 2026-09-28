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
/** Un documento de apoyo del expediente: se muestra, no se extrae. */
export type Adjunto = { nombre: string; tipo: "imagen" | "pdf" | "otro" };

export type EstadoExpediente = {
  sid: string;
  manifiesto: Record<string, unknown>;
  huecos: Hueco[];
  // TODO(SP2): full estimacion card + grouped problemas view. SP1 solo pinta
  // `problemas` como lista y una linea con `estimacion.nivel`/`dias`.
  estimacion: Estimacion;
  problemas: string[];
  tieneVistas: boolean;
  /**
   * Los `(codigo, ubicacion)` ya marcados como "se configuran a mano".
   * El servidor los conserva; sin sembrarlos aqui la SPA los perdia al
   * recargar y el wizard repintaba el hueco como pendiente.
   */
  reconocidos: [string, string][];
  adjuntos: Adjunto[];
  /** True si el generador de IA corrió (o corre) para esta sesión. */
  propuestasPendientes: boolean;
};

/**
 * Una resolucion de hueco para `POST /api/v1/expedientes/{sid}/resolver`
 * (`src/gpmc/web/api.py::ResolucionIn`).
 */
export type Resolucion = {
  tipo: "mmd03" | "meta01" | "meta02" | "meta04" | "api03";
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
  /** Indice de la pantalla donde se captura, empezando en 0. Sirve para saber
      si un campo se captura ANTES que otro: una condicion de visibilidad no
      puede mirar un campo de una pantalla posterior. */
  pantalla: number;
};

export type Cita = {
  fuente: "Diccionario de Datos";
  pantalla: string;
  pantalla_nombre: string;
  campo: string;
  texto: string;
};

/** Propuesta del generador de IA para un DIC-08. Solo llegan las aceptables sin decisión. */
export type Propuesta = {
  id: string;
  ubicacion: string;
  condicion: Condicion | null;
  motivo_modelo: string | null;
  confianza: "alta" | "media" | "baja";
  cita: Cita;
  veredicto: string;
  decision: "aceptada" | "corregida" | "descartada" | null;
  condicion_final: Condicion | null;
  creada: string;
  decidida: string | null;
};

export type PropuestasOut = {
  estado: "proponiendo" | "listo" | "error" | "sin_proveedor";
  motivo: string | null;
  propuestas: Propuesta[];
};

/** Fase 3: un documento propuesto desde el AS-IS (`agentes/fase3.py::Documento`). */
export type DecisionDocumento = "pendiente" | "aceptada" | "corregida" | "declinada";
export type DocumentoGenerado = {
  texto: string;
  version_prompt: string;
  ronda: number;
  huecos: Hueco[];
  decision: DecisionDocumento;
  /** Solo el Diccionario: pantallas y campos leidos por el extractor. */
  vista?: PantallaVista[];
};
export type EstadoGenerados = "generando" | "listo" | "error" | "sin_licencia";
/** `GET /api/v1/expedientes/{sid}/generados`. */
export type GeneradosOut = {
  estado: EstadoGenerados;
  motivo: string | null;
  nombre: string | null;
  diccionario: DocumentoGenerado | null;
  tobe: DocumentoGenerado | null;
  /** Que documento ya tiene archivo en la sesion (para abrir en el paso correcto). */
  insumos?: { diccionario: boolean; tobe: boolean };
  /** Lo que el agente fue haciendo, en orden, con la hora (ISO) de cada paso. */
  pasos?: PasoGenerado[];
};
export type PasoGenerado = { t: string; mensaje: string };

/** Quien esta dentro (spec 2026-09-25). El token no viaja aqui: va en cookie HttpOnly. */
export type Usuario = { correo: string; nombre: string; dependencia: string; rol?: "admin" | "analista" };
/** Una cuenta vista por el superusuario (`GET /api/v1/usuarios`). */
export type UsuarioAdmin = {
  correo: string; nombre: string; dependencia: string;
  rol: "admin" | "analista"; estado: "pendiente" | "activo" | "inactivo";
};
/** `GET /api/v1/sesion`. 404 = el servidor corre sin usuarios. */
export type SesionOut = { usuario: Usuario | null };
/** `POST /api/v1/sesion`. */
export type EntradaOut = { token: string; usuario: Usuario };
export type ClaveDocumento = "diccionario" | "tobe";
/**
 * Lo que devuelve una decision o una subida: el expediente ya extraido si
 * con esa el par quedo resuelto, o el estado de propuestas si falta el otro.
 */
export type ResultadoDecision =
  | { tipo: "expediente"; estado: EstadoExpediente }
  | { tipo: "generados"; generados: GeneradosOut };

/** `GET /api/v1/capacidades`. */
export type Capacidades = {
  proponer: boolean;
  motivo: string | null;
  /** El candado esta abierto sin licencia (pruebas internas con Gemini). */
  pruebas?: boolean;
};
/** Un campo del Diccionario propuesto, ya leido por el extractor. */
export type CampoVista = {
  etiqueta: string;
  tipo: string;
  obligatorio: boolean;
  opciones: string[];
  condicion: string | null;
};
export type PantallaVista = { id: string; nombre: string; actor: string; campos: CampoVista[] };

/** Comparativa de antes y después (`GET /api/v1/expedientes/{sid}/comparativa`). */
export type OrigenValor = "contado" | "leido" | "declarado" | "revisado" | "sin_dato";
export type ClaveMetrica =
  | "requisitos" | "pasos" | "actores" | "sistemas" | "tiempo" | "visitas" | "capturas";

export interface ValorComparado {
  texto: string;
  numero: number | null;
  unidad: string;
  origen: OrigenValor;
}

export interface MetricaComparada {
  clave: ClaveMetrica;
  nombre: string;
  antes: ValorComparado;
  despues: ValorComparado;
  diferencia: number | null;
  porcentaje: number | null;
}

export interface RequisitoComparado {
  nombre: string;
  destino: "conservado" | "eliminado" | "sin_destino" | "nuevo";
  fundamento: string;
}

export interface ComparativaOut {
  disponible: boolean;
  motivo: string;
  tramite: string;
  metricas: MetricaComparada[];
  requisitos: RequisitoComparado[];
  pasos_antes: string[];
  tareas_despues: { nombre: string; actor: string }[];
  fricciones: string[];
  cambios: string[];
  eliminaciones: string[];
  impacto: string[];
  autollenados: number;
  porcentaje_global: number | null;
  base_global: number;
  total_metricas: number;
  veredicto: "reduce" | "mixto" | "no_reduce" | "sin_medida";
  frase: string;
  huecos: Hueco[];
  /** El resumen de «Documentos del trámite», si alguien ya empezó a revisarlos. */
  documentos: ResumenDocumentos | null;
}

/** Documentos del trámite (`GET /api/v1/expedientes/{sid}/documentos`). */
export type Destino = "elimina" | "conserva" | "consulta" | "sistema";
export type DestinoOSin = Destino | "sin_destino";

export interface DocumentoTramite {
  id: string;
  nombre: string;
  cita_as_is: string;
  destino: DestinoOSin;
  campo: string;
  cita_to_be: string;
  motivo: string;
  motivo_de: "ia" | "persona" | "";
  confianza: "alta" | "media" | "baja" | "";
  veredicto: string;
  origen: "lector" | "agente";
  estado: "propuesto" | "aceptado" | "corregido";
}

export interface ResumenDocumentos {
  total: number;
  decididos: number;
  ya_no_se_piden: number;
  por_destino: Record<DestinoOSin, number>;
  agregados: string[];
  /** Archivos que el trámite rediseñado le pide al solicitante. */
  solicitados: number;
  completo: boolean;
  titular: string;
  /** «Cómo se simplificó el trámite»: los documentos de cada destino ya decidido. */
  simplificacion: { destino: Destino; frase: string; documentos: string[] }[];
}

export interface EstadoDocumentos {
  disponible: boolean;
  motivo: string;
  estado: "sin_analizar" | "analizando" | "lista" | "error";
  motivo_estado: string | null;
  pasos: { t: string; mensaje: string }[];
  origen: "lector" | "agente";
  documentos: DocumentoTramite[];
  resumen: ResumenDocumentos;
  puede_analizar: boolean;
  motivo_analizar: string | null;
  pruebas: boolean;
}
