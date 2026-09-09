import { Button } from "@/components/ui/button";

/**
 * Andamiaje SP1 Task 7: pantalla mínima que ejercita la cadena completa
 * React + shadcn/ui + Tailwind v4 + tokens de `hidalgo-design-token-system`.
 * El contenido real de la SPA llega en tareas posteriores.
 */
export default function App() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background p-8 text-foreground">
      <h1 className="text-2xl font-semibold">Compilador GPM</h1>
      <Button>Compilador GPM</Button>
    </main>
  );
}
