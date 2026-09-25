#!/usr/bin/env bash
# La SPA en S3 (privado) detras de CloudFront, y la misma distribucion con un
# segundo origen —la EC2— para todo lo que atiende el backend. Sin CORS: la
# SPA sigue llamando a `/api/...` en su propio dominio, y la CSP
# `default-src 'self'` sigue valida.
#
# Las rutas de la SPA (`/revisar/xxxx`, `/registro`…) no existen en S3: una
# CloudFront Function en el comportamiento por omision reescribe a
# /index.html todo lo que no tiene extension. Se hace asi y NO con «custom
# error responses» porque esas aplican a toda la distribucion y convertirian
# un 404 JSON del backend en un index.html con 200.
source "$(dirname "$0")/variables.sh"
DNS=$(exige DNS_SERVIDOR)
BUCKET="$GPMC_NOMBRE-frontend-$(cuenta)"
guardar BUCKET "$BUCKET"

# --- S3 privado
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [ "$AWS_REGION" = "us-east-1" ]; then aws s3api create-bucket --bucket "$BUCKET" >/dev/null
  else aws s3api create-bucket --bucket "$BUCKET" --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null; fi
fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# --- OAC (CloudFront lee el bucket firmando; el bucket no es publico)
OAC=$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='$GPMC_NOMBRE-oac'].Id | [0]" --output text)
if [ -z "$OAC" ] || [ "$OAC" = "None" ]; then
  OAC=$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=$GPMC_NOMBRE-oac,OriginAccessControlOriginType=s3,SigningBehavior=always,SigningProtocol=sigv4" \
    --query OriginAccessControl.Id --output text)
fi

# --- CloudFront Function: rutas de la SPA -> /index.html (solo en el origen S3)
FN_NOMBRE="$GPMC_NOMBRE-spa"
FN_CODIGO='function handler(event) {
  var uri = event.request.uri;
  if (uri === "/" || uri.indexOf(".") === -1) { event.request.uri = "/index.html"; }
  return event.request;
}'
# El CLI quiere el codigo como archivo binario (fileb://), no como texto.
FN_ARCHIVO=$(mktemp); printf '%s' "$FN_CODIGO" > "$FN_ARCHIVO"; trap 'rm -f "$FN_ARCHIVO"' EXIT
FN_ETAG=$(aws cloudfront describe-function --name "$FN_NOMBRE" --query ETag --output text 2>/dev/null || true)
if [ -z "$FN_ETAG" ]; then
  aws cloudfront create-function --name "$FN_NOMBRE" --function-code "fileb://$FN_ARCHIVO" \
    --function-config "Comment=Compilador GPM: rutas de la SPA,Runtime=cloudfront-js-2.0" >/dev/null
else
  aws cloudfront update-function --name "$FN_NOMBRE" --function-code "fileb://$FN_ARCHIVO" --if-match "$FN_ETAG" \
    --function-config "Comment=Compilador GPM: rutas de la SPA,Runtime=cloudfront-js-2.0" >/dev/null
fi
FN_ETAG=$(aws cloudfront describe-function --name "$FN_NOMBRE" --query ETag --output text)
aws cloudfront publish-function --name "$FN_NOMBRE" --if-match "$FN_ETAG" >/dev/null
FN_ARN=$(aws cloudfront describe-function --name "$FN_NOMBRE" --stage LIVE --query FunctionSummary.FunctionMetadata.FunctionARN --output text)

# --- Distribucion: dos origenes, comportamientos por prefijo del backend
CACHE_OPTIMIZADO="658327ea-f89d-4fab-a63d-7e88639e58f6"   # politicas administradas por AWS
CACHE_APAGADO="4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
PETICION_TODO="216adef6-5c7f-47e4-b989-5492eafa07d3"      # AllViewer: cookies, cabeceras y consulta al backend
comportamiento() {
  printf '{"PathPattern":"%s","TargetOriginId":"backend","ViewerProtocolPolicy":"redirect-to-https","AllowedMethods":{"Quantity":7,"Items":["GET","HEAD","OPTIONS","PUT","PATCH","POST","DELETE"],"CachedMethods":{"Quantity":2,"Items":["GET","HEAD"]}},"Compress":true,"CachePolicyId":"%s","OriginRequestPolicyId":"%s"}' "$1" "$CACHE_APAGADO" "$PETICION_TODO"
}
COMPORTAMIENTOS=""
for p in "/api/*" "/simulador/*" "/aprobacion/*" "/historial" "/vistas/*" "/descargar/*" "/descargar-plantilla*" "/extraer" "/resolver/*" "/reconocer/*"; do
  COMPORTAMIENTOS="$COMPORTAMIENTOS,$(comportamiento "$p")"
done
COMPORTAMIENTOS="${COMPORTAMIENTOS#,}"
N=$(printf '%s' "$COMPORTAMIENTOS" | grep -o '"PathPattern"' | wc -l | tr -d ' ')

CONFIG=$(cat <<EOF
{
  "CallerReference": "$GPMC_NOMBRE-$(date +%s)",
  "Comment": "Compilador GPM",
  "Enabled": true,
  "HttpVersion": "http2and3",
  "PriceClass": "PriceClass_100",
  "DefaultRootObject": "index.html",
  "Origins": {"Quantity": 2, "Items": [
    {"Id": "spa", "DomainName": "$BUCKET.s3.$AWS_REGION.amazonaws.com", "OriginAccessControlId": "$OAC",
     "S3OriginConfig": {"OriginAccessIdentity": ""}},
    {"Id": "backend", "DomainName": "$DNS",
     "CustomOriginConfig": {"HTTPPort": 8000, "HTTPSPort": 443, "OriginProtocolPolicy": "http-only",
                            "OriginReadTimeout": 60, "OriginKeepaliveTimeout": 5}}
  ]},
  "DefaultCacheBehavior": {
    "TargetOriginId": "spa", "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"], "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
    "Compress": true, "CachePolicyId": "$CACHE_OPTIMIZADO",
    "FunctionAssociations": {"Quantity": 1, "Items": [{"FunctionARN": "$FN_ARN", "EventType": "viewer-request"}]}
  },
  "CacheBehaviors": {"Quantity": $N, "Items": [$COMPORTAMIENTOS]},
  "ViewerCertificate": {"CloudFrontDefaultCertificate": true, "MinimumProtocolVersion": "TLSv1.2_2021"}
}
EOF
)
DIST=$(leer DISTRIBUCION)
if [ -z "$DIST" ]; then
  DIST=$(aws cloudfront create-distribution --distribution-config "$CONFIG" --query Distribution.Id --output text)
  guardar DISTRIBUCION "$DIST"
  echo "Distribucion $DIST creada (tarda unos minutos en desplegarse)."
else
  echo "La distribucion $DIST ya existe; para cambiar comportamientos, edita en la consola o borra DISTRIBUCION de estado.env."
fi
DOMINIO=$(aws cloudfront get-distribution --id "$DIST" --query Distribution.DomainName --output text)
guardar DOMINIO_CLOUDFRONT "$DOMINIO"

# --- El bucket solo lo lee esta distribucion
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{\"Sid\": \"CloudFront\", \"Effect\": \"Allow\", \"Principal\": {\"Service\": \"cloudfront.amazonaws.com\"},
    \"Action\": \"s3:GetObject\", \"Resource\": \"arn:aws:s3:::$BUCKET/*\",
    \"Condition\": {\"StringEquals\": {\"AWS:SourceArn\": \"arn:aws:cloudfront::$(cuenta):distribution/$DIST\"}}}]}"
echo "Frontend: https://$DOMINIO (S3 $BUCKET, distribucion $DIST)"
