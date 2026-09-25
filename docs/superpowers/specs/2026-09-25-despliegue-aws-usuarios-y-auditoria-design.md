# Despliegue en AWS, usuarios con JWT y bitácora de acciones — diseño

**Fecha:** 2026-09-25
**Estado:** decisiones tomadas por la DGT (Daniel) y la DSA (Luis) el 2026-09-25; sin implementar
**Depende de:** nada del código; sí de la cuenta de AWS y de los correos institucionales

## Propósito

Sacar el asistente de la Mac de Daniel, donde hoy corre por launchd y solo llega a quien
esté en su misma red (y no siempre: el 2026-09-25 un compañero en la misma red no pudo
abrirlo desde su navegador), y ponerlo en AWS con **usuarios identificados** y un **registro de
quién hizo qué**, porque los expedientes traen datos de ciudadanos.

## Lo que se decidió y por qué

| Decisión | Alternativa descartada | Motivo |
| --- | --- | --- |
| Backend FastAPI en una **EC2**; frontend en **S3** expuesto por **CloudFront** | Todo en la EC2 (como hoy en la Mac) | Propuesta de la DSA; la SPA ya es estática y el backend ya es funciones sobre archivos |
| **Una sola distribución de CloudFront con dos orígenes**: S3 para `/`, la EC2 para `/api/*`, `/simulador/*`, `/aprobacion/*`, `/historial`, `/vistas/*`, `/descargar*`, `/extraer`, `/resolver`, `/reconocer` | Backend en otro dominio con CORS | Sin CORS no se toca la SPA ni la CSP `default-src 'self'`; la EC2 no queda expuesta directo a internet (grupo de seguridad solo para CloudFront) |
| **Autenticación JWT** en FastAPI | Sin autenticación (hoy) | Con el asistente en internet, el `sid` en la URL ya no basta |
| **Variables de entorno** para las llaves (IA, firma del JWT) | Secrets Manager / SSM | Decisión del usuario; `cargar_entorno` ya lee primero el entorno del proceso. En la EC2 van en el `EnvironmentFile` de systemd con permisos 600 |
| **PostgreSQL en RDS**, instancia mínima («nano»), con **dos tablas**: `usuarios` y `auditoria`. Nada de SQLite (decisión del usuario, 2026-09-25) | SQLite en EBS; MySQL; DynamoDB; mover las sesiones a base de datos | Las sesiones, `bitacora-ia.jsonl` y `tablero.jsonl` siguen en archivos sobre EBS: una sola instancia, escritura atómica ya hecha, cero migración |
| **Bitácora de acciones** («quién hizo qué») en la tabla `auditoria` | Solo la bitácora de IA | La de IA registra llamadas al modelo; lo que pide la Dirección son las acciones de personas |
| Usuarios de arranque: **Daniel (DGT)** `daniel.hernandezr@hidalgo.gob.mx` y **Luis (DSA)** `luis.vera@hidalgo.gob.mx` (confirmado el 2026-09-25), identificados por correo institucional | Cognito | Dos usuarios no justifican Cognito; se puede migrar después sin tocar la API |

## Lo que no cambia

El compilador, el extractor, los agentes, el validador y sus pruebas. El servidor no guarda
estado en memoria, así que se mueve tal cual. La regla «sin base de datos» del `CLAUDE.md` se
mantiene para el **núcleo**: la base nano es de la capa `web`, y solo para usuarios y
auditoría.

## Diseño

### 1. Usuarios y JWT (se puede hacer hoy, sin AWS)

- Acceso por `psycopg` (extra `[web]`), SQL plano, sin ORM: dos tablas no lo justifican. Un
  almacén en memoria con el mismo contrato sirve a las pruebas (como `ProveedorFalso`); las
  pruebas contra Postgres real corren solo con `GPMC_BD_PRUEBAS` puesto, como las de material real.
- Tabla `usuarios`: `correo` (único), `nombre`, `dependencia` (`DGT` | `DSA` | …),
  `hash_contrasena` (argon2 o bcrypt), `activo`, `creado`.
- `POST /api/v1/sesion` con correo y contraseña → JWT firmado con `GPMC_JWT_SECRETO`
  (variable de entorno), vigencia 8 h, con `sub` = correo y `dependencia` en el cuerpo.
- Dependencia de FastAPI `usuario_actual` en **todas** las rutas salvo `/api/v1/sesion` y
  `/api/v1/capacidades`. Las páginas del servidor (`/simulador/{sid}`, `/aprobacion/{sid}`,
  descargas) también la exigen: el token viaja en una cookie `HttpOnly` además de la cabecera,
  porque esas páginas se abren con un enlace, no con `fetch`.
- La SPA: pantalla de entrada, guarda el token, lo manda en cada llamada, y muestra el nombre y
  la dependencia en la barra. Un 401 vuelve a la entrada sin perder la ruta.
- Alta de usuarios por CLI: `gpmc usuario alta <correo> --nombre --dependencia`, que pide la
  contraseña en la terminal. Sin pantalla de administración por ahora.
- Sin `GPMC_JWT_SECRETO` el servidor **no arranca** (no hay modo «sin autenticación» que se
  pueda olvidar encendido).

### 2. Bitácora de acciones

- Tabla `auditoria`: `id`, `fecha` (UTC), `usuario` (correo), `dependencia`, `accion`,
  `sid`, `detalle` (texto corto), `ip`.
