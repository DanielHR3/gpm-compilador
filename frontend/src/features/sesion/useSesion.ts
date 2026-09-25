import { useCallback, useEffect, useState } from "react";

import { alPerderSesion, ErrorApi, leerSesion, salir as salirApi } from "@/lib/api";
import type { Usuario } from "@/lib/types";

/**
 * Estado de la sesión del asistente.
 *
 * - `cargando`: todavía no se preguntó al servidor.
 * - `sin_usuarios`: el servidor no exige sesión (`gpmc servir --sin-usuarios`,
 *   la Mac de pruebas): se entra directo, como siempre.
 * - `cerrada`: hace falta entrar.
 * - `abierta`: hay usuario.
 *
 * El token nunca lo guarda la SPA: viaja en la cookie HttpOnly que puso el
 * servidor al entrar. Un 401 en cualquier llamada cierra la sesión aquí, y la
 * pantalla vuelve a la entrada sin perder la liga.
 */
export type EstadoSesion = "cargando" | "sin_usuarios" | "cerrada" | "abierta";

export function useSesion() {
  const [estado, setEstado] = useState<EstadoSesion>("cargando");
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  useEffect(() => {
    let vivo = true;
    leerSesion()
      .then((r) => {
        if (!vivo) return;
        setUsuario(r.usuario);
        setEstado(r.usuario ? "abierta" : "cerrada");
      })
      .catch((e: unknown) => {
        if (!vivo) return;
        // 404 (o 405): la ruta no existe porque el servidor corre sin usuarios.
        const st = e instanceof ErrorApi ? e.status : (e as { status?: number })?.status;
        if (st === 404 || st === 405) setEstado("sin_usuarios");
        else setEstado("cerrada");
      });
    return alPerderSesion(() => {
      if (!vivo) return;
      setUsuario(null);
      setEstado((s) => (s === "sin_usuarios" ? s : "cerrada"));
    }, () => { vivo = false; });
  }, []);

  const entrar = useCallback((u: Usuario) => {
    setUsuario(u);
    setEstado("abierta");
  }, []);

  const salir = useCallback(async () => {
    try {
      await salirApi();
    } finally {
      setUsuario(null);
      setEstado("cerrada");
    }
  }, []);

  return { estado, usuario, entrar, salir };
}
