#!/usr/bin/env bash
# Variables y ayudas comunes de los scripts de AWS (spec 2026-09-25).
# Se hace `source` desde cada script; no se ejecuta solo.
#
# Todo lo que se crea lleva el prefijo GPMC_NOMBRE y la etiqueta Proyecto=gpmc,
# para poder encontrarlo (y borrarlo) desde la consola. Los identificadores que
# van saliendo se guardan en `estado.env` (ignorado por git, permisos 600):
# el endpoint de RDS, la IP elastica, el id de la distribucion, la contrasena
# de la base y las credenciales SMTP. Es el unico lugar donde viven.
set -euo pipefail

export AWS_REGION="${AWS_REGION:-mx-central-1}"
export AWS_PAGER=""
export GPMC_NOMBRE="${GPMC_NOMBRE:-gpmc}"
export GPMC_INSTANCIA="${GPMC_INSTANCIA:-t4g.small}"       # ARM: el trabajo pesado lo hace el modelo, no la maquina
export GPMC_RDS_CLASE="${GPMC_RDS_CLASE:-db.t4g.micro}"    # la RDS mas chica («nano»)
export GPMC_REMITENTE="${GPMC_REMITENTE:-compilador-gpm@hidalgo.gob.mx}"
export GPMC_DOMINIO_CORREO="${GPMC_DOMINIO_CORREO:-hidalgo.gob.mx}"

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESTADO="$AQUI/estado.env"
LLAVE_SSH="$HOME/.ssh/${GPMC_NOMBRE}-despliegue.pem"

guardar() {              # guardar CLAVE valor  -> estado.env (reemplaza si ya existe)
  touch "$ESTADO"; chmod 600 "$ESTADO"
  grep -v "^$1=" "$ESTADO" > "$ESTADO.tmp" || true
  printf '%s=%s\n' "$1" "$2" >> "$ESTADO.tmp"
  mv "$ESTADO.tmp" "$ESTADO"
}
leer() {                 # leer CLAVE -> valor o vacio
  [ -f "$ESTADO" ] && grep "^$1=" "$ESTADO" | tail -1 | cut -d= -f2- || true
}
exige() {                # exige CLAVE: aborta si no esta en estado.env
  local v; v="$(leer "$1")"
  [ -n "$v" ] || { echo "Falta $1 en estado.env: corre antes el script que lo crea." >&2; exit 2; }
  printf '%s' "$v"
}
cuenta() { aws sts get-caller-identity --query Account --output text; }
etiquetas() {            # etiquetas TIPO Nombre -> --tag-specifications
  printf 'ResourceType=%s,Tags=[{Key=Name,Value=%s},{Key=Proyecto,Value=%s}]' "$1" "$2" "$GPMC_NOMBRE"
}

echo "Region: $AWS_REGION · cuenta: $(cuenta) · prefijo: $GPMC_NOMBRE"
