"""Lo que se consulta de la bitacora de acciones.

El registro vive en el middleware de `acceso.py` y en la tabla `auditoria`
(spec 2026-09-25). Esto es la mitad que se ve (2026-10-16): el CSV que pide la
auditoria interna y la regla de que cuenta como error, compartidas por el API,
la CLI y los dos almacenes.
"""
import csv
import io
import re

COLUMNAS = ("fecha", "usuario", "dependencia", "accion", "sid", "detalle", "ip")

# Una accion que el servidor rechazo lleva el codigo HTTP al final del detalle
# («produccion (409)»); un fallo del servidor es su propia accion; un intento
# de entrar fallido tambien cuenta: es lo primero que mira una auditoria.
_CODIGO_AL_FINAL = re.compile(r"\((4|5)\d\d\)$")
ACCIONES_DE_ERROR = ("error.servidor", "sesion.fallo")


def es_error(fila: dict) -> bool:
    if fila.get("accion") in ACCIONES_DE_ERROR:
        return True
    return bool(_CODIGO_AL_FINAL.search(fila.get("detalle") or ""))


def a_csv(filas: list) -> str:
    """CSV con las siete columnas, en el orden de `COLUMNAS`; comas y comillas
    escapadas como manda el formato, sin BOM, con salto final."""
    salida = io.StringIO()
    w = csv.writer(salida, lineterminator="\n")
    w.writerow(COLUMNAS)
    for f in filas:
        w.writerow([("" if f.get(c) is None else f.get(c)) for c in COLUMNAS])
    return salida.getvalue()
