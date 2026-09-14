import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { ErrorApi } from "@/lib/api";

/**
 * Envuelve una llamada a `/api/v1` con el estado que todo control necesita:
 * `guardando` mientras la peticion esta en vuelo y `error` con el `ErrorApi`
 * que haya devuelto la API.
 *
 * Existe porque cada control repetia (o se saltaba) el mismo try/catch:
 * `ControlVisibilidad` y `ControlCompuerta` lo tenian completo; `ControlTexto`,
 * `ControlActor` y `ControlCampoPadre` no tenian nada, asi que su boton seguia
 * activo durante la peticion y un doble clic mandaba dos resoluciones.
 *
 * El candado es un `ref` y no el estado `guardando` a proposito: dos clics en
 * el mismo tick leerian el `guardando` viejo, el `ref` se actualiza al vuelo.
 *
 * El toast de error vive aqui y no en cada control a proposito: es la unica
 * forma de que ningun control pueda olvidarse de avisar. Antes, un fallo de red
 * dejaba la pantalla exactamente igual que antes del clic.
 *
 * Un error que no sea `ErrorApi` es un bug del frontend, no una respuesta del
 * servidor: se deja escapar para que se vea en consola en vez de disfrazarlo
 * de fallo de la API.
 */
export function useAccion() {
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<ErrorApi | null>(null);
  const enVuelo = useRef(false);

  const ejecutar = useCallback(
    async <T>(accion: () => Promise<T>): Promise<T | undefined> => {
      if (enVuelo.current) return undefined;
      enVuelo.current = true;
      setError(null);
      setGuardando(true);
      try {
        return await accion();
      } catch (e) {
        if (e instanceof ErrorApi) {
          setError(e);
          toast.error(e.error);
          return undefined;
        }
        throw e;
      } finally {
        enVuelo.current = false;
        setGuardando(false);
      }
    },
    [],
  );

  return { guardando, error, ejecutar };
}
