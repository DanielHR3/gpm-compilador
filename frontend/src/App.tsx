import { useEffect, useState } from "react";

import AppHeader from "@/components/AppHeader";
import NavegacionLateral from "@/components/NavegacionLateral";
import { Toaster } from "@/components/ui/sonner";
import CargaInsumos from "@/features/carga/CargaInsumos";
import WizardHuecos from "@/features/huecos/WizardHuecos";
import { leerExpediente } from "@/lib/api";
import type { EstadoExpediente } from "@/lib/types";

/**
 * Raiz de la SPA. SP1: sin router (llega en Task 11). Deep-link minimo para
 * `/revisar/:sid` (sid = 16 hex): si la URL encaja, se carga el expediente y se
 * entra directo al wizard; si no existe, se avisa y se cae a la carga. Mientras
 * no haya expediente se muestra la carga de insumos.
 */
const RE_REVISAR = /^\/revisar\/([0-9a-f]{16})$/;

export default function App() {
  const [est, setEst] = useState<EstadoExpediente | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    const m = RE_REVISAR.exec(window.location.pathname);
    if (!m) return;
    leerExpediente(m[1])
      .then(setEst)
      .catch(() =>
        setAviso("La sesion expiro o no existe. Vuelve a subir los insumos."),
      );
  }, []);

  return (
    <>
      <AppHeader />
      {/* Area de avisos de toda la SPA: `useAccion` publica aqui los errores
          de la API y `WizardHuecos` los acuses de cada hueco resuelto. */}
      <Toaster />
      {/* Armazon de dos columnas. La barra de proceso vive aqui y no dentro de
          cada pantalla para que sobreviva al cambio de paso, igual que hacia la
          version servidor antes de la migracion a React. */}
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:gap-8 sm:px-6">
        <aside className="sm:sticky sm:top-6 sm:self-start">
          <NavegacionLateral sid={est?.sid ?? null} />
        </aside>
        <div className="min-w-0 flex-1">
          {aviso ? (
            <p role="alert" className="pb-4 text-sm text-destructive">
              {aviso}
            </p>
          ) : null}
          {est ? (
            <WizardHuecos estado={est} onEstado={setEst} />
          ) : (
            <CargaInsumos onListo={setEst} />
          )}
        </div>
      </div>
    </>
  );
}
