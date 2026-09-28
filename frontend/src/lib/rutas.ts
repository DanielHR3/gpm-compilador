/**
 * Que pantalla toca y que migas de pan lleva, en funciones puras. `App` sigue
 * decidiendo por `pathname` (sin enrutador de terceros: cinco pantallas no lo
 * justifican y las ligas `/revisar/{sid}` que ya circulan siguen vivas).
 */
export type Camino = "carpeta" | "as_is";
export type Ruta =
  | { tipo: "inicio" }
  | { tipo: "expediente" }
  | { tipo: "desde_as_is" }
  | { tipo: "revisar"; sid: string }
  | { tipo: "comparativa"; sid: string }
  | { tipo: "documentos"; sid: string }
  | { tipo: "catalogos" }
  | { tipo: "historial" }
  | { tipo: "tablero" }
  | { tipo: "registro" }
  | { tipo: "recuperar" }
  | { tipo: "restablecer"; token: string }
  | { tipo: "usuarios" };

const RE_REVISAR = /^\/revisar\/([0-9a-f]{16})$/;
const RE_COMPARATIVA = /^\/revisar\/([0-9a-f]{16})\/comparativa$/;
const RE_DOCUMENTOS = /^\/revisar\/([0-9a-f]{16})\/documentos$/;

export function leerRuta(pathname: string, search = ""): Ruta {
  const d = RE_DOCUMENTOS.exec(pathname);
  if (d) return { tipo: "documentos", sid: d[1] };
  const c = RE_COMPARATIVA.exec(pathname);
  if (c) return { tipo: "comparativa", sid: c[1] };
  const m = RE_REVISAR.exec(pathname);
  if (m) return { tipo: "revisar", sid: m[1] };
  if (pathname === "/restablecer") {
    // La liga del correo: el token viaja en la consulta.
    return { tipo: "restablecer", token: new URLSearchParams(search).get("token") ?? "" };
  }
  switch (pathname) {
    case "/expediente":
      return { tipo: "expediente" };
    case "/desde-as-is":
      return { tipo: "desde_as_is" };
    case "/catalogos":
      return { tipo: "catalogos" };
    case "/historial":
      return { tipo: "historial" };
    case "/tablero":
      return { tipo: "tablero" };
    case "/registro":
      return { tipo: "registro" };
    case "/recuperar":
      return { tipo: "recuperar" };
    case "/usuarios":
      return { tipo: "usuarios" };
    default:
      return { tipo: "inicio" };
  }
}

export type Pantalla = "inicio" | "carga" | "diccionario" | "tobe" | "revision";
export type Tramo = { etiqueta: string; href?: string };

const NOMBRE_CAMINO: Record<Camino, string> = {
  carpeta: "Expediente completo",
  as_is: "Solo AS-IS",
};

/**
 * Maximo tres tramos y solo «Inicio» enlaza: volver a «Expediente completo»
 * desde la revision abriria una carga nueva y la sesion se perderia de vista.
 */
export function migas(pantalla: Pantalla, camino: Camino | null): Tramo[] {
  if (pantalla === "inicio") return [{ etiqueta: "Inicio" }];
  const inicio: Tramo = { etiqueta: "Inicio", href: "/" };
  const tramoCamino: Tramo[] = camino ? [{ etiqueta: NOMBRE_CAMINO[camino] }] : [];
  if (pantalla === "carga") return [inicio, ...tramoCamino];
  if (pantalla === "diccionario")
    return [inicio, { etiqueta: NOMBRE_CAMINO.as_is }, { etiqueta: "Diccionario (1 de 2)" }];
  if (pantalla === "tobe")
    return [inicio, { etiqueta: NOMBRE_CAMINO.as_is }, { etiqueta: "TO-BE (2 de 2)" }];
  return [inicio, ...tramoCamino, { etiqueta: "Revisión" }];
}
