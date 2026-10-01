import type { PropuestaDeLado } from "@/lib/types";

/**
 * De donde salio una cifra que propuso el agente. La cifra es cuantas frases
 * hay aqui, y cada frase esta copiada del expediente tal como esta escrita:
 * por eso se puede abrir y comprobar. Plegada, para no llenar la tarjeta.
 */
export default function EvidenciaPropuesta({
  lado,
  propuesta,
}: {
  lado: "antes" | "después";
  propuesta: PropuestaDeLado;
}) {
  const n = propuesta.evidencia.length;
  return (
    <div className="flex flex-col gap-1">
      {propuesta.motivo ? <p className="text-xs">{propuesta.motivo}</p> : null}
      <details className="text-xs">
        <summary className="cursor-pointer text-primary underline underline-offset-2">
          {n === 1 ? `Ver la frase de ${lado}` : `Ver las ${n} frases de ${lado}`}
        </summary>
        <ul className="mt-1.5 flex flex-col gap-1.5 border-l-2 border-border pl-3">
          {propuesta.evidencia.map((e, i) => (
            <li key={`${i}-${e.cita}`} className="text-muted-foreground">
              {propuesta.ninguno ? null : <span className="font-medium text-foreground">{e.nombre}</span>}
              {propuesta.ninguno ? null : " — "}«{e.cita}»
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
