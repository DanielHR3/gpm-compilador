"""Límites de columna de la plataforma GPM, en un solo lugar.

Verificados importando expedientes reales (bitácora 2026-08-31 y 2026-09-02):
un nombre que pasa de estos topes tumba el import entero con
`Data too long for column …`. El extractor los aplica al derivar nombres; el
validador es la red para un manifiesto escrito a mano.
"""

# Columna `campo.nombre`. Un `@@` de 38 (Prórroga) reventó el import (PLAT-7).
LIMITE_CAMPO_NOMBRE = 30

# Columnas `formulario.nombre` y `tarea.nombre`. Una etiqueta larga producía un
# nombre de 40+ que la plataforma rechazaba (PLAT-5).
LIMITE_FORMULARIO_NOMBRE = 60
