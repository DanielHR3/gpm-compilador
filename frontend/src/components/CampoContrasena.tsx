import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";

/**
 * Campo de contraseña con el ojo para verla. Escribir una contraseña a ciegas
 * en un teléfono o con una mala es la primera causa de «no puedo entrar»; el
 * botón alterna el tipo del campo y anuncia lo que hace.
 */
export default function CampoContrasena({
  id, etiqueta, value, onChange, aviso, autoComplete = "current-password",
}: {
  id: string; etiqueta: string; value: string; onChange: (v: string) => void;
  aviso?: string | null; autoComplete?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">{etiqueta}</label>
      <div className="relative">
        <Input id={id} name={id} type={visible ? "text" : "password"} autoComplete={autoComplete}
          spellCheck={false} value={value} onChange={(e) => onChange(e.target.value)}
          aria-invalid={aviso ? true : undefined} required className="h-10 pr-10" />
        <button type="button" onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"} aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 rounded-r-lg">
          {visible ? <EyeOff aria-hidden className="size-4" /> : <Eye aria-hidden className="size-4" />}
        </button>
      </div>
      {aviso ? <p className="text-xs text-destructive">{aviso}</p> : null}
    </div>
  );
}
