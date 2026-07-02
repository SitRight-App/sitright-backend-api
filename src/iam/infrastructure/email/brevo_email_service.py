import asyncio
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Envía correos transaccionales por el relay SMTP de Brevo. Si faltan
    credenciales, corre en modo dev: no envía y loguea el enlace (útil en local)."""

    def __init__(self, settings) -> None:
        self._host = settings.brevo_smtp_host
        self._port = settings.brevo_smtp_port
        self._user = settings.brevo_smtp_user
        self._key = settings.brevo_smtp_key
        self._sender_name = settings.email_sender_name
        self._sender_address = settings.email_sender_address

    def _configured(self) -> bool:
        return bool(self._user and self._key and self._sender_address)

    def _build_message(self, to_email: str, to_name: str, reset_link: str) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = "Restablece tu contrasena de SitRight"
        msg["From"] = f"{self._sender_name} <{self._sender_address}>"
        msg["To"] = f"{to_name} <{to_email}>"
        msg.set_content(
            f"Hola {to_name},\n\n"
            "Recibimos una solicitud para restablecer tu contrasena de SitRight.\n"
            "Abre este enlace para crear una nueva (caduca en 1 hora):\n\n"
            f"{reset_link}\n\n"
            "Si no fuiste tu, ignora este correo.\n"
        )
        return msg

    def _send_sync(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(self._user, self._key)
            smtp.send_message(msg)

    async def send_password_reset(
        self, to_email: str, to_name: str, reset_link: str
    ) -> None:
        if not self._configured():
            logger.info(
                "[reset] (modo dev, sin SMTP) enlace para %s: %s", to_email, reset_link
            )
            return
        msg = self._build_message(to_email, to_name, reset_link)
        await asyncio.to_thread(self._send_sync, msg)
