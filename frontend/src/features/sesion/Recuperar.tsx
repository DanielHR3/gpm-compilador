import { KeyRound } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { recuperar, restablecer } from "@/lib/api";

import MarcoSesion from "./MarcoSesion";
import { Campo, DOMINIO } from "./Registro";

const MIN_CONTRASENA = 8;

/** «Olvidé mi contraseña»: pide el correo y el servidor manda la liga. */
export default function Recuperar() {
  const [correo, setCorreo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setOcupado(true);
    try {
      const r = await recuperar(correo.trim());
      setMensaje(r.mensaje);
    } catch {
      setError("No se pudo pedir la recuperación. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  };

  return (
    <MarcoSesion titulo="Recuperar contraseña" etiqueta="Recuperar contraseña"
      descripcion="Te mandamos una liga a tu correo institucional. Caduca en una hora y sirve una sola vez.">
      {mensaje ? (
        <div className="flex flex-col gap-4 text-sm">
          <p role="status">{mensaje}</p>
          <a href="/" className="text-primary underline underline-offset-2">Volver a la entrada</a>
        </div>
      ) : (
        <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
          <Campo id="correo" etiqueta="Correo institucional" type="email" autoComplete="username"
            placeholder={`nombre.apellido@${DOMINIO}`} value={correo} onChange={setCorreo} />
          {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" disabled={ocupado || !correo.includes("@")} className="mt-1">
            <KeyRound aria-hidden data-icon="inline-start" />
            {ocupado ? "Enviando…" : "Enviar liga"}
          </Button>
          <p className="text-xs text-muted-foreground">
            <a href="/" className="text-primary underline underline-offset-2">Volver a la entrada</a>
          </p>
        </form>
      )}
    </MarcoSesion>
  );
}

/** La liga del correo: `/restablecer?token=…`. */
export function Restablecer({ token }: { token: string }) {
  const [contrasena, setContrasena] = useState("");
  const [confirma, setConfirma] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [hecho, setHecho] = useState(false);

  const listo = contrasena.length >= MIN_CONTRASENA && contrasena === confirma;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setOcupado(true);
    try {
      await restablecer(token, contrasena);
      setHecho(true);
    } catch {
      setError("La liga no es válida, ya se usó o caducó. Pide otra desde «Recuperar contraseña».");
    } finally {
      setOcupado(false);
    }
  };

  return (
    <MarcoSesion titulo="Nueva contraseña" etiqueta="Nueva contraseña"
      descripcion={hecho ? "Listo. Ya puedes entrar con la nueva contraseña." : "Escribe la contraseña nueva dos veces."}>
      {hecho ? (
        <a href="/" className="text-sm text-primary underline underline-offset-2">Ir a la entrada</a>
      ) : (
        <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
          <Campo id="contrasena" etiqueta={`Contraseña nueva (mínimo ${MIN_CONTRASENA} caracteres)`} type="password"
            autoComplete="new-password" value={contrasena} onChange={setContrasena} />
          <Campo id="confirma" etiqueta="Repite la contraseña" type="password" autoComplete="new-password"
            value={confirma} onChange={setConfirma}
            aviso={confirma && confirma !== contrasena ? "Las contraseñas no coinciden." : null} />
          {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" disabled={ocupado || !listo} className="mt-1">
            {ocupado ? "Guardando…" : "Guardar contraseña"}
          </Button>
        </form>
      )}
    </MarcoSesion>
  );
}
