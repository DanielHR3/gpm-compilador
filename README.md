# Compilador GPM

Convierte los insumos de reingeniería de un trámite —Análisis AS-IS, Propuesta TO-BE y
Diccionario de Datos, en markdown— en un archivo `.gpm` importable en una plataforma de modelado
BPMN.

Escrito para el equipo de la Dirección de Gestión Tecnológica.

## Instalar

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[web]'
```

Requiere Python 3.9 o superior, que es el que trae macOS. El núcleo y la CLI no necesitan nada
más. Dos extras opcionales: `[agentes]` para el generador de propuestas con modelo de lenguaje
—su configuración está en `despliegue/LEEME.md`— y `[guia]` para regenerar los PDF de
`docs/guias/`.

### El asistente web hay que compilarlo

La interfaz es una SPA (Vite + React) y `frontend/dist/` **no se comitea**. Sin ese build,
`gpmc servir` levanta la API pero `/` responde `503`:

```bash
cd frontend && npm install && npm run build   # deja frontend/dist/
```

Node y npm hacen falta **solo para el build**: el servicio en marcha no los usa. Para
desarrollar, `npm run dev` (:5173, con proxy de `/api` al :8000) junto a `gpmc servir`
(:8000). `bash scripts/check-frontend.sh` corre tipos, pruebas y build de una vez.

## Asistente web

```bash
gpmc servir
```

Abre `http://127.0.0.1:8000`. Se elige la carpeta del trámite —o los archivos uno a uno— y el
asistente los reparte entre AS-IS, TO-BE, Diccionario y documentos de salida; ante un empate
real deja la zona vacía y dice por qué, en vez de adivinar. Los insumos valen en `.md`, `.docx`
o PDF con texto, y entre dos candidatos para la misma zona gana el que el extractor lee mejor.
De ahí salen el `.gpm`, el manifiesto, el simulador y el reporte de huecos.

## Uso por terminal

```bash
# Del expediente a un manifiesto YAML
gpmc extraer ruta/al/expediente -o tramite.yaml
gpmc extraer ruta/al/expediente -o tramite.yaml --estricto  # no escribe si quedan huecos que bloquean

# Revisar y corregir a mano los huecos que reporte el paso anterior

gpmc estimar  tramite.yaml                   # complejidad y tiempo de ciclo
gpmc simular  tramite.yaml -o simulador.html # recorrer el trámite
gpmc aprobar  tramite.yaml -o aprobacion.html # HTML para que firme la dependencia
gpmc compilar tramite.yaml -o tramite.gpm    # archivo importable
gpmc compilar --desde-expediente ruta/al/expediente -o tramite.gpm  # re-extrae y aplica la puerta del linter
gpmc validar  otro.gpm                       # revisar uno existente
gpmc planear  proyectar --cantidad 35 --analistas 3

gpmc medir-ia carpeta-de-expedientes   # mide el generador de propuestas sobre material real
gpmc diagnostico --sintaxis            # material para la prueba empírica de sintaxis
```

Códigos de salida: `0` correcto · `1` hallazgos bloqueantes · `2` error de uso, o huecos sin resolver con `--estricto` / `--desde-expediente`.

## Empezar un trámite nuevo

**Si ya hay expediente** (AS-IS, TO-BE y Diccionario de Datos en markdown):

```bash
gpmc extraer ruta/al/expediente -o tramite.yaml
```

Revisar los huecos que reporte, corregirlos en el YAML, y compilar.

**Si todavía no hay expediente** —el documento está por llegar, o el trámite es nuevo—:

```bash
cp ejemplos/plantilla-tramite.yaml tramite.yaml
```

`ejemplos/plantilla-tramite.yaml` está comentada campo por campo: qué acepta cada tipo, cómo se
declara un catálogo, cómo se bifurca el flujo y cómo se parametriza cada arquetipo de Acción.
Compila y valida tal cual, así que sirve de punto de partida verificado.

En cualquiera de los dos casos, antes de compilar conviene:

```bash
gpmc estimar tramite.yaml    # ¿la complejidad corresponde a lo esperado?
gpmc simular tramite.yaml -o sim.html   # ¿el flujo hace lo que debe?
```

## Cómo funciona

```
insumos (.md)  →  manifiesto (.yaml)  →  .gpm + simulador + reporte
                        ↑
                 donde se corrige
```

El manifiesto es una representación intermedia legible. El analista corrige **ahí**, no en el
`.gpm`, para que sus correcciones sobrevivan cuando los insumos cambien. El `.gpm` pasa a ser un
artefacto de compilación: se regenera, no se edita.

### Los extractores proponen, no adivinan

Lo que no puede derivarse de los insumos se reporta como **hueco** para que una persona lo
resuelva. Un extractor que no reportara huecos sobre material real estaría inventando, y esos
errores no se notan hasta que el trámite está en producción.

El flujo que se propone es **lineal**, una tarea por pantalla. Las compuertas del diagrama TO-BE
se cuentan y se reportan, pero no se reproducen: traducir automáticamente una etiqueta en
lenguaje natural a una condición es justo donde un error pasaría inadvertido.

### Calidad por construcción

Tres defectos frecuentes dejan de ser expresables, porque el analista da parámetros y nunca
código:

| Arquetipo | Qué garantiza |
| --- | --- |
| `folio` | Bloqueo transaccional sobre `dato_seguimiento.valor`, llaveado por el nombre de la variable y sin `proceso_id`. Nunca `count()` ni `rand()` |
| `documento` | Toda variable de usuario envuelta en `htmlspecialchars` |
| `notificacion` | Destinatario obligatorio, tomado del manifiesto |

## Garantía del formato

```python
json.dumps(obj, separators=(',', ':'), ensure_ascii=True).replace('/', '\\/')
```

Reproduce **byte a byte** los exports de referencia de la plataforma. La prueba de ida y vuelta lo
verifica en cada corrida, así que lo que se genera es importable.

## Pruebas

```bash
.venv/bin/pytest -v
```

Las que necesitan material real se saltan si no está disponible. Para correrlas completas:

```bash
export GPMC_EXPORTS=~/ruta/a/exports-de-referencia
export GPMC_GPM=~/ruta/a/archivos-gpm
export GPMC_WIKI=~/ruta/a/wiki/expedientes
```

## Cuestión resuelta: la sintaxis de transición

`SINTAXIS_ESTRICTA` en `src/gpmc/nucleo/reglas.py` controla si una regla de transición se emite
como `@@campo=='valor'` o como `@@campo->value === 'valor'`. Documentación interna sostenía que
la primera forma «siempre falla» con campos complejos.

**Quedó refutado con prueba empírica el 2026-08-31**, con acta en
`planeacion/actas/2026-08-30-prueba-en-plataforma.md`: cuatro exports de referencia ya publicados
usan `==` sobre campos `select`, y un trámite compilado con la forma simple avanzó de rama al
ejercitarlo de punta a punta. La constante se queda en `False` y no se cambia sin otra prueba
documentada que lo contradiga.

## Licencia

Uso interno de la Dirección de Gestión Tecnológica.
