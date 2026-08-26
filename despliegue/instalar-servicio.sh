#!/bin/bash
# Deja el Compilador GPM corriendo siempre, sin ventana de terminal.
# El equipo de Simplificacion solo abre una liga: no instala ni ejecuta nada.
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ETIQUETA="local.gpmc.servidor"
DESTINO="$HOME/Library/LaunchAgents/$ETIQUETA.plist"

echo "Compilador GPM — instalacion del servicio"
echo "  carpeta: $RAIZ"
echo

if [ ! -d "$RAIZ/.venv" ]; then
  echo "Preparando el entorno…"
  python3 -m venv "$RAIZ/.venv"
  "$RAIZ/.venv/bin/pip" install --quiet --upgrade pip
  "$RAIZ/.venv/bin/pip" install --quiet -e "$RAIZ[web]"
fi

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__RUTA__|$RAIZ|g" "$RAIZ/despliegue/$ETIQUETA.plist" > "$DESTINO"

launchctl bootout "gui/$(id -u)/$ETIQUETA" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DESTINO"
launchctl enable "gui/$(id -u)/$ETIQUETA"

sleep 3
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

echo "Servicio instalado. Arranca solo al encender la maquina."
echo
echo "  Manda esta liga al equipo:   http://$IP:8000"
echo
echo "  Ver bitacora:   tail -f '$RAIZ/despliegue/servidor.log'"
echo "  Detener:        launchctl bootout gui/$(id -u)/$ETIQUETA"
echo
echo "OJO: la IP cambia si la maquina se reconecta a otra red. Para que la liga"
echo "sea estable, pide a Infraestructura una IP fija o un nombre interno."
