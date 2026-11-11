/**
 * El trámite de Simplifica con el que se va a empezar un expediente («Empezar expediente» en la
 * campanita). Vive en `sessionStorage`: dura lo que la pestaña y solo guarda el ID de RUTS y el
 * nombre del trámite, que no son datos personales. La carga lo manda como `ruts_id` y lo borra.
 */
const CLAVE = "gpmc.tramite-ligado";

export interface TramiteLigado {
  ruts_id: string;
  nombre: string;
}

export function leerTramiteLigado(): TramiteLigado | null {
  try {
    const d = JSON.parse(sessionStorage.getItem(CLAVE) ?? "null") as Partial<TramiteLigado> | null;
    return d && typeof d.ruts_id === "string" && /^[A-Za-z0-9]{1,20}$/.test(d.ruts_id)
      ? { ruts_id: d.ruts_id, nombre: typeof d.nombre === "string" ? d.nombre : "" }
      : null;
  } catch {
    return null;
  }
}

export function guardarTramiteLigado(t: TramiteLigado): void {
  try {
    sessionStorage.setItem(CLAVE, JSON.stringify({ ruts_id: t.ruts_id, nombre: t.nombre }));
  } catch {
    // Sin almacenamiento (modo privado estricto) el expediente simplemente no nace ligado.
  }
}

export function quitarTramiteLigado(): void {
  try {
    sessionStorage.removeItem(CLAVE);
  } catch {
    // nada que quitar
  }
}
