import type { ReactNode } from "react";

import PieInstitucional from "@/components/PieInstitucional";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * El marco de las pantallas sin sesión (entrar, registro, recuperación):
 * superficie `background`, una tarjeta centrada con el logo institucional y el
 * nombre del producto en guinda, y la greca al pie. Es la misma casa que el
 * resto de la SPA, sin la barra lateral porque todavía no hay a dónde ir.
 */
export default function MarcoSesion({
  titulo,
  descripcion,
  etiqueta,
  children,
}: {
  titulo: string;
  descripcion: string;
  /** `aria-label` de la región, para las pruebas y los lectores de pantalla. */
  etiqueta: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <Card role="region" aria-label={etiqueta} className="w-full max-w-md py-6">
          <CardHeader className="items-center text-center">
            <img
              src="/logo-hidalgo-coemere.svg"
              alt="Gobierno del Estado de Hidalgo · Comisión Estatal de Mejora Regulatoria"
              className="mx-auto mb-2 h-10 w-auto"
            />
            <p className="font-heading text-sm font-semibold uppercase tracking-wide text-primary">
              Compilador GPM
            </p>
            <CardTitle className="font-heading text-xl">
              <h1>{titulo}</h1>
            </CardTitle>
            <CardDescription>{descripcion}</CardDescription>
          </CardHeader>
          <CardContent>{children}</CardContent>
        </Card>
      </main>
      <PieInstitucional />
    </div>
  );
}
