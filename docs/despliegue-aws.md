# Despliegue en AWS

Spec: `docs/superpowers/specs/2026-09-25-despliegue-aws-usuarios-y-auditoria-design.md`.
Región: **mx-central-1** (Querétaro). Todo lo que se crea lleva la etiqueta `Proyecto=gpmc`.

## Una sola vez: entrar al CLI

El documento de accesos trae usuarios de **consola**, no llaves de API. El AWS CLI v2 entra
con ese usuario abriendo el navegador, sin crear llaves:

```
aws configure set region mx-central-1
aws login
```

`aws login` abre la consola; ahí se escribe la contraseña de `admin_coemere` (no se le da a
nadie ni se pega en ningún archivo). Las credenciales temporales quedan en `~/.aws`. Para
comprobar: `aws sts get-caller-identity`.

## Crear la infraestructura, en orden

```
scripts/aws/10-red.sh            grupos de seguridad y llave SSH (~1 min)
scripts/aws/20-base-de-datos.sh  RDS PostgreSQL mínima, cifrada, privada (~10 min)
scripts/aws/30-servidor.sh       EC2 Ubuntu ARM con IP elástica (~3 min)
scripts/aws/40-frontend.sh       S3 privado + CloudFront con dos orígenes (~5 min)
scripts/aws/50-correo-ses.sh     SES: remitente y credenciales SMTP
```

Cada script se puede repetir: encuentra lo que ya existe en vez de duplicarlo. Los
identificadores y secretos quedan en `scripts/aws/estado.env` (permisos 600, fuera de git).

Después de `50-correo-ses.sh` hay dos pasos manuales en la consola de SES: abrir la liga de
verificación que llega al remitente, y **pedir salida del sandbox** para poder mandar a
cualquier `@hidalgo.gob.mx`.

## Desplegar

```
scripts/desplegar.sh          pruebas → SPA a S3 → /etc/gpmc/entorno → backend a la EC2
scripts/desplegar.sh frontend
scripts/desplegar.sh backend
scripts/desplegar.sh entorno  vuelve a escribir las variables en la EC2 (llaves nuevas)
```

Nada se despliega con la suite en rojo. El backend corre como servicio `gpmc` de systemd
(`deploy/gpmc.service`), con las llaves en `/etc/gpmc/entorno` (640, `root:gpmc`). Las
variables de IA se copian de `~/.config/gpmc/entorno` de quien despliega, **sin**
`GPMC_FASE3_PRUEBAS`: en AWS rige el candado de licencia.

## Primer arranque

```
ssh -i ~/.ssh/gpmc-despliegue.pem ubuntu@<IP_SERVIDOR>
sudo -u gpmc -H bash -c 'set -a; . /etc/gpmc/entorno; set +a; /opt/gpmc/.venv/bin/gpmc usuario alta daniel.hernandezr@hidalgo.gob.mx --nombre "Daniel Hernández" --dependencia DGT --rol admin'
```

Luis se registra desde la pantalla y Daniel lo aprueba en «Cuentas».

## Qué cuesta y qué vigilar

- `t4g.small` + `db.t4g.micro` + 30 GB + CloudFront en PriceClass_100: del orden de 30 a 40
  USD al mes. RDS lleva `deletion-protection` y 7 días de respaldo; el disco de la EC2 no se
  borra al terminar la instancia.
- Las sesiones viven en `/var/lib/gpmc/sesiones` de la EC2: conviene un snapshot diario del
  volumen (Data Lifecycle Manager) — pendiente.
- CloudFront llega a la EC2 por HTTP en el puerto 8000; el grupo de seguridad solo admite la
  lista de prefijos de CloudFront, así que nadie más alcanza ese puerto.
