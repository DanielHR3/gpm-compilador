# Comparativa que llega completa: evidencia del agente y puntos de mejora — diseño

Fecha: 2026-10-01 · Estado: aprobada en conversación (Daniel, 2026-10-01) · Solicita: Daniel, para Simplificación

## Propósito

Hoy «Antes y después» llega con huecos. De sus siete métricas el compilador solo llena
completas dos (requisitos y pasos); las otras cinco exigen que Simplificación teclee el dato, y
con menos de dos métricas completas ni siquiera sale el porcentaje. Medido el 2026-10-01 sobre
cuatro sesiones reales: en todas faltaban actores (antes), sistemas (los dos lados), tiempo
(después), visitas y capturas (los dos lados).

Éxito: el analista abre «Antes y después» y la página se completa sola. Cada cifra que no contó
el compilador dice «propuesto por el agente» y enseña las frases del expediente en que se
apoya. Al final hay una lista de lo que el trámite rediseñado todavía puede simplificar.

## Decisiones tomadas (Daniel, 2026-10-01)

| Pregunta | Decisión |
| --- | --- |
| ¿Cómo entra una cifra propuesta? | Sola, cuenta para el porcentaje y va rotulada «propuesto por el agente» con su evidencia. |
| ¿De qué hablan los puntos de mejora? | De lo que aún se puede simplificar en el trámite ya rediseñado. |
| ¿Cuándo corre el agente? | Solo, la primera vez que se abre la comparativa de un expediente. |

## Lo que cambió con la prueba en vivo

Se probaron los dos prompts con `gemini-3.5-flash-lite` sobre *Reposición de Certificado* y
*Prórroga y/o Ampliación*:

- **El modelo entrega evidencia, no cifras.** En Reposición copió literales 17 de 17 frases.
  En Prórroga (TO-BE de 25 000 caracteres) falló 4 de 13: leyó a través de los `<br/>` de un
  nodo del diagrama, unió trozos de líneas distintas y citó del TO-BE una frase para el
  «antes». De ahí tres reglas de la verificación: las etiquetas HTML no son texto, se acepta
  el **tramo literal más largo** de la cita (y se guarda ese tramo, tal como está en el
  documento, no lo que escribió el modelo), y el «antes» solo se sostiene en el AS-IS.
- **Los TO-BE traen una tabla que la comparativa ignoraba:** «Análisis de eliminación por
  requisito y por paso» (`Elemento del AS-IS | ¿Se elimina? | Fundamento`). Es la forma del
  equipo y la que prescribe el prompt de la Fase 3. Leerla no necesita modelo y es la
  evidencia más directa de la reingeniería: «de 17 elementos, 8 se eliminan». Entra como
  sección propia, **sin** tocar las siete métricas ni su porcentaje.
- **En un punto de mejora, un campo del manifiesto es evidencia.** El modelo cita mal las
  filas de tabla, pero nombra bien el campo `file` que se sigue pidiendo.

## Las tres piezas

### 1. «Qué pasó con cada elemento del trámite» (sin modelo)

`extractores/rediseno.py` lee la tabla de eliminación. Cada fila conserva el texto del equipo
(elemento, decisión, fundamento) y se clasifica solo para contar y colorear:

| Clase | La celda «¿Se elimina?» empieza por… |
| --- | --- |
| `elimina` | «Sí» |
| `conserva` | «No», «Se conserva» |
| `cambia` | «Se integra», «Se sustituye», «Se reduce», «Se flexibiliza», «Se fusiona», «Se automatiza», «Se simplifica» |
| `sin_decision` | «Sin decisión», «Pendiente», «Por confirmar», vacío |
| `otro` | cualquier otra cosa: se enseña tal cual y no se cuenta en ninguna de las anteriores |

### 2. Evidencia para los lados vacíos (agente + verificación)

Una llamada (`cmp-v1`). El agente recibe AS-IS, TO-BE y la lista de lados sin dato, y devuelve
elementos `{nombre, cita}` por lado. **La cifra no la da el modelo: es cuántos elementos
sobreviven la verificación.**

