import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import AppHeader from "@/components/AppHeader";
import MigasDePan from "@/components/MigasDePan";
import NavegacionLateral from "@/components/NavegacionLateral";
import PieInstitucional from "@/components/PieInstitucional";
import { Toaster } from "@/components/ui/sonner";
import CargaAsIs from "@/features/carga/CargaAsIs";
import CargaInsumos from "@/features/carga/CargaInsumos";
import Propuestas from "@/features/propuestas/Propuestas";
import Catalogos from "@/features/catalogos/Catalogos";
import Historial from "@/features/historial/Historial";
import Inicio from "@/features/inicio/Inicio";
import Entrada from "@/features/sesion/Entrada";
import { useSesion } from "@/features/sesion/useSesion";
import Tablero from "@/features/tablero/Tablero";
import WizardHuecos from "@/features/huecos/WizardHuecos";
import { useUrlDeRevision } from "@/features/huecos/useUrlDeRevision";
import { ErrorApi, leerExpediente, leerGenerados } from "@/lib/api";
import { leerRuta, migas, type Camino } from "@/lib/rutas";
import type { EstadoExpediente } from "@/lib/types";

/**
 * Raiz de la SPA. La pantalla sale de la direccion (`lib/rutas.ts`): `/` es el
 * Inicio con los dos caminos, `/expediente` la carga de la carpeta completa,
 * `/desde-as-is` la del AS-IS, y `/revisar/:sid` abre la sesion (propuesta o
 * revision de huecos). Sin enrutador de terceros.
 *
 * El armazon —barra lateral guinda fija, barra superior blanca, contenido
 * sobre `surface-app`— es el mismo de `checador-web` y `GeoApertura`.
 */
/** Lee `manifiesto.tramite.nombre` sin confiar en que exista. */
function nombreDelTramite(est: EstadoExpediente | null): string | null {
  const t = (est?.manifiesto as { tramite?: { nombre?: unknown } } | undefined)
    ?.tramite?.nombre;
  if (typeof t !== "string" || t === "" || t === "[por confirmar]") return null;
  return t;
}

export default function App() {
  const ruta = leerRuta(window.location.pathname);
  const [est, setEst] = useState<EstadoExpediente | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  // Fase 3: sesion nacida solo con el AS-IS y aun sin manifiesto.
  const [sidPropuesta, setSidPropuesta] = useState<string | null>(null);
  // Por que camino llego la persona. Se sabe al elegir la tarjeta; al abrir
  // una liga `/revisar/{sid}` se deduce: si la sesion tiene propuestas, vino
  // por el AS-IS. Sin respuesta, las migas no nombran camino.
  const [camino, setCamino] = useState<Camino | null>(
    ruta.tipo === "expediente" ? "carpeta" : ruta.tipo === "desde_as_is" ? "as_is" : null,
  );
  const [cargando, setCargando] = useState(ruta.tipo === "revisar");
  // Sesion (spec 2026-09-25): con usuarios, nada se pinta hasta entrar; sin
  // usuarios (la Mac de pruebas) se entra directo, como siempre.
  const sesion = useSesion();

  // El expediente abierto tiene direccion propia: sin ella, salir al
  // simulador y volver con Atras aterrizaba en la carga de insumos. La
  // pantalla de Propuestas tambien: «puedes cerrar y volver» depende de ello.
  useUrlDeRevision(est?.sid ?? sidPropuesta);

  useEffect(() => {
    if (ruta.tipo !== "revisar") return;
    if (sesion.estado === "cargando" || sesion.estado === "cerrada") return;
    const sid = ruta.sid;
    leerExpediente(sid)
      .then((e) => {
        setEst(e);
        leerGenerados(sid)
          .then(() => setCamino("as_is"))
          .catch((err: unknown) => {
            if (err instanceof ErrorApi && err.status === 404) setCamino("carpeta");
          });
      })
      .catch((e: unknown) => {
        // 409: la sesion nacio en la Fase 3 y aun no tiene manifiesto. Se
        // reabre en «Propuestas» en el estado en que este.
        if (e instanceof ErrorApi && e.status === 409) {
          setSidPropuesta(sid);
          setCamino("as_is");
        } else setAviso("La sesion expiro o no existe. Vuelve a subir los insumos.");
      })
      .finally(() => setCargando(false));
    // La ruta se lee una sola vez al montar (y otra vez al abrirse la sesion):
    // los cambios de pantalla dentro de la SPA no recargan.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesion.estado]);

  const titulo =
    ruta.tipo === "catalogos" ? "Catálogos"
    : ruta.tipo === "historial" ? "Historial"
    : ruta.tipo === "tablero" ? "Tablero"
    : est ? "Revisión del expediente"
    : sidPropuesta ? "Propuesta del compilador"
    : ruta.tipo === "expediente" ? "Expediente completo"
    : ruta.tipo === "desde_as_is" ? "Solo AS-IS"
    : "Inicio";

  let contenido: ReactNode;
  if (ruta.tipo === "catalogos") contenido = <Catalogos />;
  else if (ruta.tipo === "historial") contenido = <Historial />;
  else if (ruta.tipo === "tablero") contenido = <Tablero />;
  else if (est)
    contenido = (
      <>
        <MigasDePan tramos={migas("revision", camino)} />
        <WizardHuecos estado={est} onEstado={setEst} />
      </>
    );
  else if (sidPropuesta)
    contenido = (
      <Propuestas
        sid={sidPropuesta}
        onListo={(e) => {
          setSidPropuesta(null);
          setEst(e);
        }}
      />
    );
  else if (cargando)
    contenido = <p className="text-sm text-muted-foreground">Abriendo el expediente…</p>;
  else if (ruta.tipo === "expediente")
    contenido = (
      <>
        <MigasDePan tramos={migas("carga", "carpeta")} />
        <CargaInsumos onListo={setEst} />
      </>
    );
  else if (ruta.tipo === "desde_as_is")
    contenido = (
      <>
        <MigasDePan tramos={migas("carga", "as_is")} />
        <CargaAsIs onPropuesta={setSidPropuesta} />
      </>
    );
  else
    contenido = (
      <>
        <MigasDePan tramos={migas("inicio", null)} />
        <Inicio />
      </>
    );

  if (sesion.estado === "cargando") return <div className="min-h-svh bg-background" />;
  if (sesion.estado === "cerrada") return <Entrada onEntrar={sesion.entrar} />;

  return (
    <div className="flex min-h-svh bg-background">
      <Toaster />
      <NavegacionLateral sid={est?.sid ?? null} tramite={nombreDelTramite(est)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader titulo={titulo} usuario={sesion.usuario} onSalir={() => void sesion.salir()} />
        <main className="flex-1 px-6 py-8">
          {aviso ? (
            <p role="alert" className="pb-4 text-sm text-destructive">
              {aviso}
            </p>
          ) : null}
          {contenido}
        </main>
        <PieInstitucional />
      </div>
    </div>
  );
}
