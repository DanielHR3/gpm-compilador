import { LogIn } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import CampoContrasena from "@/components/CampoContrasena";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { entrar, ErrorApi } from "@/lib/api";
import type { Usuario } from "@/lib/types";

import MarcoSesion from "./MarcoSesion";

/**
 * La entrada al asistente cuando el servidor exige sesión (spec 2026-09-25).
 * Solo correos institucionales; las cuentas nuevas las aprueba la DGT.
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
      // El unico 401 con mensaje propio es «cuenta pendiente»; lo demas es
      // «incorrectos», sin decir cual de los dos datos fallo.
      if (err instanceof ErrorApi && err.status === 401)
        setError(/pendiente/i.test(err.message) ? err.message : "Correo o contraseña incorrectos.");
      else setError("No se pudo entrar. Revisa la conexión e inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  };

  return (
    <MarcoSesion titulo="Entrar" etiqueta="Entrar al Compilador GPM"
      descripcion="Con tu correo institucional. Uso interno de la DGT y la DSA.">
      <form onSubmit={enviar} className="flex flex-col gap-5" noValidate>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="correo" className="text-sm font-medium">Correo institucional</label>
          <Input id="correo" name="correo" type="email" autoComplete="username" spellCheck={false}
            placeholder="nombre.apellido@hidalgo.gob.mx" value={correo}
            onChange={(e) => setCorreo(e.target.value)} required autoFocus className="h-10" />
        </div>
        <CampoContrasena id="contrasena" etiqueta="Contraseña" value={contrasena} onChange={setContrasena} />
        {error ? (
          <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        ) : null}
        <Button type="submit" size="lg" disabled={ocupado || !correo || !contrasena} className="h-11 w-full text-base">
          <LogIn aria-hidden data-icon="inline-start" />
          {ocupado ? "Entrando…" : "Entrar"}
        </Button>
        <div className="flex items-center justify-between text-sm">
          <a href="/registro" className="font-medium text-primary underline-offset-4 hover:underline">Crear cuenta</a>
          <a href="/recuperar" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">Olvidé mi contraseña</a>
        </div>
        <p className="border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground">
          Solo correos institucionales. Una cuenta nueva la aprueba la Dirección General de Tecnologías antes de poder entrar.
        </p>
      </form>
    </MarcoSesion>
  );
}
