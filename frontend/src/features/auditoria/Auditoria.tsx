import { useCallback, useEffect, useState } from "react";
import { Download, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "cn";
import { leerAuditoria, urlAuditoriaCsv, type FiltrosAuditoria } from "@/lib/api";
import type { FilaAuditoria } from "@/lib/types";

import { fechaCorta, redactarEvento } from "./lenguaje";

/**
 * «Quién hizo qué»: la bitácora de acciones para la auditoría interna de la
 * DGT. Solo la ve el superusuario (el servidor responde 403 a los demás). Una
 * tarjeta por evento, filtros arriba y el mismo filtro como CSV. El registro
 * no se toca desde aquí: nadie borra filas.
 */
export default function Auditoria({ sidInicial = null }: { sidInicial?: string | null }) {
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({ sid: sidInicial ?? undefined, limite: 500 });
  const [borrador, setBorrador] = useState({ sid: sidInicial ?? "", usuario: "", desde: "", solo_errores: false });
  const [filas, setFilas] = useState<FilaAuditoria[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback((f: FiltrosAuditoria) => {
    setError(null);
    leerAuditoria(f)
      .then((r) => setFilas(r.filas))
      .catch(() => setError("No se pudo leer la bitácora. Solo el superusuario puede verla."));
  }, []);
  useEffect(() => cargar(filtros), [cargar, filtros]);

  const buscar = () => {
    const sid = borrador.sid.trim();
    const usuario = borrador.usuario.trim();
    const desde = borrador.desde.trim();
    setFiltros({
      sid: sid || undefined, usuario: usuario || undefined, desde: desde || undefined,
      solo_errores: borrador.solo_errores || undefined, limite: 500,
    });
  };

  return (
    <section className="flex max-w-5xl flex-col gap-6 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Quién hizo qué</h1>
        <p className="text-sm text-muted-foreground">
          Cada acción sobre un trámite, con la persona, el momento y desde dónde. Lo anota el servidor
          solo; nadie puede borrarlo. Los fallos del servidor llevan un número para buscarlos en el
          registro técnico.
        </p>
      </header>

      <form
        aria-label="Filtros"
        className="grid gap-3 rounded-lg border border-border bg-card p-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          buscar();
        }}
      >
        <label className="flex flex-col gap-1 text-xs font-medium">
          Usuario (correo)
          <Input value={borrador.usuario} onChange={(e) => setBorrador({ ...borrador, usuario: e.target.value })} placeholder="nombre@hidalgo.gob.mx" />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Trámite (id de sesión)
          <Input value={borrador.sid} onChange={(e) => setBorrador({ ...borrador, sid: e.target.value })} placeholder="16 caracteres" className="font-mono" />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Desde
          <Input type="date" value={borrador.desde} onChange={(e) => setBorrador({ ...borrador, desde: e.target.value })} />
        </label>
        <label className="flex items-center gap-2 self-end pb-2 text-sm">
          <input type="checkbox" checked={borrador.solo_errores} onChange={(e) => setBorrador({ ...borrador, solo_errores: e.target.checked })} className="size-4 accent-primary" />
          Solo errores
        </label>
        <div className="flex gap-2 self-end">
          <Button type="submit" size="sm">
            <Search aria-hidden className="size-4" />
            Buscar
          </Button>
          <Button variant="outline" size="sm" render={<a href={urlAuditoriaCsv(filtros)} download>Descargar CSV</a>}>
            <Download aria-hidden className="size-4" />
            Descargar CSV
          </Button>
        </div>
      </form>

      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
      {filas === null && !error ? <p className="text-sm text-muted-foreground">Leyendo la bitácora…</p> : null}
      {filas !== null && filas.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-4 py-5 text-center text-sm text-muted-foreground">
          Sin eventos con esos filtros.
        </p>
      ) : null}

      {filas && filas.length > 0 ? (
        <ul aria-label="Eventos" className="flex flex-col gap-2">
          {filas.map((f, i) => {
            const ev = redactarEvento(f);
            return (
              <li key={`${f.fecha}-${i}`}>
                <Card
                  role="article"
                  aria-label={`${fechaCorta(f.fecha)} · ${f.usuario}`}
                  className={cn("py-3", ev.fallo && "border-l-4 border-l-destructive", ev.rechazo !== null && "border-l-4 border-l-amber-500")}
                >
                  <CardHeader className="gap-0.5 py-0">
                    <CardTitle className="text-sm font-semibold leading-snug">{ev.frase}</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-x-4 gap-y-1 pt-1 text-xs text-muted-foreground">
                    <span className="text-foreground">{f.usuario}{f.dependencia ? ` · ${f.dependencia}` : ""}</span>
                    <time dateTime={f.fecha}>{fechaCorta(f.fecha)}</time>
                    {f.sid ? (
                      <a href={`/revisar/${f.sid}`} className="font-mono text-primary underline underline-offset-2">
                        {f.sid.slice(0, 8)}
                      </a>
                    ) : null}
                    {f.ip ? <span className="font-mono">{f.ip}</span> : null}
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
