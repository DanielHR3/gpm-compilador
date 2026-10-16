import type { ReactNode } from "react";

/**
 * Pinta el Markdown que escribe `documentoDeObservaciones`, y solo ese
 * dialecto: encabezados de uno a tres niveles, viñetas, listas numeradas,
 * citas, negritas y cursivas. No hay dependencia nueva porque el texto lo
 * generamos nosotros; lo que no se reconoce se pinta como párrafo. Nunca
 * entra HTML: todo son nodos de React, así que un `<img onerror>` en una
 * etiqueta del Diccionario se ve como texto.
 */
export default function Markdown({ texto }: { texto: string }) {
  const bloques: ReactNode[] = [];
  const lineas = texto.split(/\r?\n/);
  let i = 0;
  let k = 0;
  const key = () => `b${k++}`;

  while (i < lineas.length) {
    const linea = lineas[i];
    if (linea.trim() === "") {
      i++;
      continue;
    }
    const enc = /^(#{1,3})\s+(.*)$/.exec(linea);
    if (enc) {
      const nivel = enc[1].length;
      const cuerpo = enLinea(enc[2]);
      bloques.push(
        nivel === 1 ? <h1 key={key()} className="text-xl font-bold tracking-tight">{cuerpo}</h1>
        : nivel === 2 ? <h2 key={key()} className="mt-4 border-b border-border pb-1 text-base font-semibold">{cuerpo}</h2>
        : <h3 key={key()} className="mt-3 text-sm font-semibold text-primary">{cuerpo}</h3>,
      );
      i++;
      continue;
    }
    if (/^- /.test(linea) || /^\d+\. /.test(linea)) {
      const numerada = /^\d+\. /.test(linea);
      const patron = numerada ? /^\d+\. / : /^- /;
      const items: ReactNode[] = [];
      while (i < lineas.length && patron.test(lineas[i])) {
        items.push(<li key={key()}>{enLinea(lineas[i].replace(patron, ""))}</li>);
        i++;
      }
      bloques.push(
        numerada
          ? <ol key={key()} className="list-decimal space-y-1 pl-5">{items}</ol>
          : <ul key={key()} className="list-disc space-y-1 pl-5">{items}</ul>,
      );
      continue;
    }
    if (/^> /.test(linea)) {
      const partes: string[] = [];
      while (i < lineas.length && /^> /.test(lineas[i])) {
        partes.push(lineas[i].slice(2));
        i++;
      }
      bloques.push(
        <blockquote key={key()} className="border-l-2 border-primary/40 pl-3 text-muted-foreground">
          {enLinea(partes.join(" "))}
        </blockquote>,
      );
      continue;
    }
    // Párrafo: líneas seguidas hasta la próxima en blanco.
    const partes: string[] = [];
    while (i < lineas.length && lineas[i].trim() !== "" && !/^(#{1,3}\s|- |\d+\. |> )/.test(lineas[i])) {
      partes.push(lineas[i]);
      i++;
    }
    bloques.push(<p key={key()}>{enLinea(partes.join(" "))}</p>);
  }

  return <div className="flex flex-col gap-2 text-sm leading-relaxed text-foreground">{bloques}</div>;
}

/** `**negrita**` y `_cursiva_` dentro de una línea; lo demás, texto. */
function enLinea(texto: string): ReactNode[] {
  const salida: ReactNode[] = [];
  const re = /\*\*(.+?)\*\*|(?:^|(?<=\s))_(.+?)_(?=\s|[.,;:]|$)/g;
  let ultimo = 0;
  let m: RegExpExecArray | null;
  let n = 0;
  while ((m = re.exec(texto)) !== null) {
    if (m.index > ultimo) salida.push(texto.slice(ultimo, m.index));
    if (m[1] !== undefined) salida.push(<strong key={`s${n++}`} className="font-semibold">{m[1]}</strong>);
    else salida.push(<em key={`e${n++}`}>{m[2]}</em>);
    ultimo = m.index + m[0].length;
  }
  if (ultimo < texto.length) salida.push(texto.slice(ultimo));
  return salida;
}
