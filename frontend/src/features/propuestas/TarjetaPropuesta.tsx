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
import { redactarHueco, tituloDeCodigo } from "@/features/huecos/lenguaje";
import type { ClaveDocumento, DocumentoGenerado, Hueco } from "@/lib/types";

import DiagramaMermaid from "./DiagramaMermaid";

type Props = {
  titulo: string;
  clave: ClaveDocumento;
  /** `null` cuando no hubo propuesta (error, sin licencia). */
  documento: DocumentoGenerado | null;
  onDecidir: (decision: "aceptada" | "corregida" | "declinada", textoFinal?: string) => void;
  onSubir: (archivo: File) => void;
  ocupado: boolean;
};

const NOMBRE_CORTO: Record<ClaveDocumento, string> = { diccionario: "Diccionario", tobe: "TO-BE" };

/** "1 dato que falta · 2 por confirmar" — contados por gravedad, como en el wizard. */
function resumenHuecos(huecos: Hueco[]): string {
  const n = (nivel: string) => huecos.filter((h) => h.nivel === nivel).length;
  const partes = [
    [n("bloqueante"), "bloqueante", "bloqueantes"],
    [n("falta_dato"), "dato que falta", "datos que faltan"],
    [n("por_confirmar"), "por confirmar", "por confirmar"],
  ] as const;
  const texto = partes
    .filter(([k]) => k > 0)
    .map(([k, s, p]) => `${k} ${k === 1 ? s : p}`)
    .join(" · ");
  return texto || "Sin pendientes del verificador";
}

function ZonaDeCarga({
  clave,
  onSubir,
  ocupado,
  ayuda,
}: Pick<Props, "clave" | "onSubir" | "ocupado"> & { ayuda?: string }) {
  const id = `subir-${clave}`;
  return (
    <div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-4">
      <label htmlFor={id} className="text-sm font-medium">
        Subir mi {NOMBRE_CORTO[clave]}
      </label>
      {ayuda ? <p className="text-sm text-muted-foreground">{ayuda}</p> : null}
      <input
        id={id}
        type="file"
        accept=".md,.docx,.pdf,text/markdown"
        disabled={ocupado}
        className="text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onSubir(f);
        }}
      />
    </div>
  );
}

export default function TarjetaPropuesta({
  titulo,
  clave,
  documento,
  onDecidir,
  onSubir,
  ocupado,
}: Props) {
  const [texto, setTexto] = useState(documento?.texto ?? "");
  // Si el servidor manda otra version (recarga), el editor la toma. Lo que la
  // persona escribio y no acepto no sobrevive una recarga a proposito: el
  // borrador vive en el servidor; la edicion, en la pantalla.
  useEffect(() => setTexto(documento?.texto ?? ""), [documento?.texto]);
  const cambiado = documento !== null && texto !== documento.texto;

  const cerrado =
    documento !== null &&
    (documento.decision === "aceptada" || documento.decision === "corregida");
  const cargar = documento === null || documento.decision === "declinada";

  return (
    <Card role="article" aria-label={titulo} className="py-4">
      <CardHeader>
        <CardTitle>{titulo}</CardTitle>
        {documento ? (
          <CardDescription>
            {resumenHuecos(documento.huecos)} · ronda {documento.ronda}
          </CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {cerrado ? (
          <>
            <p className="text-sm text-foreground">
              {documento.decision === "aceptada"
                ? "Aceptado tal cual."
                : "Aceptado con tus cambios."}
            </p>
            {/* Si al juntar los dos el extractor no saca pantallas, sin esto
                no habria forma de corregir: la decision ya no se puede cambiar. */}
            <ZonaDeCarga
              clave={clave}
              onSubir={onSubir}
              ocupado={ocupado}
              ayuda="Si hace falta, sube tu propio archivo en su lugar."
            />
          </>
        ) : cargar ? (
          <ZonaDeCarga clave={clave} onSubir={onSubir} ocupado={ocupado} />
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Esto lo propuso un modelo a partir del AS-IS. Revísalo como revisarías el
              trabajo de alguien nuevo.
            </p>
            <textarea
              aria-label={`Texto propuesto de ${titulo}`}
              className="min-h-72 w-full rounded-md border border-border bg-card p-3 font-mono text-sm"
              value={texto}
              disabled={ocupado}
              onChange={(e) => setTexto(e.target.value)}
              spellCheck={false}
            />
            {clave === "tobe" ? <DiagramaMermaid texto={texto} /> : null}
            {documento.huecos.length > 0 ? (
              <ul className="flex flex-col gap-2 text-sm">
                {documento.huecos.map((h, i) => (
                  <li
                    key={`${h.codigo}-${h.ubicacion}-${i}`}
                    className="rounded-md border border-border p-2"
                  >
                    <strong className="block">{tituloDeCodigo(h.codigo)}</strong>
                    {redactarHueco(h)}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        )}
      </CardContent>
      {!cerrado && !cargar ? (
        <CardFooter className="flex flex-wrap gap-2">
          <Button type="button" disabled={ocupado} onClick={() => onDecidir("aceptada", undefined)}>
            Aceptar tal cual
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={ocupado || !cambiado}
            onClick={() => onDecidir("corregida", texto)}
          >
            Aceptar con mis cambios
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={ocupado}
            onClick={() => onDecidir("declinada")}
          >
            Declinar y subir el mío
          </Button>
        </CardFooter>
      ) : null}
    </Card>
  );
}
