#!/usr/bin/env bash
# Red y seguridad: VPC por omision, dos grupos de seguridad y la llave SSH.
#
# - `backend`: el puerto del asistente (8000) SOLO desde CloudFront (lista de
#   prefijos administrada por AWS) y SSH solo desde la IP de quien despliega.
#   La EC2 no queda expuesta a internet aunque tenga IP publica.
# - `bd`: Postgres (5432) SOLO desde el grupo `backend`.
source "$(dirname "$0")/variables.sh"

VPC=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
[ "$VPC" != "None" ] || { echo "La cuenta no tiene VPC por omision en $AWS_REGION; hay que crear una." >&2; exit 2; }
guardar VPC "$VPC"
SUBRED=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true \
          --query 'Subnets[0].SubnetId' --output text)
guardar SUBRED "$SUBRED"

sg_o_crear() {   # sg_o_crear nombre descripcion -> id
  local id
  id=$(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" Name=group-name,Values="$1" \
        --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
  if [ -z "$id" ] || [ "$id" = "None" ]; then
    id=$(aws ec2 create-security-group --vpc-id "$VPC" --group-name "$1" --description "$2" \
          --tag-specifications "$(etiquetas security-group "$1")" --query GroupId --output text)
  fi
  printf '%s' "$id"
}

SG_BACKEND=$(sg_o_crear "$GPMC_NOMBRE-backend" "Compilador GPM: backend, solo CloudFront y SSH")
SG_BD=$(sg_o_crear "$GPMC_NOMBRE-bd" "Compilador GPM: PostgreSQL, solo desde el backend")
guardar SG_BACKEND "$SG_BACKEND"; guardar SG_BD "$SG_BD"

# CloudFront -> backend. La lista de prefijos es global y la mantiene AWS.
PL_CLOUDFRONT=$(aws ec2 describe-managed-prefix-lists \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query 'PrefixLists[0].PrefixListId' --output text)
aws ec2 authorize-security-group-ingress --group-id "$SG_BACKEND" \
  --ip-permissions "IpProtocol=tcp,FromPort=8000,ToPort=8000,PrefixListIds=[{PrefixListId=$PL_CLOUDFRONT,Description=CloudFront}]" \
  2>/dev/null || echo "  (8000 desde CloudFront ya estaba)"

# SSH solo desde quien despliega. Se puede repetir con otra IP: agrega, no quita.
MI_IP="${GPMC_SSH_CIDR:-$(curl -s https://checkip.amazonaws.com)/32}"
aws ec2 authorize-security-group-ingress --group-id "$SG_BACKEND" \
  --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=$MI_IP,Description=despliegue}]" \
  2>/dev/null || echo "  (22 desde $MI_IP ya estaba)"

# Postgres solo desde el backend.
aws ec2 authorize-security-group-ingress --group-id "$SG_BD" \
  --ip-permissions "IpProtocol=tcp,FromPort=5432,ToPort=5432,UserIdGroupPairs=[{GroupId=$SG_BACKEND,Description=backend}]" \
  2>/dev/null || echo "  (5432 desde el backend ya estaba)"

# Llave SSH: se crea una vez y el .pem queda solo en esta maquina (600).
if ! aws ec2 describe-key-pairs --key-names "$GPMC_NOMBRE-despliegue" >/dev/null 2>&1; then
  aws ec2 create-key-pair --key-name "$GPMC_NOMBRE-despliegue" --key-type ed25519 \
    --tag-specifications "$(etiquetas key-pair "$GPMC_NOMBRE-despliegue")" \
    --query KeyMaterial --output text > "$LLAVE_SSH"
  chmod 600 "$LLAVE_SSH"
  echo "Llave SSH guardada en $LLAVE_SSH"
elif [ ! -f "$LLAVE_SSH" ]; then
  echo "La llave $GPMC_NOMBRE-despliegue existe en AWS pero no esta en $LLAVE_SSH: recuperala o borrala en la consola." >&2
  exit 2
fi
echo "Red lista: VPC $VPC · backend $SG_BACKEND · bd $SG_BD"