- Una sola función `auditar(usuario, accion, sid, detalle)` llamada desde las rutas que cambian
  algo o entregan algo:

  | Acción | Ruta |
  | --- | --- |
  | `expediente.subir` | `POST /extraer`, `POST /api/v1/expedientes` |
  | `as_is.proponer` | `POST /api/v1/expedientes/proponer` |
  | `propuesta.decidir` (aceptada / corregida / declinada) | `…/generados/{documento}/decision` |
  | `propuesta.subir` | `…/generados/{documento}/subir` |
  | `hueco.resolver` | `POST /resolver` |
  | `hueco.reconocer` | `POST /reconocer` |
  | `propuesta_ia.decidir` | decisión sobre una propuesta de `DIC-08` |
  | `gpm.descargar` | `GET /descargar/{sid}/gpm` y `…/gpm-pruebas` |
  | `sesion.entrar` / `sesion.fallo` | `POST /api/v1/sesion` |

- `GET /api/v1/auditoria?sid=&usuario=&desde=` para consultarla; en la SPA, una pestaña en el
  historial. Solo lectura; nadie borra filas.
- `bitacora-ia.jsonl` deja de decir `usuario: "anonimo"`: recibe el correo del token.

### 3. Infraestructura (con AWS CLI, cuando estén los accesos)

- **EC2** pequeña (t4g.small basta: el trabajo pesado lo hace el modelo, no la instancia),
  Ubuntu, `gpmc servir` bajo systemd con `Restart=always`, almacén en un volumen **EBS cifrado**
  aparte, con snapshot diario. Grupo de seguridad: solo el puerto del backend desde la lista de
  prefijos de CloudFront, y SSH solo desde las IP de la DGT y la DSA.
- **S3** privado con `frontend/dist/`; CloudFront con OAC, certificado de ACM, HTTPS forzado,
  comportamiento por defecto a S3 y comportamientos por prefijo a la EC2 (sin caché en los del
  backend; los assets con hash ya llevan `immutable`).
- **Región:** la que autorice la Dirección para datos de ciudadanos; cifrado en reposo en EBS,
  S3 y la base.
- **Despliegue:** un script `scripts/desplegar.sh` que corre la suite, construye el frontend,
  sube `dist/` a S3, invalida CloudFront y reinicia el servicio en la EC2 por SSH. Nada se
  despliega sin la suite en verde (regla del `CLAUDE.md`).
- **Variables de entorno en la EC2:** `GPMC_IA_PROVEEDOR`, `GPMC_IA_LLAVE`, `GPMC_IA_MODELO`,
  `GPMC_IA_TIMEOUT_S`, `GPMC_JWT_SECRETO`, `GPMC_BD` (cadena de conexión), y **sin**
  `GPMC_FASE3_PRUEBAS` cuando lleguen las credenciales de OpenAI.

## Cambio del 2026-09-25 (tarde): superusuario, registro y recuperación

Decisiones nuevas del usuario, que sustituyen «altas solo por terminal»:

| Decisión | Alternativa descartada | Motivo |
| --- | --- | --- |
| **Rol `admin` (superusuario) y `analista`**; Daniel es el superusuario | Un solo tipo de cuenta | Alguien tiene que aprobar cuentas y cambiar roles sin entrar a la terminal |
| **Hoja de registro** que solo admite `@hidalgo.gob.mx` (`GPMC_DOMINIO_CORREO`) y deja la cuenta **pendiente** hasta que el superusuario la aprueba | Activación por verificación de correo | No exige enviar correos y nadie entra sin visto bueno |
| **Recuperación por liga de correo**, un solo uso, caduca en 1 h | Restablecimiento por el superusuario | Elegida por el usuario; el envío va por SMTP (`GPMC_SMTP_*`), que sirve para SES y para el SMTP de Hidalgo, aún por decidir. Sin SMTP el asistente lo dice y la liga queda en el log |
| Pantalla «Cuentas» en la SPA para el superusuario | Solo `gpmc usuario` | Es la tarea diaria de aprobar |

Tablas nuevas: `recuperaciones` (hash del token, correo, expira, usado). Columnas nuevas en
`usuarios`: `rol`, `estado` (`pendiente` · `activo` · `inactivo`). Acciones nuevas en la auditoría:
`usuario.registro`, `usuario.aprobar`, `usuario.desactivar`, `usuario.rol`, `recuperacion.pedir`,
`recuperacion.restablecer`. Rutas públicas: `POST /api/v1/registro`, `/recuperar`, `/restablecer`;
solo admin: `GET/POST /api/v1/usuarios…` (403 para un analista; nadie se desactiva a sí mismo).
Pendiente: decidir SES o SMTP institucional y sus credenciales (`GPMC_SMTP_HOST`, `_PUERTO`,
`_USUARIO`, `_CLAVE`, `_REMITENTE`).

## Pendientes que esta decisión destapa

- **SP3**: el simulador y la aprobación siguen siendo HTML del servidor. Con CloudFront basta
  con enrutarlas a la EC2, pero cada una exige el token por cookie; pasarlas a la SPA lo
  simplificaría. No bloquea.
- `_purgar_sesiones` borra sesiones sin tocar a los 7 días; con usuarios reales conviene que
  la auditoría conserve la fila aunque la carpeta ya no exista (ya es así: son tablas
  distintas).
- La liga `/revisar/{sid}` se comparte por chat: con JWT, quien la abra sin sesión entra
  primero y luego aterriza en ella.

## Orden de trabajo

1. Usuarios, JWT y la tabla de auditoría en FastAPI, con pruebas (sin AWS; se prueba en la
   Mac).
2. Pantalla de entrada y token en la SPA; usuario real en la bitácora de IA.
3. Cuenta de AWS: EC2 + EBS, S3 + CloudFront, base nano, script de despliegue.
4. Alta de Daniel y Luis; primera prueba desde fuera de la red de la DGT.
