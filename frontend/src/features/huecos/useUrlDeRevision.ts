import { useEffect } from "react";

/**
 * Le da al expediente abierto una direccion propia: `/revisar/:sid`.
 *
 * `App` ya sabia LEER esa ruta —es herencia del flujo viejo, cuando el servidor
 * redirigia ahi tras extraer (`app.py`, `RedirectResponse("/revisar/{sid}")`)—
 * pero desde que la carga la hace la SPA nadie la escribia: el expediente vivia
 * solo en memoria de React y la barra de direcciones se quedaba en `/`.
 *
 * Eso rompia cualquier salida y vuelta. El simulador, la aprobacion y el
 * manifiesto son paginas del servidor, no vistas de la SPA: al abrirlas se
 * pierde el arbol de React entero. «Salir del Simulador» hace `history.back()`,
 * volvia a `/`, y la SPA arrancaba de cero en la carga de insumos -- con el
 * expediente intacto en disco, pero sin nada en la URL que lo dijera.
 *
 * Se empuja una sola vez por expediente: cada hueco resuelto reescribe el
 * estado, y empujar en cada uno llenaria el historial de copias identicas.
 */
export function useUrlDeRevision(sid: string | null): void {
  useEffect(() => {
    if (!sid) return;
    const ruta = `/revisar/${sid}`;
    if (window.location.pathname === ruta) return;
    window.history.pushState({ gpmcRevision: sid }, "", ruta);
  }, [sid]);
}
