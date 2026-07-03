import logging

import httpx

logger = logging.getLogger(__name__)

_API_URL = "https://api.brevo.com/v3/smtp/email"

# Paleta de marca SitRight (HTML de los correos)
_MOSS = "#2d4a36"
_MOSS_DEEP = "#1f3324"
_CREAM = "#f4efe6"
_BONE = "#ebe3d3"
_INK = "#1a1f1b"
_INK_SOFT = "#4a5249"
_INK_FAINT = "#8a9088"
_TERRACOTTA = "#c8623c"
_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


class BrevoEmailService:
    """Envía correos transaccionales por la API HTTP de Brevo (puerto 443).

    Se usa la API HTTP en lugar de SMTP porque muchos hosts (Render) bloquean
    los puertos SMTP salientes. Si faltan credenciales o remitente, corre en
    modo dev: no envía y loguea el aviso.
    """

    def __init__(self, settings) -> None:
        self._api_key = settings.brevo_api_key
        self._sender_name = settings.email_sender_name
        self._sender_address = settings.email_sender_address

    def _configured(self) -> bool:
        return bool(self._api_key and self._sender_address)

    # ── Plantilla HTML de marca ────────────────────────────────────────────
    def _html(
        self,
        heading: str,
        body_html: str,
        cta_label: str | None = None,
        cta_link: str | None = None,
        note_html: str | None = None,
        accent: str = _MOSS,
    ) -> str:
        cta = ""
        if cta_label and cta_link:
            cta = (
                "<table role='presentation' cellpadding='0' cellspacing='0' style='margin:24px 0 4px;'>"
                f"<tr><td style='border-radius:10px;background:{accent};'>"
                f"<a href='{cta_link}' style='display:inline-block;padding:13px 26px;color:{_CREAM};"
                f"font-weight:600;font-size:15px;text-decoration:none;font-family:{_FONT};'>{cta_label}</a>"
                "</td></tr></table>"
            )
        note = ""
        if note_html:
            note = (
                f"<p style='margin:18px 0 0;font-size:13px;line-height:1.55;color:{_INK_FAINT};'>{note_html}</p>"
            )
        return (
            f"<div style='margin:0;padding:24px 12px;background:{_CREAM};font-family:{_FONT};'>"
            "<table role='presentation' width='100%' cellpadding='0' cellspacing='0'>"
            "<tr><td align='center'>"
            "<table role='presentation' width='480' cellpadding='0' cellspacing='0' "
            f"style='max-width:480px;width:100%;background:#ffffff;border-radius:16px;"
            f"overflow:hidden;border:1px solid {_BONE};'>"
            f"<tr><td style='background:{_MOSS_DEEP};padding:18px 28px;'>"
            f"<span style='color:{_CREAM};font-size:18px;font-weight:700;letter-spacing:-0.01em;'>SitRight</span>"
            "<span style='color:#9db3a4;font-size:12px;'> · Monitoreo postural</span>"
            "</td></tr>"
            "<tr><td style='padding:30px 28px 26px;'>"
            f"<h1 style='margin:0 0 14px;font-size:21px;line-height:1.25;color:{_INK};font-weight:700;'>{heading}</h1>"
            f"<div style='font-size:15px;line-height:1.6;color:{_INK_SOFT};'>{body_html}</div>"
            f"{cta}{note}"
            "</td></tr>"
            f"<tr><td style='padding:16px 28px;background:{_BONE};'>"
            f"<p style='margin:0;font-size:12px;line-height:1.5;color:{_INK_FAINT};'>"
            "Recibiste este correo porque tienes una cuenta en SitRight. · Lima, 2026</p>"
            "</td></tr>"
            "</table></td></tr></table></div>"
        )

    # ── Construcción de cada correo -> (asunto, texto, html) ────────────────
    def _build_message(self, to_name: str, reset_link: str) -> tuple[str, str, str]:
        text = (
            f"Hola {to_name},\n\n"
            "Recibimos una solicitud para restablecer tu contraseña de SitRight.\n"
            "Abre este enlace para crear una nueva (caduca en 1 hora):\n\n"
            f"{reset_link}\n\n"
            "Si no fuiste tú, ignora este correo: tu contraseña seguirá igual.\n"
        )
        html = self._html(
            "Restablece tu contraseña",
            "<p style='margin:0 0 12px;'>Recibimos una solicitud para restablecer la contraseña de tu cuenta.</p>"
            "<p style='margin:0;'>Haz clic en el botón para crear una nueva. El enlace "
            "<b>caduca en 1 hora</b> y solo puede usarse una vez.</p>",
            cta_label="Crear una nueva contraseña",
            cta_link=reset_link,
            note_html=(
                "Si el botón no funciona, copia y pega este enlace en tu navegador:<br>"
                f"<a href='{reset_link}' style='color:{_MOSS};word-break:break-all;'>{reset_link}</a><br><br>"
                "Si no fuiste tú, puedes ignorar este correo: tu contraseña seguirá igual."
            ),
        )
        return "Restablece tu contraseña de SitRight", text, html

    def _build_password_changed_message(self, to_name: str) -> tuple[str, str, str]:
        text = (
            f"Hola {to_name},\n\n"
            "Te avisamos que la contraseña de tu cuenta de SitRight fue cambiada.\n"
            "Si fuiste tú, no necesitas hacer nada más.\n"
            "Si no reconoces este cambio, contacta a soporte de inmediato.\n"
        )
        html = self._html(
            "Tu contraseña fue cambiada",
            "<p style='margin:0 0 12px;'>Te avisamos que la contraseña de tu cuenta de SitRight "
            "acaba de cambiarse correctamente.</p>"
            "<p style='margin:0;'>Si fuiste tú, no necesitas hacer nada más.</p>",
            note_html=(
                f"<b style='color:{_TERRACOTTA};'>¿No reconoces este cambio?</b> "
                "Contacta a soporte de inmediato para proteger tu cuenta."
            ),
        )
        return "Tu contraseña de SitRight fue cambiada", text, html

    def _build_posture_alert_message(self, to_name: str) -> tuple[str, str, str]:
        text = (
            f"Hola {to_name},\n\n"
            "Detectamos que llevas un rato en mala postura.\n"
            "Endereza la espalda y ajusta tu posición frente al escritorio.\n"
        )
        html = self._html(
            "Endereza la espalda",
            "<p style='margin:0 0 12px;'>Detectamos que llevas <b>varios minutos en mala postura</b>.</p>"
            "<p style='margin:0;'>Tómate un momento para enderezar la espalda y ajustar tu posición "
            "frente al escritorio. Tu columna te lo agradecerá.</p>",
            accent=_TERRACOTTA,
        )
        return "Llevas un rato en mala postura", text, html

    def _build_break_reminder_message(self, to_name: str) -> tuple[str, str, str]:
        text = (
            f"Hola {to_name},\n\n"
            "Llevas bastante tiempo sentado.\n"
            "Levántate y estírate 1-2 minutos antes de continuar.\n"
        )
        html = self._html(
            "Tómate una pausa activa",
            "<p style='margin:0 0 12px;'>Llevas <b>bastante tiempo sentado</b> sin moverte.</p>"
            "<p style='margin:0;'>Levántate y estírate 1–2 minutos antes de continuar. "
            "Una pausa corta ayuda a prevenir la fatiga muscular.</p>",
        )
        return "Es momento de una pausa activa", text, html

    async def _send(
        self, to_email: str, to_name: str, subject: str, text: str, html: str
    ) -> None:
        payload = {
            "sender": {"name": self._sender_name, "email": self._sender_address},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html,
            "textContent": text,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _API_URL,
                headers={
                    "api-key": self._api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()

    async def send_password_reset(
        self, to_email: str, to_name: str, reset_link: str
    ) -> None:
        if not self._configured():
            logger.info(
                "[reset] (modo dev, sin API) enlace para %s: %s", to_email, reset_link
            )
            return
        subject, text, html = self._build_message(to_name, reset_link)
        await self._send(to_email, to_name, subject, text, html)

    async def send_password_changed(self, to_email: str, to_name: str) -> None:
        if not self._configured():
            logger.info(
                "[password-changed] (modo dev, sin API) aviso para %s", to_email
            )
            return
        subject, text, html = self._build_password_changed_message(to_name)
        await self._send(to_email, to_name, subject, text, html)

    async def send_posture_alert(self, to_email: str, to_name: str) -> None:
        if not self._configured():
            logger.info("[posture-alert] (modo dev, sin API) aviso para %s", to_email)
            return
        subject, text, html = self._build_posture_alert_message(to_name)
        await self._send(to_email, to_name, subject, text, html)

    async def send_break_reminder(self, to_email: str, to_name: str) -> None:
        if not self._configured():
            logger.info("[break-reminder] (modo dev, sin API) aviso para %s", to_email)
            return
        subject, text, html = self._build_break_reminder_message(to_name)
        await self._send(to_email, to_name, subject, text, html)
