import { useEffect, useState } from "react";

import AppHeader from "@/components/AppHeader";
import NavegacionLateral from "@/components/NavegacionLateral";
import PieInstitucional from "@/components/PieInstitucional";
import { Toaster } from "@/components/ui/sonner";
import CargaInsumos from "@/features/carga/CargaInsumos";
import WizardHuecos from "@/features/huecos/WizardHuecos";
import { leerExpediente } from "@/lib/api";
import type { EstadoExpediente } from "@/lib/types";

/**
 * Raiz de la SPA. Deep-link minimo para `/revisar/:sid` (sid = 16 hex): si la
 * URL encaja, se carga el expediente y se entra directo al wizard; si no
 * existe, se avisa y se cae a la carga. Mientras no haya expediente se muestra
 * la carga de insumos.
 *
 * El armazon —barra lateral guinda fija, barra superior blanca, contenido
 * sobre `surface-app`— es el mismo de `checador-web` y `GeoApertura`.
 */
const RE_REVISAR = /^\/revisar\/([0-9a-f]{16})$/;

/** Lee `manifiesto.tramite.nombre` sin confiar en que exista. */
function nombreDelTramite(est: EstadoExpediente | null): string | null {
  const t = (est?.manifiesto as { tramite?: { nombre?: unknown } } | undefined)
    ?.tramite?.nombre;
  if (typeof t !== "string" || t === "" || t === "[por confirmar]") return null;
  return t;
}

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
    <div className="flex min-h-svh bg-background">
      <Toaster />
      <NavegacionLateral sid={est?.sid ?? null} tramite={nombreDelTramite(est)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader titulo={est ? "Revisión del expediente" : "Carga de insumos"} />
        <main className="flex-1 px-6 py-8">
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
        </main>
        <PieInstitucional />
      </div>
    </div>
  );
}
