/**
 * Barra superior de la columna de contenido.
 *
 * En el armazón de la casa (`checador-web`, `GeoApertura`) la identidad vive en
 * la barra lateral guinda, y la superior es blanca con el título de la pantalla
 * en guinda: dice DÓNDE estás, no QUÉ producto es. Por eso ya no repite
 * "Compilador GPM", que ahora encabeza la barra lateral.
 *
 * El logo va aquí y no en la barra lateral por una razón concreta: sobre esta
 * superficie clara puede ir en sus colores institucionales —guinda, granate y
 * oro—, mientras que sobre el guinda de la lateral habría que degradarlo a
 * monocromo para que se viera. Y sustituye al texto "Gobierno del Estado de
 * Hidalgo", que es literalmente lo que el logo ya dice.
 */
export default function AppHeader({ titulo }: { titulo: string }) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-card px-6">
      <span className="font-heading text-lg font-bold tracking-tight text-primary">
        {titulo}
      </span>
      <img
        src="/logo-hidalgo-coemere.svg"
        alt="Gobierno del Estado de Hidalgo · Comisión Estatal de Mejora Regulatoria"
        className="hidden h-8 w-auto sm:block"
      />
    </header>
  );
}
