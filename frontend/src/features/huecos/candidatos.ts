import type { CampoManifiesto } from "@/lib/types";

/**
 * Que campos se pueden usar en la condicion de visibilidad de OTRO campo.
 *
 * Son las dos reglas que `verificar.py` ya aplica a las propuestas del
 * generador de IA. Hasta ahora la persona era la unica que podia saltarselas:
 * el desplegable ofrecia los 41 campos del expediente, incluidos los que se
 * capturan mas adelante, y el servidor los aceptaba. El resultado es una regla
 * que la plataforma no puede evaluar nunca — exactamente lo que se le pidio a
 * Simplificacion que dejara de escribir en el Diccionario.
 */
export type Grupo = "sugerido" | "usable" | "inservible";

export type Candidato = {
  campo: CampoManifiesto;
  grupo: Grupo;
  /** Por que no se puede usar. Solo en los inservibles. */
  motivo?: string;
};

/** El campo cuya visibilidad se esta definiendo. `null` en la compuerta. */
export type Objetivo = { interno: string; pantalla: number };

const ORDEN: Grupo[] = ["sugerido", "usable", "inservible"];

/** Sin acentos, minusculas y espacios colapsados: «ESTATUS DEL TRÁMITE» y
 *  «estatus del tramite» tienen que casar. */
function llano(t: string): string {
  return t
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function clasificarCandidatos(
  campos: CampoManifiesto[],
  objetivo: Objetivo | null,
  frase: string,
): Candidato[] {
  const enLaFrase = llano(frase);
  const clasificados = campos.map((campo): Candidato => {
    if (objetivo) {
      if (campo.nombre === objetivo.interno) {
        return { campo, grupo: "inservible", motivo: "es este mismo campo" };
      }
      if (campo.pantalla > objetivo.pantalla) {
        return { campo, grupo: "inservible", motivo: "se captura después" };
      }
    }
    // La sugerencia va DESPUES de descartar: que el Diccionario nombre un campo
    // imposible no lo vuelve posible, y proponerlo seria contradecir la regla.
    const sugerido =
      campo.etiqueta !== "" && enLaFrase.includes(llano(campo.etiqueta));
    return { campo, grupo: sugerido ? "sugerido" : "usable" };
  });
  return clasificados.sort(
    (a, b) => ORDEN.indexOf(a.grupo) - ORDEN.indexOf(b.grupo),
  );
}
