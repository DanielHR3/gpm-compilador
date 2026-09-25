import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Usuario } from "@/lib/types";

/**
 * Barra superior de la columna de contenido.
 *
 * En el armazón de la casa (`checador-web`, `GeoApertura`) la identidad vive en
 * la barra lateral guinda, y la superior es blanca con el título de la pantalla
 * en guinda: dice DÓNDE estás, no QUÉ producto es.
 *
 * A la derecha, quién está dentro: iniciales en un círculo guinda tenue, nombre
 * y dependencia, y «Salir» como acción discreta. El logo institucional cierra
 * la barra, separado por una línea: va aquí y no en la lateral porque sobre
 * superficie clara puede ir en sus colores.
 */
function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  return ((partes[0]?.[0] ?? "") + (partes[1]?.[0] ?? "")).toUpperCase() || "?";
}

export default function AppHeader({
  titulo,
  usuario,
  onSalir,
}: {
  titulo: string;
  /** Quien esta dentro; null cuando el servidor corre sin usuarios. */
  usuario?: Usuario | null;
  onSalir?: () => void;
}) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-card px-6">
      <span className="font-heading text-lg font-bold tracking-tight text-primary">{titulo}</span>
      <div className="flex items-center gap-5">
        {usuario ? (
          <div className="flex items-center gap-3">
            <span aria-hidden className="flex size-9 items-center justify-center rounded-full bg-primary/10 font-heading text-sm font-bold text-primary">
              {iniciales(usuario.nombre)}
            </span>
            <span className="hidden flex-col leading-tight sm:flex" aria-label="Sesión">
              <span className="text-sm font-semibold text-foreground">{usuario.nombre}</span>
              <span className="text-xs text-muted-foreground">
                {usuario.dependencia}{usuario.rol === "admin" ? " · superusuario" : ""}
              </span>
            </span>
            <Button type="button" variant="ghost" size="sm" onClick={onSalir} className="text-muted-foreground hover:text-foreground">
              <LogOut aria-hidden data-icon="inline-start" />
              Salir
            </Button>
          </div>
        ) : null}
        <img
          src="/logo-hidalgo-coemere.svg"
          alt="Gobierno del Estado de Hidalgo · Comisión Estatal de Mejora Regulatoria"
          className={"hidden h-8 w-auto sm:block" + (usuario ? " border-l border-border pl-5" : "")}
        />
      </div>
    </header>
  );
}