| Métrica | Un elemento es… | Además de la cita literal |
| --- | --- | --- |
| requisitos, pasos (solo antes) | un documento que se entrega · un paso | — |
| actores, sistemas | un área o persona · un sistema, plataforma o archivo | el nombre aparece en el documento |
| tiempo | el plazo con cifra y unidad | el plazo está dentro de la cita |
| visitas | una vez que el ciudadano va en persona | la cita habla de ir, entregar o recoger en persona |
| capturas | un dato que se escribe más de una vez | la cita habla de capturar, llenar o escribir |

«Ninguno» (cero visitas, cero capturas repetidas) solo entra con una frase que lo diga y que
hable del tema. Sin evidencia, el lado se queda «sin dato»: no se rellena.

Precedencia: lo declarado por una persona gana; después lo revisado, lo contado y lo leído; lo
propuesto solo ocupa un lado que seguía vacío.

### 3. «Qué más se puede simplificar» (agente + verificación)

Segunda llamada (`mejoras-v1`), aparte, porque el modelo disponible ya copia mal con una sola
tarea. Entre tres y seis puntos, cada uno con título, propuesta, beneficio y evidencia: una
frase literal o un campo del manifiesto. Un punto sin evidencia se descarta. Si propone
consultar un servicio, la clave tiene que estar en el catálogo público
(`nucleo/integraciones.CATALOGOS`); si no, se rotula «requiere convenio». Cada tarjeta se
puede descartar, y un descarte sobrevive a «Volver a analizar».

## Arquitectura

- `agentes/prompt_comparativa.py`, `agentes/verificar_comparativa.py` (sin modelo),
  `agentes/comparativa.py` (orquesta las dos llamadas; nunca propaga).
- `comparativa/propuestas.py`: la forma de una propuesta y de un punto de mejora, pura.
  `comparativa/` sigue sin importar de `agentes`: `armar.comparar` recibe las propuestas ya
  verificadas como datos y sigue siendo una función pura.
- `web/api_comparativa.py` persiste en `comparativa.json`, con candado por sesión:
  `POST …/comparativa/analizar` (202, segundo plano) y
  `POST …/comparativa/mejoras/{id}/descartar`. Nada de `agentes/` escribe en la sesión ni en
  el manifiesto.
- La SPA dispara el análisis al abrir la página si nunca se hizo, y consulta hasta que termina.
- Sin proveedor o sin pasar `fase3.puede_generar`, la página queda como hoy y lo dice.
- Si el modelo falla, queda lo contado. Si falla solo la segunda llamada, las cifras quedan.

## Avisos

- `CMP-02` nombra solo lo que sigue sin dato después de las propuestas.
- `CMP-06` (`por_confirmar`): qué métricas usan una cifra propuesta por el agente. Va en las
  observaciones, no bloquea.

## Límites que se dicen en pantalla

La verificación comprueba que la frase existe y que habla del tema, no que el modelo la
interpretó bien. Por eso la evidencia va a la vista, el origen dice «propuesto», y la frase del
veredicto cuenta cuántas métricas usan cifras propuestas.

## Fuera de alcance

- Qué cuenta como requisito y como paso en las cuentas del compilador (pendiente con
  Simplificación desde el 2026-09-28). La prueba lo volvió a mostrar: en Reposición la cuenta
  de «después» incluye el archivo que sube el funcionario y da «3 → 7».
- Convertir unidades de tiempo.

## Cambio propuesto al `CLAUDE.md` (requiere aprobación)

La sección 13 dice «Determinista… no hay un modelo opinando». Texto propuesto: «Las cuentas
son deterministas: `comparativa/armar.comparar` es una función pura. Un agente puede proponer
la evidencia de los lados que el compilador no sabe contar; la cifra es cuántas frases
sobreviven una verificación sin modelo, y va rotulada `propuesto`.»
