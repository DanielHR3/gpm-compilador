/**
 * Barra institucional persistente. Vive fuera de cada pantalla (montada una
 * vez en `App.tsx`) para que la identidad del Compilador GPM no dependa de
 * que cada feature la reimplemente. Puramente de marca: no lleva navegación
 * ni estado, así que no hay contrato que preservar entre features salvo el
 * roble `role="banner"` que da el propio `<header>`.
 */
export default function AppHeader() {
  return (
    <header
      className="border-b-2 bg-primary text-primary-foreground"
      style={{ borderColor: "var(--brand-secondary)" }}
    >
      <div className="mx-auto flex max-w-3xl items-baseline justify-between gap-4 px-8 py-3">
        <span className="font-heading text-base font-semibold tracking-tight">
          Compilador GPM
        </span>
        <span className="text-xs text-primary-foreground/75">
          Gobierno del Estado de Hidalgo
        </span>
      </div>
    </header>
  );
}
