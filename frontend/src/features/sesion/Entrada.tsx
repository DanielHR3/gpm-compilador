import { LogIn } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import PieInstitucional from "@/components/PieInstitucional";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { entrar, ErrorApi } from "@/lib/api";
import type { Usuario } from "@/lib/types";

/**
 * La entrada al asistente cuando el servidor exige sesión (spec 2026-09-25).
 *
 * Mismo armazón que el resto de la casa: superficie `background`, tarjeta
 * `card`, guinda solo en la acción principal y en la franja de identidad.
 * Sin registro ni «olvidé mi contraseña»: las altas las hace la DGT por
 * terminal (`gpmc usuario alta`), y así lo dice la pantalla.
 */
export default function Entrada({ onEntrar }: { onEntrar: (u: Usuario) => void }) {
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setOcupado(true);
    try {
      const r = await entrar(correo.trim(), contrasena);
      onEntrar(r.usuario);
    } catch (err: unknown) {
      if (err instanceof ErrorApi && err.status === 401) setError("Correo o contraseña incorrectos.");
      else setError("No se pudo entrar. Revisa la conexión e inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <Card role="region" aria-label="Entrar al Compilador GPM" className="w-full max-w-md py-6">
          <CardHeader className="items-center text-center">
            <img
              src="/logo-hidalgo-coemere.svg"
              alt="Gobierno del Estado de Hidalgo · Comisión Estatal de Mejora Regulatoria"
              className="mx-auto mb-2 h-10 w-auto"
            />
            <CardTitle className="font-heading text-xl text-primary">
              <h1>Compilador GPM</h1>
            </CardTitle>
            <CardDescription>
              Entra con tu correo institucional. Uso interno de la DGT y la DSA.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="correo" className="text-sm font-medium">
                  Correo institucional
                </label>
                <Input
                  id="correo"
                  name="correo"
                  type="email"
                  autoComplete="username"
                  spellCheck={false}
                  placeholder="nombre.apellido@hidalgo.gob.mx"
                  value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="contrasena" className="text-sm font-medium">
                  Contraseña
                </label>
                <Input
                  id="contrasena"
                  name="contrasena"
                  type="password"
                  autoComplete="current-password"
                  spellCheck={false}
                  value={contrasena}
                  onChange={(e) => setContrasena(e.target.value)}
                  required
                />
              </div>
              {error ? (
                <p role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              ) : null}
              <Button type="submit" disabled={ocupado || !correo || !contrasena} className="mt-1">
                <LogIn aria-hidden data-icon="inline-start" />
                {ocupado ? "Entrando…" : "Entrar"}
              </Button>
              <p className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
                <a href="/registro" className="text-primary underline underline-offset-2">Crear cuenta</a>
                <a href="/recuperar" className="text-primary underline underline-offset-2">Olvidé mi contraseña</a>
              </p>
              <p className="text-xs text-muted-foreground">
                Solo correos institucionales. Una cuenta nueva la aprueba la Dirección General de Tecnologías.
              </p>
            </form>
          </CardContent>
        </Card>
      </main>
      <PieInstitucional />
    </div>
  );
}
