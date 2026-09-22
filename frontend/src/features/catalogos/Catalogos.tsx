import { useEffect, useState } from "react";

import { leerCatalogos, type CatalogosOut } from "@/lib/api";

/**
 * Seccion «Catalogos»: que endpoints conoce el compilador y con que palabras
 * del Diccionario se activan. Solo lectura y sin llamar a nada en vivo:
 * comprobar que un endpoint responde es trabajo del simulador.
 *
 * Lo de pago o convenio no aparece a proposito (decision del 2026-09-22): se
 * configura en la plataforma, y listarlo aqui invitaria a esperar que salga
 * solo.
 */
export default function Catalogos() {
  const [datos, setDatos] = useState<CatalogosOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    leerCatalogos().then(setDatos).catch(() => setError("No se pudo leer el registro."));
  }, []);

  if (error) return <p role="alert" className="text-sm text-destructive">{error}</p>;
  if (!datos) return <p className="text-sm text-muted-foreground">Cargando…</p>;

  return (
    <section className="flex flex-col gap-4 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Catálogos</h1>
        <p className="text-sm text-muted-foreground">
          El compilador conoce <strong>{datos.catalogos.length} endpoints</strong>. {datos.nota}
        </p>
      </header>
      <table className="w-full text-sm">
        <thead className="text-left font-mono text-[0.625rem] uppercase tracking-[0.09em] text-muted-foreground">
          <tr>
            <th className="py-2 pr-4">Proveedor</th>
            <th className="py-2 pr-4">Qué hace</th>
            <th className="py-2 pr-4">Se activa con</th>
            <th className="py-2 pr-4">Devuelve</th>
            <th className="py-2">URL</th>
          </tr>
        </thead>
        <tbody>
          {datos.catalogos.map((c) => (
            <tr key={c.clave} aria-label={c.proveedor} className="border-t border-border align-top">
              <td className="py-2 pr-4 font-medium">{c.proveedor}</td>
              <td className="py-2 pr-4">
                {c.tipo === "consulta" ? "Consulta: autollena campos" : "Lista para un desplegable"}
              </td>
              <td className="py-2 pr-4">{c.sinonimos.join(", ")}</td>
              <td className="py-2 pr-4">{c.campos_respuesta.join(", ") || "—"}</td>
              <td className="py-2 break-all font-mono text-xs text-muted-foreground">{c.url}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
