"""Palabras que nombran algo, compartidas por las verificaciones sin modelo.

Que una frase exista en el documento no prueba que hable de ESTE elemento:
tiene que compartir con su nombre al menos una palabra que nombre algo
(revision de la rama, 2026-09-28). Lo usan la verificacion de documentos y,
desde 2026-10-16, la de la comparativa.
"""
from gpmc.planeacion.registro import clave

# Palabras de cuatro letras o mas que no nombran nada.
VACIAS = {"para", "como", "este", "esta", "esto", "todo", "toda", "todos", "todas", "sobre",
          "entre", "desde", "hasta", "cuando", "donde", "solo", "caso", "cada", "otro", "otra",
          "pero", "tambien", "debe", "deben", "sera", "seran", "tiene", "tienen", "tramite"}


def raiz(palabra: str) -> str:
    if len(palabra) > 4 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def significativas(texto) -> set:
    return {raiz(p) for p in clave(texto if isinstance(texto, str) else "").split()
            if len(p) >= 4 and p not in VACIAS}


def comparten(a, b) -> bool:
    return bool(significativas(a) & significativas(b))
