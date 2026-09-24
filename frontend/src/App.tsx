import { useEffect, useState } from "react";

import AppHeader from "@/components/AppHeader";
import NavegacionLateral from "@/components/NavegacionLateral";
import PieInstitucional from "@/components/PieInstitucional";
import { Toaster } from "@/components/ui/sonner";
import CargaInsumos from "@/features/carga/CargaInsumos";
import Propuestas from "@/features/propuestas/Propuestas";
import Catalogos from "@/features/catalogos/Catalogos";
import Historial from "@/features/historial/Historial";
import Tablero from "@/features/tablero/Tablero";
import WizardHuecos from "@/features/huecos/WizardHuecos";
import { useUrlDeRevision } from "@/features/huecos/useUrlDeRevision";
import { ErrorApi, leerExpediente } from "@/lib/api";
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
  // Fase 3: sesion nacida solo con el AS-IS y aun sin manifiesto.
  const [sidPropuesta, setSidPropuesta] = useState<string | null>(null);

  // El expediente abierto tiene direccion propia: sin ella, salir al
  // simulador y volver con Atras aterrizaba en la carga de insumos. La
  // pantalla de Propuestas tambien: «puedes cerrar y volver» depende de ello.
  useUrlDeRevision(est?.sid ?? sidPropuesta);

  useEffect(() => {
    const m = RE_REVISAR.exec(window.location.pathname);
    if (!m) return;
    leerExpediente(m[1])
      .then(setEst)
      .catch((e: unknown) => {
        // 409: la sesion nacio en la Fase 3 y aun no tiene manifiesto. Se
        // reabre en «Propuestas» en el estado en que este.
        if (e instanceof ErrorApi && e.status === 409) setSidPropuesta(m[1]);
        else setAviso("La sesion expiro o no existe. Vuelve a subir los insumos.");
      });
  }, []);

  // Referencia, no un paso: se sirve sin expediente. El servidor entrega
  // index.html para cualquier ruta que no sea de un handler real.
  const enCatalogos = window.location.pathname === "/catalogos";
  // Hasta el 2026-09-23 era HTML del servidor (`plantillas.historial`).
  const enHistorial = window.location.pathname === "/historial";
  const enTablero = window.location.pathname === "/tablero";

  return (
    <div className="flex min-h-svh bg-background">
      <Toaster />
      <NavegacionLateral sid={est?.sid ?? null} tramite={nombreDelTramite(est)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader
            titulo={
              enCatalogos ? "Catálogos"
              : enHistorial ? "Historial"
              : enTablero ? "Tablero"
              : est ? "Revisión del expediente"
              : sidPropuesta ? "Propuesta del compilador"
              : "Carga de insumos"
            }
          />
        <main className="flex-1 px-6 py-8">
          {aviso ? (
            <p role="alert" className="pb-4 text-sm text-destructive">
              {aviso}
            </p>
          ) : null}
          {enCatalogos ? (
            <Catalogos />
          ) : enHistorial ? (
            <Historial />
          ) : enTablero ? (
            <Tablero />
          ) : est ? (
            <WizardHuecos estado={est} onEstado={setEst} />
          ) : sidPropuesta ? (
            <Propuestas
              sid={sidPropuesta}
              onListo={(e) => {
                setSidPropuesta(null);
                setEst(e);
              }}
            />
          ) : (
            <CargaInsumos onListo={setEst} onPropuesta={setSidPropuesta} />
          )}
        </main>
        <PieInstitucional />
      </div>
    </div>
  );
}
