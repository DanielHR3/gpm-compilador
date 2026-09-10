import { useEffect, useState } from "react";

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

  if (est) return <WizardHuecos estado={est} onEstado={setEst} />;

  return (
    <>
      {aviso ? (
        <p
          role="alert"
          className="mx-auto max-w-3xl px-8 pt-8 text-sm text-destructive"
        >
          {aviso}
        </p>
      ) : null}
      <CargaInsumos onListo={setEst} />
    </>
  );
}
