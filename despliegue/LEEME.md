# Despliegue — cómo dejarlo corriendo para el equipo

El equipo de Simplificación **no debe instalar ni ejecutar nada**. Abren una liga y ya.
Para eso, una máquina corre el servicio de forma permanente.

## Instalar

```bash
./despliegue/instalar-servicio.sh
```

Deja el servicio registrado en `launchd`. A partir de ahí:

- Arranca solo al encender la máquina
- Se reinicia solo si se cae (verificado: matando el proceso, vuelve en segundos)
- No hay ventana de terminal que nadie deba dejar abierta

## Operación

```bash
tail -f ~/Library/Logs/gpmc/servidor.log            # bitácora
launchctl bootout gui/$(id -u)/local.gpmc.servidor  # detener
./despliegue/instalar-servicio.sh                   # reinstalar tras actualizar
```

## Dónde vive cada cosa, y por qué fuera del repo

| | Ruta | Por qué ahí |
| --- | --- | --- |
| Bitácora | `~/Library/Logs/gpmc/servidor.log` | **Obligatorio.** Si el repo cuelga de `~/Desktop`, `~/Documents` o `~/Downloads`, macOS no deja que `launchd` cree ahí los archivos de stdout/stderr del trabajo: el servicio muere con `EX_CONFIG` (78) en cada arranque, **sin escribir una sola línea que lo explique**. Lo que el propio proceso escriba después sí funciona; es solo la preparación del trabajo lo que se bloquea |
| Sesiones | `~/Library/Application Support/gpmc/sesiones` | Sin `--almacen` las sesiones son temporales: se pierden al reiniciar, y este servicio tiene `KeepAlive`, o sea que se reinicia solo cuando se cae. Un analista a media revisión perdería su expediente. Fuera del repo, además, actualizar el código no se lleva por delante el trabajo de nadie |

Las dos rutas se pueden cambiar con `GPMC_LOG` y `GPMC_ALMACEN` antes de instalar:

```bash
GPMC_ALMACEN=/ruta/que/prefieras ./despliegue/instalar-servicio.sh
```

## Comprobar que de verdad quedó

El instalador ya no dice «instalado» por el hecho de que `launchd` acepte el
trabajo: hace una petición real al puerto 8000 y, si no contesta, imprime el
código de salida y qué revisar. Para comprobarlo a mano:

```bash
launchctl print gui/$(id -u)/local.gpmc.servidor | grep -E "state|last exit"
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
```

Y que se levanta solo: `kill -9` al pid y volver a pedir la página. Vuelve en
segundos.

## Frontend (SPA React)

Desde SP1 la pantalla de carga y el asistente de huecos son una SPA React que el
servidor sirve **desde `/`** (y `/revisar/{sid}` cae al mismo `index.html`, con
enrutado en el cliente). Esa SPA vive compilada en `frontend/dist/`, que **no se
versiona**: hay que construirla.

- `instalar-servicio.sh` y `Abrir Compilador GPM.command` corren
  `cd frontend && npm ci && npm run build` automáticamente **si hay `npm`**. Si no
  lo hay, avisan y usan el `frontend/dist/` que ya exista (y si no existe ninguno,
  `/` responde `503` con instrucciones).
- Build manual: `cd frontend && npm ci && npm run build`.
- `GPMC_FRONTEND_DIST` — variable de entorno opcional que apunta el servidor a
  otra carpeta `dist/` (por defecto `frontend/dist/` junto al repo). Útil para
  servir un build hecho en otra máquina o ruta.

`/simulador/{sid}`, `/aprobacion/{sid}`, `/historial`, `/vistas/{sid}` y las
descargas siguen siendo HTML del servidor hasta SP3.

## La limitación que hay que resolver

**La liga depende de la IP de la máquina, y esa IP cambia.** Durante estas pruebas cambió de
`192.168.1.181` a `192.168.1.134` en cuestión de minutos, solo por reconexión de red.

Mandarle al equipo una liga que deja de funcionar es peor que no mandarles nada: van a pensar que
la herramienta se descompuso.

**Antes de repartir la liga**, pedir a Infraestructura una de estas dos:

1. **IP fija** para la máquina que hospeda, o
2. **Nombre interno de DNS** (por ejemplo `compilador.dgt.local`), que es lo preferible porque
   sobrevive a un cambio de máquina.

## Dónde debería vivir

Una laptop no es el lugar: se apaga, se lleva a casa, cambia de red. Lo correcto es un servidor
o contenedor interno siempre encendido.

Mientras eso llega, la laptop sirve para que el equipo lo pruebe y dé retroalimentación — pero
sin repartir la liga de forma amplia hasta tener dirección estable.

## Limpieza de sesiones

Cada archivo que sube el equipo deja una carpeta bajo `tempfile.mkdtemp(prefix="gpmc-")`. El
asistente ya **borra solo** las carpetas de sesión sin tocar hace más de 7 días
(`_purgar_sesiones`, al arrancar y en cada `/extraer`), así que no hace falta cron. Si aun así
quieres una red extra en el servidor:

```bash
find "${TMPDIR:-/tmp}"/gpmc-* -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null
```

## Nota técnica

El `plist` fija `PATH` y `PYTHONUNBUFFERED`. Sin ellos el servicio arranca, aparece como
`running` en `launchctl list`, y **nunca se enlaza al puerto** — con la bitácora vacía, que hace
el diagnóstico muy confuso. No quitar esas dos variables.

## Generador de propuestas con IA (opcional)

Sin configurar, el asistente funciona exactamente igual que siempre. Para
activarlo, crea `~/.config/gpmc/entorno` (permisos `600`) con:

```
GPMC_IA_PROVEEDOR=gemini        # o: openai  (licencia de Planeación)
GPMC_IA_LLAVE=...               # la llave del proveedor
# GPMC_IA_MODELO=gemini-2.5-flash
# GPMC_IA_TIMEOUT_S=60
# GPMC_IA_MAX_TOKENS_LOTE=24000
```

`gpmc servir` lo carga al arrancar. **La llave nunca va en el `plist`, ni en el
repositorio, ni en el instalador.** Instala el extra: `pip install -e ".[web,agentes]"`.

La bitácora de interacción con el modelo (campos de la Licencia AI de
Planeación) se escribe, *append-only*, en `<almacén>/bitacora-ia.jsonl`.
Exportar: `gpmc medir-ia CARPETA --exportar salida.jsonl`. No se purga.

**Pruebas con Gemini (AI Studio):** usar `ejemplos/expedientes/`, no los seis
expedientes reales (decisión de la Dirección, 2026-09-17): el nivel de
estudio puede usar los datos para mejorar sus modelos; la licencia de
Planeación con OpenAI garantiza procesamiento transitorio.
