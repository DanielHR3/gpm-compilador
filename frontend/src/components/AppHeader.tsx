/**
 * Barra superior de la columna de contenido.
 *
 * En el armazón de la casa (`checador-web`, `GeoApertura`) la identidad vive en
 * la barra lateral guinda, y la superior es blanca con el título de la pantalla
 * en guinda: dice DÓNDE estás, no QUÉ producto es. Por eso ya no repite
 * "Compilador GPM", que ahora encabeza la barra lateral.
 */
export default function AppHeader({ titulo }: { titulo: string }) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-card px-6">
      <span className="font-heading text-lg font-bold tracking-tight text-primary">
        {titulo}
      </span>
      <span className="hidden text-xs text-muted-foreground sm:block">
        Gobierno del Estado de Hidalgo
      </span>
    </header>
  );
}
