#!/usr/bin/env bash
# La EC2 del backend: Ubuntu 24.04 ARM, disco cifrado, IP elastica (para que
# la liga y el origen de CloudFront no cambien al reiniciar) y un user-data
# que deja la maquina lista para `desplegar.sh`: Python, rsync, el usuario
# `gpmc` y las carpetas del almacen y los logs.
source "$(dirname "$0")/variables.sh"
SG_BACKEND=$(exige SG_BACKEND); SUBRED=$(exige SUBRED)
NOMBRE="$GPMC_NOMBRE-servidor"

AMI=$(aws ssm get-parameter --query Parameter.Value --output text \
  --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id)

INSTANCIA=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=$NOMBRE" "Name=instance-state-name,Values=pending,running,stopped" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null || true)

if [ -z "$INSTANCIA" ] || [ "$INSTANCIA" = "None" ]; then
  USER_DATA=$(cat <<'EOF'
#!/bin/bash
set -eux
apt-get update
apt-get install -y python3 python3-venv python3-pip rsync git
id -u gpmc >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash gpmc
mkdir -p /opt/gpmc /var/lib/gpmc/sesiones /var/log/gpmc /etc/gpmc
chown -R gpmc:gpmc /var/lib/gpmc /var/log/gpmc
chown root:gpmc /etc/gpmc
chmod 750 /etc/gpmc
# El codigo lo escribe ubuntu (rsync del despliegue) y lo lee el servicio (gpmc).
chown -R ubuntu:gpmc /opt/gpmc
chmod 755 /opt/gpmc
EOF
)
  INSTANCIA=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$GPMC_INSTANCIA" \
    --key-name "$GPMC_NOMBRE-despliegue" --security-group-ids "$SG_BACKEND" --subnet-id "$SUBRED" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=30,VolumeType=gp3,Encrypted=true,DeleteOnTermination=false}' \
    --metadata-options HttpTokens=required \
    --user-data "$USER_DATA" \
    --tag-specifications "$(etiquetas instance "$NOMBRE")" "$(etiquetas volume "$NOMBRE")" \
    --query 'Instances[0].InstanceId' --output text)
  echo "Creando ${INSTANCIA}…"
fi
guardar INSTANCIA "$INSTANCIA"
aws ec2 wait instance-running --instance-ids "$INSTANCIA"

# IP elastica: una sola por servidor; se reutiliza si ya la tiene.
EIP_ALLOC=$(aws ec2 describe-addresses --filters "Name=tag:Name,Values=$NOMBRE" \
  --query 'Addresses[0].AllocationId' --output text 2>/dev/null || true)
if [ -z "$EIP_ALLOC" ] || [ "$EIP_ALLOC" = "None" ]; then
  EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --tag-specifications "$(etiquetas elastic-ip "$NOMBRE")" \
    --query AllocationId --output text)
fi
aws ec2 associate-address --instance-id "$INSTANCIA" --allocation-id "$EIP_ALLOC" --allow-reassociation >/dev/null
IP=$(aws ec2 describe-addresses --allocation-ids "$EIP_ALLOC" --query 'Addresses[0].PublicIp' --output text)
guardar IP_SERVIDOR "$IP"
# El nombre DNS publico de la EIP es el origen de CloudFront (a CloudFront no se le da una IP).
DNS=$(aws ec2 describe-instances --instance-ids "$INSTANCIA" --query 'Reservations[0].Instances[0].PublicDnsName' --output text)
guardar DNS_SERVIDOR "$DNS"
echo "Servidor $INSTANCIA en $IP ($DNS). SSH: ssh -i $LLAVE_SSH ubuntu@$IP"
