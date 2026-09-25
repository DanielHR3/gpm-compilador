#!/usr/bin/env bash
# Despliegue a AWS (spec 2026-09-25). Nada se despliega sin la suite en verde.
#
#   scripts/desplegar.sh            todo: pruebas, frontend a S3, backend a la EC2
#   scripts/desplegar.sh frontend   solo la SPA
#   scripts/desplegar.sh backend    solo el servidor
#   scripts/desplegar.sh entorno    (re)escribe /etc/gpmc/entorno en la EC2 desde estado.env
#
# El backend viaja por rsync (sin .venv, node_modules ni dist) y se instala
# con pip en su propio venv; el servicio es deploy/gpmc.service.
set -euo pipefail
QUE="${1:-todo}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
source "$RAIZ/scripts/aws/variables.sh"
IP=$(exige IP_SERVIDOR); SSH="ssh -i $LLAVE_SSH -o StrictHostKeyChecking=accept-new ubuntu@$IP"

pruebas() {
  echo "== Pruebas"
  (cd "$RAIZ" && .venv/bin/pytest -q)
  (cd "$RAIZ" && bash scripts/check-frontend.sh)
}

frontend() {
  echo "== Frontend -> S3 + CloudFront"
  BUCKET=$(exige BUCKET); DIST=$(exige DISTRIBUCION)
  # Los assets llevan hash: inmutables un ano. El shell se revalida siempre.
  aws s3 sync "$RAIZ/frontend/dist/assets" "s3://$BUCKET/assets" --delete --cache-control "public, max-age=31536000, immutable"
  aws s3 sync "$RAIZ/frontend/dist" "s3://$BUCKET" --exclude "assets/*" --delete --cache-control "no-cache"
  aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/index.html" "/" >/dev/null
  echo "Frontend en https://$(exige DOMINIO_CLOUDFRONT)"
}

entorno() {
  echo "== /etc/gpmc/entorno en la EC2"
  # Lo de IA viene del archivo local del usuario (GPMC_IA_*), lo demas de estado.env.
  local ia; ia=$(grep -E '^GPMC_IA_' "$HOME/.config/gpmc/entorno" 2>/dev/null || true)
  [ -n "$ia" ] || { echo "No hay GPMC_IA_* en ~/.config/gpmc/entorno" >&2; exit 2; }
  local jwt; jwt=$(leer GPMC_JWT_SECRETO)
  [ -n "$jwt" ] || { jwt=$(openssl rand -hex 32); guardar GPMC_JWT_SECRETO "$jwt"; }
  {
    echo "# Generado por scripts/desplegar.sh el $(date -u +%FT%TZ). No editar a mano: se regenera."
    echo "$ia"
    echo "GPMC_JWT_SECRETO=$jwt"
    echo "GPMC_BD=$(exige GPMC_BD)"
    echo "GPMC_DOMINIO_CORREO=$GPMC_DOMINIO_CORREO"
    for k in GPMC_SMTP_HOST GPMC_SMTP_PUERTO GPMC_SMTP_USUARIO GPMC_SMTP_CLAVE GPMC_SMTP_REMITENTE; do
      v=$(leer "$k"); [ -n "$v" ] && echo "$k=$v"
    done
    echo "GPMC_LOG_NIVEL=INFO"
    # Modo de pruebas de la Fase 3 en AWS: solo si la Direccion lo autorizo
    # (decision de Daniel, 2026-09-25: `guardar GPMC_FASE3_PRUEBAS 1` en estado.env).
    # Con Gemini en nivel gratuito, los expedientes reales pueden usarse para entrenar.
    [ "$(leer GPMC_FASE3_PRUEBAS)" = "1" ] && echo "GPMC_FASE3_PRUEBAS=1"
  } | $SSH "sudo install -m 640 -o root -g gpmc /dev/stdin /etc/gpmc/entorno"
  if [ "$(leer GPMC_FASE3_PRUEBAS)" = "1" ]; then echo "Entorno escrito CON modo de pruebas de la Fase 3 (Gemini sobre expedientes reales)."
  else echo "Entorno escrito (sin GPMC_FASE3_PRUEBAS: rige el candado de licencia)."; fi
}

backend() {
  echo "== Backend -> EC2 $IP"
  rsync -rlptz --omit-dir-times --delete -e "ssh -i $LLAVE_SSH -o StrictHostKeyChecking=accept-new" \
    --exclude .venv --exclude node_modules --exclude frontend/dist --exclude .git \
    --exclude '__pycache__' --exclude '.pytest_cache' --exclude 'scripts/aws/estado.env' \
    "$RAIZ/" "ubuntu@$IP:/opt/gpmc/"
  $SSH bash -s <<'EOF'
set -euo pipefail
cd /opt/gpmc
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e '.[web,agentes]'
sudo install -m 644 deploy/gpmc.service /etc/systemd/system/gpmc.service
sudo systemctl daemon-reload
sudo systemctl enable gpmc >/dev/null
sudo systemctl restart gpmc
sleep 3
systemctl is-active gpmc
curl -s -o /dev/null -w 'backend local: %{http_code}\n' http://127.0.0.1:8000/api/v1/capacidades
EOF
}

case "$QUE" in
  todo)     pruebas; frontend; entorno; backend ;;
  frontend) (cd "$RAIZ" && bash scripts/check-frontend.sh); frontend ;;
  backend)  (cd "$RAIZ" && .venv/bin/pytest -q); backend ;;
  entorno)  entorno; $SSH sudo systemctl restart gpmc ;;
  *) echo "uso: $0 [todo|frontend|backend|entorno]" >&2; exit 2 ;;
esac
