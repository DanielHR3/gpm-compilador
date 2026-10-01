#!/usr/bin/env bash
# Espejo de los documentos del repo en la boveda de Obsidian, en UN solo
# sentido: repo -> boveda. Reemplaza las copias a mano de specs y actas.
#
# Uso: GPMC_BOVEDA="<.../Compilador GPM>" scripts/a-boveda.sh
#
# Escribe solo dentro de «07 - Documentacion tecnica interna/_espejo-repo/», que
# se regenera entera: nada ahi se edita a mano. Nunca lee de la boveda: lo de
# 07 (hallazgos SEG, inventario de AWS) es privado y el repo es publico.
# Sin enlaces simbolicos: Obsidian los desaconseja junto con su sincronizacion.
set -euo pipefail
raiz="$(git rev-parse --show-toplevel)"
boveda="${GPMC_BOVEDA:?pon GPMC_BOVEDA con la carpeta del proyecto en la boveda}"
destino="$boveda/07 - Documentacion tecnica interna/_espejo-repo"
[ -d "$boveda/07 - Documentacion tecnica interna" ] || { echo "No es la carpeta del proyecto: $boveda" >&2; exit 2; }

commit="$(git -C "$raiz" rev-parse --short HEAD)"
fecha="$(git -C "$raiz" log -1 --format=%cs)"
sucio=""; git -C "$raiz" diff --quiet HEAD -- docs planeacion/actas || sucio=" (con cambios sin comitear)"

# Origen (relativo al repo) -> subcarpeta del espejo.
fuentes=(
  "docs/superpowers/specs:specs"
  "planeacion/actas:actas"
  "docs/decisiones:decisiones"
)

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
for par in "${fuentes[@]}"; do
  origen="${par%%:*}"; sub="${par##*:}"
  mkdir -p "$tmp/$sub"
  for f in "$raiz/$origen"/*.md; do
    [ -e "$f" ] || continue
    {
      printf -- '---\nespejo_de: %s\ncommit: %s\n---\n\n' "$origen/$(basename "$f")" "$commit"
      printf '> [!info] Copia generada desde el repo (commit `%s`, %s)%s\n' "$commit" "$fecha" "$sucio"
      printf '> **No se edita aquí:** se cambia en `%s` y se corre `scripts/a-boveda.sh`.\n\n' "$origen/$(basename "$f")"
      cat "$f"
    } > "$tmp/$sub/$(basename "$f")"
  done
done

{
  printf '# Espejo del repositorio\n\n'
  printf 'Generado por `scripts/a-boveda.sh` desde el commit `%s` (%s)%s. Se regenera entero.\n\n' "$commit" "$fecha" "$sucio"
  for par in "${fuentes[@]}"; do
    origen="${par%%:*}"; sub="${par##*:}"
    printf '## %s\n\nDe `%s`.\n\n' "$sub" "$origen"
    for f in "$tmp/$sub"/*.md; do
      [ -e "$f" ] || continue
      n="$(basename "$f" .md)"; printf -- '- [[%s/%s|%s]]\n' "$sub" "$n" "$n"
    done
    printf '\n'
  done
} > "$tmp/README.md"

# Solo se borra la carpeta del espejo, y solo si se llama asi.
case "$destino" in */_espejo-repo) ;; *) echo "destino inesperado: $destino" >&2; exit 2;; esac
rm -rf "$destino"
mkdir -p "$destino"
cp -R "$tmp/." "$destino/"
echo "Espejo actualizado en $destino ($(find "$destino" -name '*.md' | wc -l | tr -d ' ') notas, commit $commit)"
