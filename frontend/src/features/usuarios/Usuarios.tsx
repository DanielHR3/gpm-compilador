import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { aprobarUsuario, cambiarRol, desactivarUsuario, listarUsuarios } from "@/lib/api";
import type { UsuarioAdmin } from "@/lib/types";

/**
 * Administración de cuentas, solo para el superusuario (rol `admin`). Una
 * tarjeta por cuenta, agrupadas por estado (en la SPA no hay tablas). Las
 * pendientes van primero: aprobar es la tarea de este cuadro.
 */
const ESTADOS: { clave: UsuarioAdmin["estado"]; titulo: string; nota: string }[] = [
  { clave: "pendiente", titulo: "Pendientes de aprobación", nota: "Se registraron y esperan tu visto bueno." },
  { clave: "activo", titulo: "Activas", nota: "Pueden entrar al asistente." },
  { clave: "inactivo", titulo: "Desactivadas", nota: "No pueden entrar; la auditoría las sigue citando." },
];

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
      setError("No se pudo aplicar el cambio.");
    } finally {
      setOcupado(null);
    }
  };

  if (error && !lista) return <p role="alert" className="text-sm text-destructive">{error}</p>;
  if (!lista) return <p className="text-sm text-muted-foreground">Cargando…</p>;

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Cuentas</h1>
        <p className="text-sm text-muted-foreground">
          Quién puede entrar al asistente. Solo se registran correos institucionales; tú apruebas cada cuenta.
        </p>
      </header>
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
      {ESTADOS.map(({ clave, titulo, nota }) => {
        const grupo = lista.filter((u) => u.estado === clave);
        return (
          <section key={clave} aria-label={titulo} className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold">
              {titulo} <span className="text-sm font-normal text-muted-foreground">({grupo.length})</span>
            </h2>
            <p className="text-sm text-muted-foreground">{nota}</p>
            {grupo.length === 0 ? (
              <p className="text-sm text-muted-foreground">Ninguna.</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {grupo.map((u) => (
                  <li key={u.correo}>
                    <Card role="article" aria-label={u.correo} className="py-4">
                      <CardHeader className="gap-1">
                        <CardTitle className="text-base">{u.nombre}</CardTitle>
                        <CardDescription>
                          {u.correo} · {u.dependencia} · {u.rol === "admin" ? "superusuario" : "analista"}
                          {u.correo === yo ? " · tú" : ""}
                        </CardDescription>
                        <CardAction className="flex flex-wrap gap-2">
                          {u.estado === "pendiente" || u.estado === "inactivo" ? (
                            <Button size="sm" disabled={ocupado === u.correo}
                              onClick={() => void accion(u.correo, () => aprobarUsuario(u.correo))}>
                              {u.estado === "pendiente" ? "Aprobar" : "Reactivar"}
                            </Button>
                          ) : null}
                          {u.estado === "activo" && u.correo !== yo ? (
                            <>
                              <Button size="sm" variant="outline" disabled={ocupado === u.correo}
                                onClick={() => void accion(u.correo, () => cambiarRol(u.correo, u.rol === "admin" ? "analista" : "admin"))}>
                                {u.rol === "admin" ? "Quitar superusuario" : "Hacer superusuario"}
                              </Button>
                              <Button size="sm" variant="outline" disabled={ocupado === u.correo}
                                onClick={() => void accion(u.correo, () => desactivarUsuario(u.correo))}>
                                Desactivar
                              </Button>
                            </>
                          ) : null}
                        </CardAction>
                      </CardHeader>
                      <CardContent className="text-xs text-muted-foreground">
                        Estado: {u.estado}
                      </CardContent>
                    </Card>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </section>
  );
}
