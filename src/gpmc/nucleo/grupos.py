"""Grupos de usuarios de la plataforma que se han visto en uso.

El catalogo de grupos vive en la plataforma y el compilador no lo conoce: no
hay forma de derivar de un expediente a que grupo corresponde un responsable.
Esta lista solo AYUDA a quien lo escribe en el asistente (`ACT-01`); un grupo
que no este aqui es tan valido como uno que si.

De donde sale cada entrada: las cuatro constan en `planeacion/pendientes.md`
(PLAT-11, 2026-09-22), tomadas de tramites hechos a mano en la plataforma.
No se han vuelto a leer de los exports de referencia. Antes de añadir una, que
se haya visto en un export o en el modelador; `grupo práctica` existe y no
entra, porque es un grupo de pruebas.
"""

OBSERVADOS = (
    "area_primer_contacto",
    "licitaciones_admin",
    "transparencia_admin",
    "verificacion_vehicular",
)
