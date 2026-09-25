#!/usr/bin/env bash
# Correo por SES para la recuperacion de contrasena. SES se usa por su
# interfaz SMTP (el codigo ya habla SMTP: `web/correo.py`), asi que aqui se
# crea un usuario IAM que SOLO puede mandar correo y se derivan sus
# credenciales SMTP de la llave de acceso, con el algoritmo que documenta AWS.
#
# Dos cosas que NO hace un script: (1) el remitente hay que verificarlo —SES
# manda un correo a GPMC_REMITENTE con una liga—, y (2) la cuenta nace en
# «sandbox»: solo manda a direcciones verificadas hasta que se pide acceso a
# produccion desde la consola de SES.
source "$(dirname "$0")/variables.sh"
# SES no existe en mx-central-1 (comprobado el 2026-09-25): el correo sale de
# Virginia. Solo el correo; el resto se queda en Mexico. IAM es global.
SES_REGION="${SES_REGION:-us-east-1}"

# Remitente (identidad). Verificar el dominio entero exige registros DNS en
# hidalgo.gob.mx; una direccion sola basta y la verifica quien lea ese buzon.
aws sesv2 create-email-identity --region "$SES_REGION" --email-identity "$GPMC_REMITENTE" \
  --tags "Key=Proyecto,Value=$GPMC_NOMBRE" >/dev/null 2>&1 && \
  echo "SES mando un correo de verificacion a $GPMC_REMITENTE: hay que abrir la liga." || \
  echo "La identidad $GPMC_REMITENTE ya existe en SES."

USUARIO="$GPMC_NOMBRE-ses-smtp"
if ! aws iam get-user --user-name "$USUARIO" >/dev/null 2>&1; then
  aws iam create-user --user-name "$USUARIO" --tags "Key=Proyecto,Value=$GPMC_NOMBRE" >/dev/null
  aws iam put-user-policy --user-name "$USUARIO" --policy-name solo-enviar-correo --policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ses:SendRawEmail","ses:SendEmail"],"Resource":"*"}]}'
fi

if [ -z "$(leer GPMC_SMTP_CLAVE)" ]; then
  LLAVE=$(aws iam create-access-key --user-name "$USUARIO" --query AccessKey --output json)
  ID=$(printf '%s' "$LLAVE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["AccessKeyId"])')
  SECRETO=$(printf '%s' "$LLAVE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["SecretAccessKey"])')
  # La contrasena SMTP de SES se deriva del secreto (docs de SES, «Obtaining SMTP credentials»).
  SMTP_CLAVE=$(SECRETO="$SECRETO" REGION="$SES_REGION" python3 - <<'EOF'
import base64, hashlib, hmac, os
def firmar(k, m): return hmac.new(k, m.encode("utf-8"), hashlib.sha256).digest()
s = os.environ["SECRETO"]; r = os.environ["REGION"]
k = firmar(("AWS4" + s).encode("utf-8"), "11111111")
for parte in (r, "ses", "aws4_request", "SendRawEmail"):
    k = firmar(k, parte)
print(base64.b64encode(bytes([0x04]) + k).decode("ascii"))
EOF
)
  guardar GPMC_SMTP_HOST "email-smtp.$SES_REGION.amazonaws.com"
  guardar GPMC_SMTP_PUERTO "587"
  guardar GPMC_SMTP_USUARIO "$ID"
  guardar GPMC_SMTP_CLAVE "$SMTP_CLAVE"
  guardar GPMC_SMTP_REMITENTE "$GPMC_REMITENTE"
  echo "Credenciales SMTP de SES guardadas en estado.env."
else
  echo "Las credenciales SMTP ya estaban en estado.env."
fi
guardar GPMC_SMTP_REMITENTE "$GPMC_REMITENTE"   # se puede cambiar de remitente sin regenerar credenciales
echo "Recuerda: pedir salida del sandbox de SES en la consola para mandar a cualquier @$GPMC_DOMINIO_CORREO."
