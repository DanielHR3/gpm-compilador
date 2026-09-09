#!/usr/bin/env bash
# Gate del frontend (SPA React). Ejecuta la cadena completa:
#   1. tipos    -> tsc -b --noEmit  (project references de la plantilla Vite)
#   2. pruebas  -> vitest run
#   3. build    -> npm run build     (deja frontend/dist/, que NO se comitea)
set -euo pipefail
cd "$(dirname "$0")/../frontend"

npx tsc -b --noEmit
npx vitest run
npm run build
