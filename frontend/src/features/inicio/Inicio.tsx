import { FolderOpen, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { leerCapacidades } from "@/lib/api";
import type { Capacidades } from "@/lib/types";

const CLASE_EMPEZAR =
  "inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/80";

/**
 * La primera pregunta: ¿que tienes del tramite? Cada camino con una frase de
 * cuando usarlo. Sin licencia, el del AS-IS lo dice aqui, antes de subir nada.
 */
export default function Inicio() {
  // Mientras no se sepa, el camino se muestra activo: si la consulta falla,
  // el error llega al subir, como antes de que existiera esta pregunta.
  const [cap, setCap] = useState<Capacidades>({ proponer: true, motivo: null });

  useEffect(() => {
    let vivo = true;
    leerCapacidades()
      .then((c) => {
        if (vivo) setCap(c);
      })
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <section className="flex flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">¿Qué tienes del trámite?</h1>
        <p className="text-sm text-muted-foreground">
          Elige un camino. Los dos terminan en la misma revisión, el simulador y el .gpm.
        </p>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <Card role="article" aria-label="Tengo el expediente completo" className="py-4">
          <CardHeader>
            <FolderOpen aria-hidden className="size-8 text-primary" />
            <CardTitle className="text-lg">Tengo el expediente completo</CardTitle>
            <CardDescription>
              AS-IS, TO-BE y Diccionario ya están listos. Sube la carpeta y el compilador te
              dice qué le falta para generar el .gpm.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <a
              href="/expediente"
              aria-label="Empezar con el expediente completo"
              className={CLASE_EMPEZAR}
            >
              Empezar →
            </a>
          </CardFooter>
        </Card>
        <Card role="article" aria-label="Solo tengo el AS-IS" className="py-4">
          <CardHeader>
            <Sparkles aria-hidden className="size-8 text-primary" />
            <CardTitle className="text-lg">Solo tengo el AS-IS</CardTitle>
            <CardDescription>
              El compilador propone el Diccionario y el TO-BE a partir del AS-IS. Tú los
              revisas, los corriges si hace falta y decides si se usan.
            </CardDescription>
          </CardHeader>
          {!cap.proponer && cap.motivo ? (
            <CardContent>
              {/* Enfocable: un boton desactivado no recibe el foco, y sin esto
                  quien navega con teclado nunca llegaba al motivo. */}
              <p
                id="motivo-sin-proponer"
                tabIndex={0}
                className="rounded-md border border-border bg-muted p-3 text-sm"
              >
                {cap.motivo}
              </p>
            </CardContent>
          ) : null}
          <CardFooter>
            {cap.proponer ? (
              <a href="/desde-as-is" aria-label="Empezar con el AS-IS" className={CLASE_EMPEZAR}>
                Empezar →
              </a>
            ) : (
              <Button
                type="button"
                disabled
                aria-label="Empezar con el AS-IS"
                aria-describedby="motivo-sin-proponer"
              >
                Empezar →
              </Button>
            )}
          </CardFooter>
        </Card>
      </div>
      <footer className="text-sm text-muted-foreground">
        <a className="text-primary underline underline-offset-2" href="/historial">
          Ver expedientes anteriores
        </a>
      </footer>
    </section>
  );
}
