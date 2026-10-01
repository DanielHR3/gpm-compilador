import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { AnalisisComparativa } from "@/lib/types";

/**
 * En que va el agente que completa la comparativa. Solo aparece cuando hay
 * algo que decir: trabajando, fallo, no disponible o modo de pruebas. Con el
 * analisis hecho y sin novedad, la pagina no lleva un aviso de mas.
 */
export default function EstadoAnalisis({
  analisis,
  ocupado,
  aviso,
  onAnalizar,
}: {
  analisis: AnalisisComparativa;
  ocupado: boolean;
  aviso: string | null;
  onAnalizar: () => void;
}) {
  const analizando = analisis.estado === "analizando";
  const noDisponible = !analisis.puede_analizar && analisis.motivo_analizar;
  // «lista» con motivo: las cifras llegaron pero falto la segunda llamada.
  const nota = analisis.estado !== "analizando" ? analisis.motivo : null;

  return (
    <Card>
      <CardContent className="flex flex-col gap-2">
        {analizando ? (
          <div role="status" className="flex flex-col gap-1 text-sm">
            <span className="font-medium">El agente está completando la comparativa…</span>
            <span className="text-xs text-muted-foreground">
              Busca en el AS-IS y el TO-BE las cifras que el compilador no pudo contar. Lo que ya
              está contado no cambia.
            </span>
            <ul className="text-xs text-muted-foreground">
              {analisis.pasos.map((p, i) => (
                <li key={`${p.t}-${i}`}>{p.mensaje}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {nota ? (
          <p role={analisis.estado === "error" ? "alert" : undefined}
             className={analisis.estado === "error" ? "text-sm text-destructive" : "text-sm"}>
            {nota}
          </p>
        ) : null}
        {aviso ? <p role="alert" className="text-sm text-destructive">{aviso}</p> : null}
        {noDisponible ? (
          <p className="text-sm">
            {analisis.motivo_analizar}{" "}
            <span className="text-muted-foreground">
              La comparativa muestra lo que contó el compilador; lo demás se puede escribir a mano.
            </span>
          </p>
        ) : null}
        {analisis.pruebas ? (
          <p className="rounded-md bg-muted/60 p-2 text-xs">
            Modo de pruebas: para completar esta página, el AS-IS y el TO-BE de este expediente
            viajan a Gemini.
          </p>
        ) : null}
        {analisis.estado === "lista" && !nota ? (
          <p className="text-sm text-muted-foreground">
            Las cifras rotuladas «propuesto por el agente» salen de frases del expediente: ábrelas
            en cada tarjeta y corrige la que no se sostenga.
          </p>
        ) : null}
        {analisis.puede_analizar && !analizando && analisis.estado !== "sin_analizar" ? (
          <Button type="button" size="sm" variant="outline" className="self-start"
                  disabled={ocupado} onClick={onAnalizar}>
            <Sparkles aria-hidden />
            Volver a analizar
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
