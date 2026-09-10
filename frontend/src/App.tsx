import { useState } from "react";

import CargaInsumos from "@/features/carga/CargaInsumos";
import type { EstadoExpediente } from "@/lib/types";

/**
 * Raiz de la SPA. SP1: sin router (llega en Task 11). Mientras no haya
 * expediente se muestra la carga de insumos; al crearlo se guarda el estado y
 * se deja un marcador `<pre>` que Task 10 sustituye por `WizardHuecos`.
 */
export default function App() {
  const [est, setEst] = useState<EstadoExpediente | null>(null);
  if (!est) return <CargaInsumos onListo={setEst} />;
  return <pre data-testid="estado-cargado">{est.sid}</pre>;
}
