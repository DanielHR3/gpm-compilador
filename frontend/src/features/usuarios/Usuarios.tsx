import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { aprobarUsuario, cambiarRol, desactivarUsuario, listarUsuarios } from "@/lib/api";
import type { UsuarioAdmin } from "@/lib/types";
import { cn } from "cn";

/**
 * Administración de cuentas, solo para el superusuario (rol `admin`).
 *
 * La tarea de este cuadro es aprobar: las pendientes van primero y con la
 * acción en guinda; el resto de acciones son secundarias. Cada cuenta es una
 * fila-tarjeta con iniciales, nombre, correo y sus dos etiquetas (dependencia
 * y rol); el estado lo dice la sección, no una etiqueta más. Tarjetas en
 * rejilla, como todo en la SPA: nunca una lista ni una tabla.
 */
const ESTADOS: { clave: UsuarioAdmin["estado"]; titulo: string; nota: string; vacio: string }[] = [
  { clave: "pendiente", titulo: "Pendientes de aprobación", nota: "Se registraron y esperan tu visto bueno para poder entrar.",
    vacio: "No hay solicitudes. Quien se registre desde la entrada aparecerá aquí." },
  { clave: "activo", titulo: "Con acceso", nota: "Pueden entrar al asistente.", vacio: "Ninguna cuenta activa." },
  { clave: "inactivo", titulo: "Desactivadas", nota: "No pueden entrar. La auditoría las sigue citando.", vacio: "Ninguna." },
];

function iniciales(nombre: string): string {
  const p = nombre.trim().split(/\s+/).filter(Boolean);
  return ((p[0]?.[0] ?? "") + (p[1]?.[0] ?? "")).toUpperCase() || "?";
}

function Etiqueta({ children, tono = "neutra" }: { children: string; tono?: "neutra" | "guinda" | "arena" }) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
      tono === "guinda" && "bg-primary/10 text-primary",
      tono === "arena" && "bg-secondary/20 text-[color-mix(in_oklch,var(--secondary),black_35%)]",
      tono === "neutra" && "bg-muted text-muted-foreground",
    )}>
      {children}
    </span>
  );
}

export default function Usuarios({ yo }: { yo: string }) {
  const [lista, setLista] = useState<UsuarioAdmin[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const cargar = useCallback(() => {
    listarUsuarios().then((r) => setLista(r.usuarios)).catch(() => setError("No se pudo leer la lista de cuentas."));
  }, []);
  useEffect(cargar, [cargar]);

  const accion = async (correo: string, f: () => Promise<unknown>) => {
    setOcupado(correo);
    setError(null);
    try {
      await f();
      cargar();
    } catch {
      setError("No se pudo aplicar el cambio. Inténtalo de nuevo.");
    } finally {
      setOcupado(null);
    }
  };

  if (error && !lista) return <p role="alert" className="text-sm text-destructive">{error}</p>;
  if (!lista) return <p className="text-sm text-muted-foreground">Cargando…</p>;

  const pendientes = lista.filter((u) => u.estado === "pendiente").length;

  return (
    <section className="flex max-w-4xl flex-col gap-8 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Cuentas</h1>
        <p className="text-sm text-muted-foreground">
          Quién puede entrar al asistente. Solo se registran correos institucionales y cada cuenta nueva la apruebas tú.
        </p>
      </header>
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}

      {ESTADOS.map(({ clave, titulo, nota, vacio }) => {
        const grupo = lista.filter((u) => u.estado === clave);
        const esPendientes = clave === "pendiente";
        return (
          <section key={clave} aria-label={titulo}
            className={cn("flex flex-col gap-3", esPendientes && pendientes > 0 && "rounded-lg border-l-4 border-secondary bg-secondary/5 p-4")}>
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="text-lg font-semibold">{titulo}</h2>
              <span className="text-sm text-muted-foreground">{grupo.length === 1 ? "1 cuenta" : `${grupo.length} cuentas`}</span>
            </div>
            <p className="-mt-2 text-sm text-muted-foreground">{nota}</p>
            {grupo.length === 0 ? (
              <p className="rounded-md border border-dashed border-border px-4 py-5 text-center text-sm text-muted-foreground">{vacio}</p>
            ) : (
              <ul className="grid gap-4 md:grid-cols-2">
                {grupo.map((u) => {
                  const soyYo = u.correo === yo;
                  return (
                    <li key={u.correo}>
                      <Card role="article" aria-label={u.correo} className="h-full py-4">
                        <CardHeader className="gap-1">
                          <div className="flex items-start gap-3">
                            <span aria-hidden className={cn(
                              "flex size-11 shrink-0 items-center justify-center rounded-full font-heading text-sm font-bold",
                              u.estado === "inactivo" ? "bg-muted text-muted-foreground" : "bg-primary/10 text-primary",
                            )}>
                              {iniciales(u.nombre)}
                            </span>
                            <div className="flex min-w-0 flex-col gap-0.5">
                              <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                                <span>{u.nombre}</span>
                                {soyYo ? <Etiqueta tono="arena">tú</Etiqueta> : null}
                              </CardTitle>
                              <CardDescription className="truncate">{u.correo}</CardDescription>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="flex flex-wrap gap-1.5">
                          <Etiqueta>{u.dependencia}</Etiqueta>
                          <Etiqueta tono={u.rol === "admin" ? "guinda" : "neutra"}>{u.rol === "admin" ? "superusuario" : "analista"}</Etiqueta>
                        </CardContent>
                        {u.estado === "pendiente" || u.estado === "inactivo" || !soyYo ? (
                          <CardFooter className="flex flex-wrap gap-2">
                            {u.estado === "pendiente" ? (
                              <Button size="sm" disabled={ocupado === u.correo}
                                onClick={() => void accion(u.correo, () => aprobarUsuario(u.correo))}>
                                Aprobar
                              </Button>
                            ) : null}
                            {u.estado === "inactivo" ? (
                              <Button size="sm" variant="outline" disabled={ocupado === u.correo}
                                onClick={() => void accion(u.correo, () => aprobarUsuario(u.correo))}>
                                Reactivar
                              </Button>
                            ) : null}
                            {u.estado === "activo" && !soyYo ? (
                              <>
                                <Button size="sm" variant="outline" disabled={ocupado === u.correo}
                                  onClick={() => void accion(u.correo, () => cambiarRol(u.correo, u.rol === "admin" ? "analista" : "admin"))}>
                                  {u.rol === "admin" ? "Quitar superusuario" : "Hacer superusuario"}
                                </Button>
                                <Button size="sm" variant="ghost" disabled={ocupado === u.correo}
                                  className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                  onClick={() => void accion(u.correo, () => desactivarUsuario(u.correo))}>
                                  Desactivar
                                </Button>
                              </>
                            ) : null}
                          </CardFooter>
                        ) : null}
                      </Card>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}
    </section>
  );
}
