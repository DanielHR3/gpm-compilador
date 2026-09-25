"""Envío de correo para la recuperación de contraseña (decisión 2026-09-25).

Todavía no se sabe si el envío será por SES de AWS o por el SMTP de Hidalgo:
los dos hablan SMTP (SES da credenciales SMTP), así que una sola
implementación sobre `smtplib` cubre ambos. Se configura por entorno:
`GPMC_SMTP_HOST`, `GPMC_SMTP_PUERTO` (587), `GPMC_SMTP_USUARIO`,
`GPMC_SMTP_CLAVE`, `GPMC_SMTP_REMITENTE`. Sin host, no hay correo y el
asistente lo dice en vez de fingir que mandó algo.
"""
import smtplib
from email.message import EmailMessage
from typing import Optional


class CorreoEnMemoria:
    """Guarda lo enviado: lo que ven las pruebas."""

    def __init__(self):
        self.enviados = []

    def enviar(self, para: str, asunto: str, texto: str) -> None:
        self.enviados.append({"para": para, "asunto": asunto, "texto": texto})


class CorreoSmtp:
    def __init__(self, host: str, puerto: int, usuario: Optional[str], clave: Optional[str],
                 remitente: str):
        self.host, self.puerto, self.usuario, self.clave, self.remitente = host, puerto, usuario, clave, remitente

    def enviar(self, para: str, asunto: str, texto: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.remitente, para, asunto
        msg.set_content(texto)
        with smtplib.SMTP(self.host, self.puerto, timeout=20) as s:
            s.ehlo()
            if self.puerto != 25:
                s.starttls()
            if self.usuario:
                s.login(self.usuario, self.clave or "")
            s.send_message(msg)


def correo_desde_entorno(e: dict) -> Optional[CorreoSmtp]:
    host = (e.get("GPMC_SMTP_HOST") or "").strip()
    if not host:
        return None
    return CorreoSmtp(host=host, puerto=int(e.get("GPMC_SMTP_PUERTO") or 587),
                      usuario=e.get("GPMC_SMTP_USUARIO") or None, clave=e.get("GPMC_SMTP_CLAVE") or None,
                      remitente=e.get("GPMC_SMTP_REMITENTE") or f"compilador-gpm@{host}")
