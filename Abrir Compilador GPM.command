#!/bin/bash
# Doble clic para abrir el Compilador GPM.
# Usa el Python que ya trae macOS: no hay que instalar nada.
cd "$(dirname "$0")" || exit 1

echo "──────────────────────────────────────────────"
echo "  Compilador GPM — Dirección de Gestión Tecnológica"
echo "──────────────────────────────────────────────"
echo

if [ ! -d ".venv" ]; then
  echo "Primera vez: preparando el entorno (tarda ~1 minuto)…"
  python3 -m venv .venv || { echo "No se pudo crear el entorno."; read -r; exit 1; }
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -e '.[web]' || { echo "Falló la instalación."; read -r; exit 1; }
  echo "Listo."
  echo
fi

PUERTO=8000
while lsof -ti:$PUERTO >/dev/null 2>&1; do PUERTO=$((PUERTO+1)); done

echo "Abriendo en http://127.0.0.1:$PUERTO"
echo "Para cerrar: presiona Ctrl+C en esta ventana."
echo

( sleep 2 && open "http://127.0.0.1:$PUERTO" ) &
.venv/bin/gpmc servir --puerto $PUERTO
