/**
 * En que tareas puede generarse un documento del tramite.
 *
 * Es la regla de `vale_para` (`src/gpmc/extractores/documentos.py`), replicada
 * sobre el manifiesto que la pantalla ya tiene, igual que `candidatos.ts`
 * replica `verificar.py`. El servidor es la autoridad: esto solo anticipa en
 * el desplegable lo que `POST /resolver` (`doc04`) contestaria con un 422.
 *
 * A una tarea le «llegan» los campos de sus pantallas y los de toda tarea
 * desde la que se alcanza. Una rama hermana no aporta: quien va por el
 * rechazo nunca paso por la cotizacion.
 */
export type TareaCandidata = {
  id: string;
  nombre: string;
  vale: boolean;
  /** Por que no vale. Solo cuando `vale` es falso. */
  motivo?: string;
  /** El documento esta colgado hoy de esta tarea. */
  actual: boolean;
};

type TareaCruda = {
  id: string;
  nombre: string;
  terminal: boolean;
  pantallas: string[];
  acciones: string[];
};

const lista = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const objeto = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" ? (v as Record<string, unknown>) : {};
const texto = (v: unknown): string => (typeof v === "string" ? v : "");

/** El manifiesto no esta tipado en la SPA: se lee con tolerancia. */
function leerTareas(manifiesto: Record<string, unknown>): TareaCruda[] {
  return lista(objeto(manifiesto.flujo).tareas).map((t) => {
    const o = objeto(t);
    return {
      id: texto(o.id),
      nombre: texto(o.nombre),
      terminal: o.terminal === true,
      // El servidor manda `{id, modo}`; un manifiesto escrito a mano, el id.
      pantallas: lista(o.pantallas).map((p) =>
        typeof p === "string" ? p : texto(objeto(p).id),
      ),
      acciones: [...lista(o.acciones_antes), ...lista(o.acciones_despues)].map(texto),
    };
  });
}

export function tareasDeDocumento(
  manifiesto: Record<string, unknown>,
  accion: string,
): TareaCandidata[] {
  const doc = lista(manifiesto.acciones)
    .map(objeto)
    .find((a) => a.tipo === "documento" && a.nombre === accion);
  if (!doc) return [];
  const necesarias = lista(doc.variables).map(texto);

  const camposDe = new Map<string, string[]>();
  for (const p of lista(manifiesto.pantallas).map(objeto)) {
    camposDe.set(texto(p.id), lista(p.campos).map((c) => texto(objeto(c).nombre)));
  }

  const tareas = leerTareas(manifiesto);
  const previas = new Map<string, string[]>();
  for (const cx of lista(objeto(manifiesto.flujo).conexiones).map(objeto)) {
    const a = texto(cx.a);
    previas.set(a, [...(previas.get(a) ?? []), texto(cx.de)]);
  }
  const porId = new Map(tareas.map((t) => [t.id, t]));

  return tareas.map((t) => {
    // `vistos` corta los ciclos de correccion (una tarea que regresa a otra).
    const vistos = new Set([t.id]);
    const cola = [t.id];
    while (cola.length) {
      for (const previa of previas.get(cola.pop() as string) ?? []) {
        if (!vistos.has(previa)) {
          vistos.add(previa);
          cola.push(previa);
        }
      }
    }
    const llegan = new Set<string>();
    for (const id of vistos) {
      for (const pantalla of porId.get(id)?.pantallas ?? []) {
        for (const campo of camposDe.get(pantalla) ?? []) llegan.add(campo);
      }
    }
    const faltan = necesarias.filter((v) => !llegan.has(v)).sort();

    let motivo: string | undefined;
    if (t.terminal) motivo = "es el cierre del trámite";
    else if (faltan.length) motivo = `todavía no se capturan: ${faltan.join(", ")}`;

    return {
      id: t.id,
      nombre: t.nombre,
      vale: motivo === undefined,
      ...(motivo ? { motivo } : {}),
      actual: t.acciones.includes(accion),
    };
  });
}
