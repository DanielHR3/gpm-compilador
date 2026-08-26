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
tail -f despliegue/servidor.log                        # bitácora
launchctl bootout gui/$(id -u)/local.gpmc.servidor # detener
./despliegue/instalar-servicio.sh                      # reinstalar tras actualizar
```

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

## Nota técnica

El `plist` fija `PATH` y `PYTHONUNBUFFERED`. Sin ellos el servicio arranca, aparece como
`running` en `launchctl list`, y **nunca se enlaza al puerto** — con la bitácora vacía, que hace
el diagnóstico muy confuso. No quitar esas dos variables.
