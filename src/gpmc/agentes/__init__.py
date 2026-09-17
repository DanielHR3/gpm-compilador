"""Agentes de IA del compilador. Es el UNICO paquete que habla con un modelo.

`nucleo/` no importa nada de aqui (tests/test_agentes.py lo verifica). Todo lo
que sale de este paquete es una *propuesta*: la escritura al manifiesto sigue
siendo exclusivamente `POST /resolver`.
"""
from gpmc.agentes.proveedor import crear_proveedor, hay_proveedor  # noqa: F401
