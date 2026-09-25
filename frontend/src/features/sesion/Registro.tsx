import { UserPlus } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import CampoContrasena from "@/components/CampoContrasena";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErrorApi, registrar } from "@/lib/api";

import MarcoSesion from "./MarcoSesion";

export const DOMINIO = "hidalgo.gob.mx";
const MIN_CONTRASENA = 8;

/**
 * Hoja de registro. Solo correos institucionales; la cuenta queda pendiente
 * hasta que el superusuario la apruebe (decisión del 2026-09-25), y la
 * pantalla lo dice antes de que la persona intente entrar.
 */
export default function Registro() {
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [dependencia, setDependencia] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [confirma, setConfirma] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [hecho, setHecho] = useState<string | null>(null);

  const institucional = correo.trim().toLowerCase().endsWith(`@${DOMINIO}`) && !correo.trim().startsWith("@");
  const listo = institucional && nombre.trim() && dependencia.trim() && contrasena.length >= MIN_CONTRASENA && contrasena === confirma;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setOcupado(true);
    try {
      const r = await registrar({ correo: correo.trim(), nombre: nombre.trim(), dependencia: dependencia.trim(), contrasena });
      setHecho(r.correo);
    } catch (err: unknown) {
      setError(err instanceof ErrorApi && err.status === 422 ? err.message : "No se pudo registrar. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  };

  if (hecho) {
    return (
      <MarcoSesion titulo="Registro recibido" etiqueta="Registro recibido"
        descripcion="Tu cuenta quedó pendiente de aprobación.">
        <div className="flex flex-col gap-4 text-sm">
          <p role="status">
            El superusuario de la DGT revisará la solicitud de <strong>{hecho}</strong>. Cuando la apruebe
            podrás entrar con tu contraseña. No recibirás correo: pregunta a tu enlace de la DGT si tarda.
          </p>
          <a href="/" className="text-primary underline underline-offset-2">Volver a la entrada</a>
        </div>
      </MarcoSesion>
    );
  }

  return (
    <MarcoSesion titulo="Crear cuenta" etiqueta="Crear cuenta"
      descripcion={`Solo con correo @${DOMINIO}. La cuenta se activa cuando la DGT la aprueba.`}>
      <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
        <Campo id="correo" etiqueta="Correo institucional" type="email" autoComplete="username"
          placeholder={`nombre.apellido@${DOMINIO}`} value={correo} onChange={setCorreo}
          aviso={correo && !institucional ? `Debe terminar en @${DOMINIO}.` : null} />
        <Campo id="nombre" etiqueta="Nombre completo" autoComplete="name" value={nombre} onChange={setNombre} />
        <Campo id="dependencia" etiqueta="Dependencia" placeholder="DGT, DSA, SEMARNATH…" value={dependencia} onChange={setDependencia} />
        <CampoContrasena id="contrasena" etiqueta={`Contraseña (mínimo ${MIN_CONTRASENA} caracteres)`}
          autoComplete="new-password" value={contrasena} onChange={setContrasena} />
        <CampoContrasena id="confirma" etiqueta="Repite la contraseña" autoComplete="new-password"
          value={confirma} onChange={setConfirma}
          aviso={confirma && confirma !== contrasena ? "Las contraseñas no coinciden." : null} />
        {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" disabled={ocupado || !listo} className="mt-1">
          <UserPlus aria-hidden data-icon="inline-start" />
          {ocupado ? "Enviando…" : "Solicitar cuenta"}
        </Button>
        <p className="text-xs text-muted-foreground">
          ¿Ya tienes cuenta? <a href="/" className="text-primary underline underline-offset-2">Entrar</a>
        </p>
      </form>
    </MarcoSesion>
  );
}

export function Campo({
  id, etiqueta, value, onChange, aviso, type = "text", ...resto
}: {
  id: string; etiqueta: string; value: string; onChange: (v: string) => void; aviso?: string | null;
  type?: string; autoComplete?: string; placeholder?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">{etiqueta}</label>
      <Input id={id} name={id} type={type} spellCheck={false} value={value}
        onChange={(e) => onChange(e.target.value)} aria-invalid={aviso ? true : undefined} required className="h-10" {...resto} />
      {aviso ? <p className="text-xs text-destructive">{aviso}</p> : null}
    </div>
  );
}
