#!/usr/bin/env bash
# PostgreSQL en RDS, instancia minima, cifrada, sin acceso publico.
# Solo guarda usuarios, auditoria y recuperaciones (spec 2026-09-25); las
# sesiones siguen en el disco de la EC2.
source "$(dirname "$0")/variables.sh"
SG_BD=$(exige SG_BD)
ID="$GPMC_NOMBRE-bd"

if aws rds describe-db-instances --db-instance-identifier "$ID" >/dev/null 2>&1; then
  echo "La base $ID ya existe."
else
  CLAVE=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-30)
  guardar BD_CLAVE "$CLAVE"
  aws rds create-db-instance --db-instance-identifier "$ID" \
    --engine postgres --engine-version 16 --db-instance-class "$GPMC_RDS_CLASE" \
    --allocated-storage 20 --storage-type gp3 --storage-encrypted \
    --master-username gpmc --master-user-password "$CLAVE" --db-name gpmc \
    --vpc-security-group-ids "$SG_BD" --no-publicly-accessible \
    --backup-retention-period 7 --deletion-protection --auto-minor-version-upgrade \
    --tags "Key=Name,Value=$ID" "Key=Proyecto,Value=$GPMC_NOMBRE" >/dev/null
  echo "Creando $ID (tarda unos 10 minutos)…"
fi
aws rds wait db-instance-available --db-instance-identifier "$ID"
HOST=$(aws rds describe-db-instances --db-instance-identifier "$ID" \
        --query 'DBInstances[0].Endpoint.Address' --output text)
guardar BD_HOST "$HOST"
guardar GPMC_BD "postgresql://gpmc:$(exige BD_CLAVE)@$HOST:5432/gpmc?sslmode=require"
echo "Base lista en $HOST (la cadena de conexion quedo en estado.env)."
