import { FileWarning } from "lucide-react";

import { ErrorApi } from "@/lib/api";

/** Tope de subida por archivo. Copia estatica: el 413 puede no traer `limite_mb`. */
export const LIMITE_POR_ARCHIVO = "10 MB";

/**
 * Un fallo de red no es un `ErrorApi` (el servidor nunca contesto), pero la
 * persona necesita verlo igual. Se envuelve con `status 0` para pintarlo
 * con el mismo bloque.
 */
export function comoErrorDeCarga(e: unknown): ErrorApi {
  if (e instanceof ErrorApi) return e;
  return new ErrorApi(
    0,
    "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.",
  );
}

/**
 * El bloque de error de las dos cargas (carpeta y AS-IS): titulo, y la lista
 * de archivos con su motivo cuando el servidor los nombra.
 *
 * `archivos` lo manda tanto el 413 (nombres a secas) como el 422 de lectura
 * ("NOMBRE: motivo"). Antes solo se pintaba en la rama del 413, asi que un
 * PDF escaneado daba "no se pudo leer el documento" sobre cuatro zonas de
 * carga sin decir cual era -- y el backend ya sabia el nombre Y el motivo.
 */
export default function ErrorDeCarga({ error }: { error: ErrorApi }) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
    >
      {error.status === 413 ? (
        <>
          <p className="font-semibold">Archivo demasiado grande</p>
          <p>El límite por archivo es {LIMITE_POR_ARCHIVO}. Reduce o divide estos archivos:</p>
        </>
      ) : (
        <p className="font-semibold">{error.message}</p>
      )}
      {error.archivos?.length ? (
        <div className="flex flex-col gap-1.5">
          {error.archivos.map((entrada) => {
            const corte = entrada.indexOf(": ");
            const nombre = corte === -1 ? entrada : entrada.slice(0, corte);
            const motivo = corte === -1 ? null : entrada.slice(corte + 2);
            return (
              <p
                key={entrada}
                className="flex items-start gap-2 rounded-md border border-destructive/30 bg-card/60 px-3 py-1.5 break-all"
              >
                <FileWarning aria-hidden className="mt-0.5 size-4 shrink-0" />
                <span>
                  <span className="font-medium">{nombre}</span>
                  {motivo ? <span className="block text-xs opacity-90">{motivo}</span> : null}
                </span>
              </p>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
