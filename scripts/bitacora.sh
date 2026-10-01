#!/usr/bin/env bash
# Borrador de «Lo que se hizo» para la entrada de la bitacora de un dia.
# Uso: scripts/bitacora.sh [AAAA-MM-DD]   (por omision, hoy)
# Sale en Markdown por stdout; se pega en la nota del dia y se completa a mano.
set -euo pipefail
dia="${1:-$(date +%F)}"
raiz="$(git rev-parse --show-toplevel)"
cliff="${GIT_CLIFF:-$(command -v git-cliff || echo "$raiz/.venv/bin/git-cliff")}"
commits=$(git log --reverse --format=%H --since="$dia 00:00" --until="$dia 23:59:59")
if [ -z "$commits" ]; then
  echo "Sin commits el $dia." >&2
  exit 1
fi
primero=$(echo "$commits" | head -1)
ultimo=$(echo "$commits" | tail -1)
# El rango excluye su inicio: se parte del padre del primero (o de la raiz).
if git rev-parse -q --verify "$primero^" >/dev/null; then
  rango="$primero^..$ultimo"
else
  rango="$ultimo"
fi
"$cliff" --config "$raiz/cliff.toml" "$rango" 2>/dev/null
