# Fase A — Integración de catálogos remotos y APIs

## Objetivo
Implementar la lectura de las columnas "Dependencia" y "Endpoint / API" del Diccionario de Datos para extraer la configuración de campos dependientes, catálogos remotos y consumos API.

## 1. El problema actual
Hasta la Fase 0, el compilador trata todos los `select` asumiendo un catálogo manual (`catalog_type="manual"`). Sin embargo, en el Diccionario existen campos que:
1. Extraen sus opciones dinámicamente desde un endpoint (catálogo remoto).
2. Dependen del valor seleccionado en otro campo (ej. `municipio_sol` depende de `estado_sol`).
3. Se autocompletan en base a una petición API (ej. `nombres_sol` con dependencia `api_ajax`).

Actualmente, esta información, presente en las columnas "Dependencia" y "Endpoint / API", se descarta por completo.

## 2. Lo que se debe extraer (Diccionario)

En `src/gpmc/extractores/diccionario.py`, se buscarán dos columnas:
- **Dependencia**:
  - `N/A` o vacío -> No hay dependencia.
  - `api_ajax` -> Autocompletado desde una API.
  - `@@campo` o `campo` -> Depende de otro campo.
- **Endpoint / API**:
  - La ruta, identificador o URL del consumo.

### Modelo Pydantic
Se añadirá al modelo `Campo` en `manifiesto.py`:
```python
    dependencia_tipo: Optional[str] = None  # "api_ajax" o "campo"
    dependencia_campo: Optional[str] = None # el nombre del campo padre
    endpoint: Optional[str] = None
```

## 3. Emisión al .gpm (Compilador)

En `src/gpmc/compilador/a_gpm.py`:
1. Si tiene `dependencia_tipo == "campo"`:
   - Configurar `dependiente_campo` con el nombre del padre.
2. Si tiene un `endpoint` y es `select`:
   - Configurar como catálogo remoto (`catalog_type="url"` o equivalente).
3. Si es `api_ajax`:
   - Evaluar si GPM lo soporta de forma nativa o si se emitirá como un Hueco de configuración manual, dado que JS inyectado o `Api variable` podrían estar prohibidos según `CLAUDE.md`.

## 4. Preguntas abiertas / Riesgos
- **Formato exacto en GPM**: Necesitamos un export auténtico (`.gpm`) que contenga un `select` remoto y un select en cascada para copiar la estructura. Sin ello, no sabemos si GPM requiere `catalog_url`, `object_response`, etc.
- **Soporte de API Ajax**: ¿Cómo se representa `api_ajax` nativamente?

## 5. Plan de Tareas
- [x] **Task 1**: Extraer las columnas en `diccionario.py`.
- [x] **Task 2**: Actualizar el modelo `Campo`.
- [x] **Task 3**: Ajustar `simulador/html.py` para visualizar en la UI si un campo es llenado por API o si es dependiente.
- [ ] **Task 4**: (Bloqueada hasta tener JSON real) Traducir al `.gpm`.
