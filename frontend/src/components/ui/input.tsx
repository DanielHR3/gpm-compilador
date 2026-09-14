import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"
import { cn } from "cn"

/**
 * Campo de texto del Compilador.
 *
 * Trae el corrector de ortografia encendido por defecto: aqui se escribe prosa
 * en español —el nombre del tramite, el tiempo de respuesta, el valor de una
 * condicion— y ese texto acaba impreso en un tramite publicado. La pagina ya
 * declara lang="es", asi que el diccionario es el del sistema. Un campo con
 * datos tecnicos (CURP, RFC, claves) puede apagarlo con spellCheck={false}.
 */
function Input({
  className,
  type,
  spellCheck = true,
  ...props
}: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      spellCheck={spellCheck}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Input }
