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
import Recuperar, { Restablecer } from "@/features/sesion/Recuperar";
import Registro from "@/features/sesion/Registro";
import Usuarios from "@/features/usuarios/Usuarios";
import Auditoria from "@/features/auditoria/Auditoria";
import { useSesion } from "@/features/sesion/useSesion";
import Tablero from "@/features/tablero/Tablero";
import Comparativa from "@/features/comparativa/Comparativa";
import Documentos from "@/features/documentos/Documentos";
import WizardHuecos from "@/features/huecos/WizardHuecos";
import { useUrlDeRevision } from "@/features/huecos/useUrlDeRevision";
import { ErrorApi, leerExpediente, leerGenerados } from "@/lib/api";
import { leerRuta, migas, type Camino } from "@/lib/rutas";
import type { EstadoExpediente, Hueco } from "@/lib/types";

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
  const ruta = leerRuta(window.location.pathname, window.location.search);
  const [est, setEst] = useState<EstadoExpediente | null>(null);
  // Estado de la puerta del linter que reporta el wizard; alimenta el menu
  // «Entrega» de la barra superior.
  const [puerta, setPuerta] = useState<{ desbloqueado: boolean; bloqueantes: Hueco[] } | null>(null);
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
    : ruta.tipo === "comparativa" ? "Antes y después"
    : ruta.tipo === "documentos" ? "Documentos del trámite"
    : ruta.tipo === "usuarios" ? "Cuentas"
    : ruta.tipo === "auditoria" ? "Quién hizo qué"
    : est ? "Revisión del expediente"
    : sidPropuesta ? "Propuesta del compilador"
    : ruta.tipo === "expediente" ? "Expediente completo"
    : ruta.tipo === "desde_as_is" ? "Solo AS-IS"
    : "Inicio";

  let contenido: ReactNode;
  if (ruta.tipo === "catalogos") contenido = <Catalogos />;
  else if (ruta.tipo === "historial") contenido = <Historial />;
  else if (ruta.tipo === "tablero") contenido = <Tablero />;
  else if (ruta.tipo === "comparativa") contenido = <Comparativa sid={ruta.sid} />;
  else if (ruta.tipo === "documentos") contenido = <Documentos sid={ruta.sid} />;
  else if (ruta.tipo === "usuarios")
    contenido = sesion.usuario?.rol === "admin"
      ? <Usuarios yo={sesion.usuario.correo} />
      : <p role="alert" className="text-sm text-destructive">Solo el superusuario puede administrar cuentas.</p>;
  else if (ruta.tipo === "auditoria")
    contenido = sesion.usuario?.rol === "admin"
      ? <Auditoria sidInicial={ruta.sid} />
      : <p role="alert" className="text-sm text-destructive">Solo el superusuario puede ver quién hizo qué.</p>;
  else if (est)
    contenido = (
      <>
        <MigasDePan tramos={migas("revision", camino)} />
        <WizardHuecos estado={est} onEstado={setEst} onPuerta={setPuerta} />
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

  // El menu «Entrega» acompaña al expediente: con semaforo en la revision, y
  // como atajo en las paginas que no cargan el expediente (comparativa,
  // documentos), donde la SPA no sabe el estado de la puerta.
  const entrega =
    ruta.tipo === "comparativa" || ruta.tipo === "documentos" ? { sid: ruta.sid, puerta: null }
    : est && ruta.tipo === "revisar" ? { sid: est.sid, puerta }
    : null;

  if (sesion.estado === "cargando") return <div className="min-h-svh bg-background" />;
  // Sin sesion solo existen las pantallas publicas; cualquier otra liga cae
  // en la entrada y, al entrar, se queda en la ruta que traia.
  if (sesion.estado === "cerrada") {
    if (ruta.tipo === "registro") return <Registro />;
    if (ruta.tipo === "recuperar") return <Recuperar />;
    if (ruta.tipo === "restablecer") return <Restablecer token={ruta.token} />;
    return <Entrada onEntrar={sesion.entrar} />;
  }

  return (
    <div className="flex min-h-svh bg-background">
      <Toaster />
      <NavegacionLateral sid={est?.sid ?? null} tramite={nombreDelTramite(est)} admin={sesion.usuario?.rol === "admin"} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader titulo={titulo} usuario={sesion.usuario} onSalir={() => void sesion.salir()} entrega={entrega} />
        {/* Ancho maximo y centrado: en una laptop de 14" llena la columna; en
            un monitor de 27" el blanco queda en las orillas, no entre las
            tarjetas. En telefono el relleno lateral baja a 16 px. */}
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
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
