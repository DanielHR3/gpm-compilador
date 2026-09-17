#!/bin/bash
# Deja el Compilador GPM corriendo siempre, sin ventana de terminal.
# El equipo de Simplificacion solo abre una liga: no instala ni ejecuta nada.
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ETIQUETA="local.gpmc.servidor"
DESTINO="$HOME/Library/LaunchAgents/$ETIQUETA.plist"

# El log vive FUERA del repo a proposito: si el repo cuelga de ~/Desktop,
# ~/Documents o ~/Downloads, macOS no deja que launchd cree ahi los archivos de
# stdout/stderr del trabajo, y el servicio muere con EX_CONFIG (78) antes de
# arrancar, sin escribir una sola linea que lo explique.
LOG="${GPMC_LOG:-$HOME/Library/Logs/gpmc/servidor.log}"

# Sin almacen las sesiones son temporales y se pierden al reiniciar. Vive fuera
# del repo para que actualizar el codigo no se lleve por delante el trabajo en
# curso de nadie.
ALMACEN="${GPMC_ALMACEN:-$HOME/Library/Application Support/gpmc/sesiones}"

echo "Compilador GPM — instalacion del servicio"
echo "  carpeta: $RAIZ"
echo

if [ ! -d "$RAIZ/.venv" ]; then
  echo "Preparando el entorno…"
  python3 -m venv "$RAIZ/.venv"
  "$RAIZ/.venv/bin/pip" install --quiet --upgrade pip
  "$RAIZ/.venv/bin/pip" install --quiet -e "$RAIZ[web]"
fi

# La SPA React se sirve desde / (frontend/dist/). Se recompila en cada
# instalación para que el servicio arranque con la versión actual.
if command -v npm >/dev/null 2>&1; then
  echo "Compilando el frontend…"
  ( cd "$RAIZ/frontend" && npm ci && npm run build )
else
  echo "AVISO: npm no está; se sirve el frontend/dist/ existente (o 503 si no hay)."
fi

mkdir -p "$HOME/Library/LaunchAgents" "$(dirname "$LOG")" "$ALMACEN"
sed -e "s|__RUTA__|$RAIZ|g" -e "s|__LOG__|$LOG|g" -e "s|__ALMACEN__|$ALMACEN|g" \
  "$RAIZ/despliegue/$ETIQUETA.plist" > "$DESTINO"

launchctl bootout "gui/$(id -u)/$ETIQUETA" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DESTINO"
launchctl enable "gui/$(id -u)/$ETIQUETA"

sleep 3
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

# Comprobacion real: que el servicio conteste, no solo que launchd lo acepte.
# La primera version de esto salia con EX_CONFIG en cada arranque y el script
# decia "Servicio instalado" igual.
if curl -fsS -o /dev/null --max-time 5 "http://127.0.0.1:8000/"; then
  echo "Servicio instalado y respondiendo. Arranca solo al encender la maquina."
else
  SALIDA=$(launchctl print "gui/$(id -u)/$ETIQUETA" 2>/dev/null | grep -i "last exit code" | tr -d "\t")
  echo "AVISO: el servicio esta registrado pero NO responde en el puerto 8000."
  echo "  $SALIDA"
  echo "  Revisa: $LOG"
  echo "  Si dice 78 (EX_CONFIG), launchd no pudo crear el log: exporta"
  echo "  GPMC_LOG a una ruta fuera de ~/Desktop, ~/Documents y ~/Downloads."
fi
echo
echo "  Manda esta liga al equipo:   http://$IP:8000"
echo
echo "  Ver bitacora:   tail -f '$LOG'"
echo "  Sesiones en:    $ALMACEN"
echo "  Detener:        launchctl bootout gui/$(id -u)/$ETIQUETA"
echo
echo "OJO: la IP cambia si la maquina se reconecta a otra red. Para que la liga"
echo "sea estable, pide a Infraestructura una IP fija o un nombre interno."
