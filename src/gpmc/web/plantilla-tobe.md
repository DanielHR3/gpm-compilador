# Propuesta TO-BE — plantilla de ejemplo

Copia este archivo y reemplaza el diagrama por el de **tu** trámite. Es un
ejemplo completo de **Constancia de Residencia**: un flujo con una revisión
que puede aprobar o rechazar.

## Cómo se llena

El diagrama va en un bloque ` ```mermaid `. Tres reglas evitan que el sistema
tenga que preguntarte cosas que ya sabes al dibujarlo:

- **Cada nodo lleva `:::actor`** (el carril de quien lo ejecuta: `:::ciudadano`,
  `:::funcionario`, etc., declarado antes con `classDef`). Sin esto, el
  compilador no sabe quién hace la tarea y te lo va a preguntar uno por uno —
  en un trámite de 40 pasos son 40 preguntas que este párrafo evita.
- **Cada compuerta (`{...}`) nombra un solo `@@campo`** del Diccionario:
  `{¿@@dictamen == 'aprobado'?}`. Con eso el compilador ramifica el flujo solo.
  Si la compuerta no nombra ningún campo, sale como pregunta pendiente y hay
  que capturar la condición a mano después.
- **Las flechas que salen de una compuerta llevan de etiqueta un valor del
  catálogo de ese campo** (o "Sí"/"No"), no una frase libre:
  `-->|Aprobado| P4`, no `-->|el dictamen salió bien| P4`. La etiqueta tiene
  que coincidir con una opción real de la lista desplegable en el Diccionario.
- El texto de cada nodo puede usar `<br/>` para partir líneas largas; se lee
  bien en el diagrama y el compilador lo entiende.

Si tu trámite tiene una compuerta que decide algo que el Diccionario no
captura como campo (una regla de negocio, un cálculo), está bien dejarla sin
`@@campo` — el sistema la marca como pendiente y se configura a mano después.

## Ejemplo

```mermaid
flowchart TD
    classDef ciudadano fill:#E4EFEA,stroke:#4C8C6B
    classDef funcionario fill:#F5E6DF,stroke:#B97A56

    Inicio([Inicio]):::ciudadano --> P1[Ciudadano: Solicitud]:::ciudadano
    P1 --> P2[Funcionario: Revisión]:::funcionario
    P2 --> G{¿@@dictamen == 'aprobado'?}:::funcionario
    G -->|Aprobado| P4[Funcionario: Emisión]:::funcionario
    G -->|Rechazado| P3[Ciudadano: Corrección]:::ciudadano
    P3 --> P2
    P4 --> Fin([Fin]):::funcionario
```
